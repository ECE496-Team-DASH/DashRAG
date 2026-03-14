import { Chat } from "@/components/Chat/Chat";
import { Footer } from "@/components/Layout/Footer";
import { Navbar } from "@/components/Layout/Navbar";
import { Message, Document, QueryMode, StatusMessage as StatusMsg, ProcessingPhase, ArXivPaper } from "@/types";
import { dashragAPI } from "@/utils/dashrag-api";
import { useAuth } from "@/utils/AuthContext";
import Head from "next/head";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/router";

const makeStatusId = () =>
  `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

const estimateIndexMsFromFileSize = (fileSizeBytes?: number) => {
  const mb = (fileSizeBytes || 0) / (1024 * 1024);
  const estimate = 14000 + mb * 24000;
  return Math.max(8000, Math.min(estimate, 25 * 60 * 1000));
};

const nowMs = () => Date.now();

// Helper function to get user-friendly phase descriptions
const getPhaseDescription = (phase: ProcessingPhase | undefined): string => {
  if (!phase) return "Processing...";
  
  const phaseDescriptions: Record<ProcessingPhase, string> = {
    pdf_extraction: "📄 Extracting text from PDF",
    text_chunking: "📝 Creating text chunks",
    entity_extraction: "🔍 Extracting entities and relationships",
    graph_clustering: "🕸️ Building knowledge graph",
    community_reports: "📊 Generating community reports",
    finalizing: "✨ Finalizing document",
  };
  
  return phaseDescriptions[phase] || "Processing...";
};

export default function ChatPage() {
  const router = useRouter();
  const { token, isLoading: authLoading } = useAuth();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionTitle, setSessionTitle] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [statusMessages, setStatusMessages] = useState<StatusMsg[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [uploadingFile, setUploadingFile] = useState<boolean>(false);
  const [queryMode, setQueryMode] = useState<QueryMode>("local");
  
  // ArXiv search state
  const [arxivSearchOpen, setArxivSearchOpen] = useState<boolean>(false);
  const [arxivQuery, setArxivQuery] = useState<string>("");
  const [arxivResults, setArxivResults] = useState<ArXivPaper[]>([]);
  const [arxivSearching, setArxivSearching] = useState<boolean>(false);
  const [arxivError, setArxivError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Auth guard
  useEffect(() => {
    if (!authLoading && !token) {
      router.replace("/login");
    }
  }, [authLoading, token]);

  // Initialize or restore session
  useEffect(() => {
    if (authLoading || !token) return;
    const initSession = async () => {
      try {
        // Try to restore from localStorage
        const savedSessionId = localStorage.getItem("dashrag_session_id");
        const savedQueryMode = localStorage.getItem("dashrag_query_mode") as QueryMode;

        if (savedQueryMode) {
          setQueryMode(savedQueryMode);
        }

        if (savedSessionId) {
          // Verify session still exists
          try {
            const sessionData = await dashragAPI.getSession(savedSessionId);
            setSessionId(savedSessionId);
            setSessionTitle(sessionData.title);
            await loadDocuments(savedSessionId);
            return;
          } catch (error) {
            console.log("Saved session not found, creating new one");
            localStorage.removeItem("dashrag_session_id");
          }
        }

        // Create new session
        const session = await dashragAPI.createSession("New Chat");
        setSessionId(session.id);
        setSessionTitle(session.title);
        localStorage.setItem("dashrag_session_id", session.id);
      } catch (error) {
        console.error("Failed to initialize session:", error);
        addStatusMessage("error", "Failed to initialize session. Please refresh the page.");
      }
    };

    initSession();
  }, [authLoading, token]);

  // Save query mode to localStorage
  useEffect(() => {
    if (queryMode) {
      localStorage.setItem("dashrag_query_mode", queryMode);
    }
  }, [queryMode]);

  const loadDocuments = async (sid: string) => {
    try {
      const docs = await dashragAPI.getDocuments(sid);
      setDocuments(docs);
    } catch (error) {
      console.error("Failed to load documents:", error);
    }
  };

  const addStatusMessage = (
    status: "uploading" | "processing" | "ready" | "error",
    message: string,
    progress?: number,
    extras?: Partial<StatusMsg>
  ) => {
    const id = makeStatusId();
    const timestamp = nowMs();
    const statusMsg: StatusMsg = {
      id,
      type: "status",
      status,
      message,
      progress,
      startedAtMs: timestamp,
      timingUpdatedAtMs: timestamp,
      ...extras,
    };
    setStatusMessages((prev) => [...prev, statusMsg]);
    setTimeout(() => scrollToBottom(), 100);
    return id;
  };

  const updateStatusMessage = (
    statusId: string,
    status: "uploading" | "processing" | "ready" | "error",
    message: string,
    progress?: number,
    extras?: Partial<StatusMsg>
  ) => {
    setStatusMessages((prev) => {
      const timestamp = nowMs();
      return prev.map((item) => {
        if (item.id !== statusId) return item;
        return {
          ...item,
          type: "status",
          status,
          message,
          progress,
          timingUpdatedAtMs: timestamp,
          ...extras,
        };
      });
    });
  };

  // Fetch-based SSE reader (avoids EventSource's lack of custom header support)
  const processDocumentSSE = async (sessId: string, docId: string, label: string, statusId: string) => {
    const API_BASE = process.env.NEXT_PUBLIC_DASHRAG_API_URL || "http://localhost:8000";
    const url = `${API_BASE}/documents/progress-stream?sid=${sessId}&doc_id=${docId}`;
    try {
      const res = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok || !res.body) {
        updateStatusMessage(statusId, "error", "Connection error during processing", 0);
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.event === "complete") {
              if (data.status === "ready") {
                const doneMs = data.completed_in_ms ?? data.elapsed_ms;
                updateStatusMessage(
                  statusId,
                  "ready",
                  `✅ Indexed ${label}`,
                  100,
                  {
                    progress: 100,
                    elapsedMs: doneMs,
                    estimatedRemainingMs: 0,
                    estimatedTotalMs: data.estimated_total_ms ?? doneMs,
                    completedInMs: doneMs,
                  }
                );
              } else if (data.status === "error") {
                updateStatusMessage(statusId, "error", `❌ Failed to process ${label}`, 0, {
                  estimatedRemainingMs: 0,
                });
              }
              await loadDocuments(sessId);
              return;
            } else if (data.event === "error") {
              updateStatusMessage(statusId, "error", data.message || "Processing failed", 0, {
                estimatedRemainingMs: 0,
              });
              return;
            } else {
              const phaseMsg = getPhaseDescription(data.processing_phase);
              updateStatusMessage(statusId, "processing", phaseMsg, data.progress_percent || 10, {
                elapsedMs: data.elapsed_ms,
                estimatedTotalMs: data.estimated_total_ms,
                estimatedRemainingMs: data.estimated_remaining_ms,
              });
            }
          } catch {}
        }
      }
    } catch {
      updateStatusMessage(statusId, "error", "Connection error during processing", 0, {
        estimatedRemainingMs: 0,
      });
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!sessionId) {
      alert("No active session. Please refresh the page.");
      return;
    }

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Only PDF files are supported");
      return;
    }

    setUploadingFile(true);
    const estimatedTotalMs = estimateIndexMsFromFileSize(file.size);
    const statusId = addStatusMessage("uploading", `📤 Uploading ${file.name}...`, 0, {
      estimatedTotalMs,
      estimatedRemainingMs: estimatedTotalMs,
      elapsedMs: 0,
    });

    try {
      // Upload the file
      const doc = await dashragAPI.uploadDocument(sessionId, file);
      
      updateStatusMessage(statusId, "processing", `⏳ Processing ${file.name}...`, 5, {
        estimatedTotalMs,
        estimatedRemainingMs: estimatedTotalMs,
        elapsedMs: 0,
      });
      await processDocumentSSE(sessionId, doc.id, file.name, statusId);
    } catch (error: any) {
      console.error("Upload error:", error);
      updateStatusMessage(statusId, "error", error.message || "Upload failed", 0, {
        estimatedRemainingMs: 0,
      });
    } finally {
      setUploadingFile(false);
    }
  };

  const handleSend = async (message: Message) => {
    if (!sessionId) {
      alert("No active session. Please refresh the page.");
      return;
    }

    const userMessage: Message = {
      role: "user",
      content: message.content,
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    const messageText = typeof message.content === "string" ? message.content : message.content.text;
    const localStartedAt = Date.now();

    try {
      const createResult = await dashragAPI.createMessageRequest(
        sessionId,
        messageText,
        queryMode
      );

      const chatStatusId = addStatusMessage(
        "processing",
        "🤖 Thinking...",
        10,
        {
          estimatedTotalMs: createResult.estimated_total_ms,
          estimatedRemainingMs: createResult.estimated_total_ms,
          elapsedMs: 0,
        }
      );

      const maxAttempts = 120;
      let assistantMessage: any = null;
      let latestCompletedMs: number | undefined;

      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        await new Promise((resolve) => setTimeout(resolve, 1000));

        try {
          const progress = await dashragAPI.getMessageProgress(sessionId, createResult.message_id);
          latestCompletedMs = progress.completed_in_ms ?? latestCompletedMs;
          updateStatusMessage(chatStatusId, progress.status === "error" ? "error" : "processing", `🤖 ${progress.stage_label || "Thinking..."}`, progress.progress_percent || 10, {
            elapsedMs: progress.elapsed_ms,
            estimatedTotalMs: progress.estimated_total_ms,
            estimatedRemainingMs: progress.estimated_remaining_ms,
            completedInMs: progress.completed_in_ms ?? undefined,
          });

          if (progress.status === "error") {
            throw new Error(progress.error || "Query failed while processing");
          }
        } catch (progressErr) {
          // Keep polling for the final assistant message even if progress endpoint is temporarily unavailable.
        }

        const allMessages = await dashragAPI.getMessages(sessionId);
        const userMsgIndex = allMessages.findIndex((m) => Number(m.id) === createResult.message_id);
        if (userMsgIndex >= 0 && userMsgIndex < allMessages.length - 1) {
          const maybeAssistant = allMessages[userMsgIndex + 1];
          if (maybeAssistant && maybeAssistant.role === "assistant") {
            assistantMessage = maybeAssistant;
            break;
          }
        }
      }

      if (!assistantMessage) {
        throw new Error("Query timed out after 120 seconds");
      }

      const rawContent = assistantMessage.content;
      const normalizedContent = typeof rawContent === "string"
        ? { text: rawContent, citations: [] }
        : {
            text: rawContent?.text || "",
            citations: Array.isArray(rawContent?.citations) ? rawContent.citations : [],
            timing: rawContent?.timing,
          };

      const doneMs =
        normalizedContent.timing?.duration_ms ??
        latestCompletedMs ??
        Date.now() - localStartedAt;

      updateStatusMessage(chatStatusId, "ready", "✅ Answer ready", 100, {
        elapsedMs: doneMs,
        estimatedRemainingMs: 0,
        completedInMs: doneMs,
      });

      const assistantMessageForUi: Message = {
        role: "assistant",
        content: normalizedContent,
      };
      setMessages((prev) => [...prev, assistantMessageForUi]);
    } catch (error: any) {
      console.error("Send message error:", error);
      const errorMessage: Message = {
        role: "assistant",
        content: `Error: ${error.message || "Failed to get response"}`,
      };
      setMessages((prev) => [...prev, errorMessage]);
      addStatusMessage("error", `❌ ${error.message || "Failed to get response"}`, 0, {
        elapsedMs: Date.now() - localStartedAt,
        estimatedRemainingMs: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    try {
      // Create new session
      const session = await dashragAPI.createSession("New Chat");
      setSessionId(session.id);
      localStorage.setItem("dashrag_session_id", session.id);
      
      // Clear UI state
      setMessages([]);
      setStatusMessages([]);
      setDocuments([]);
      
      addStatusMessage("ready", "New chat session created!");
    } catch (error) {
      console.error("Reset error:", error);
      alert("Failed to create new session. Please refresh the page.");
    }
  };

  const handleRefreshDocuments = async () => {
    if (sessionId) {
      await loadDocuments(sessionId);
    }
  };

  const handleArxivSearch = async () => {
    if (!arxivQuery.trim()) {
      setArxivError("Please enter a search query");
      return;
    }

    setArxivSearching(true);
    setArxivError(null);
    
    try {
      const results = await dashragAPI.searchArxiv(arxivQuery, 5);
      setArxivResults(results);
      
      if (results.length === 0) {
        setArxivError("No papers found for this query");
      }
    } catch (error: any) {
      console.error("ArXiv search error:", error);
      setArxivError(error.message || "Failed to search arXiv");
      setArxivResults([]);
    } finally {
      setArxivSearching(false);
    }
  };

  const handleAddArxivPaper = async (arxivId: string) => {
    if (!sessionId) {
      alert("No active session");
      return;
    }

    setUploadingFile(true);
    const statusId = addStatusMessage("uploading", `📥 Adding arXiv paper ${arxivId}...`, 0, {
      estimatedTotalMs: 30_000,
      estimatedRemainingMs: 30_000,
      elapsedMs: 0,
    });

    try {
      const doc = await dashragAPI.addArxivPaper(sessionId, arxivId);
      
      updateStatusMessage(statusId, "processing", `⏳ Downloading arXiv:${arxivId}...`, 5, {
        estimatedTotalMs: 30_000,
        estimatedRemainingMs: 30_000,
      });
      await processDocumentSSE(sessionId, doc.id, `arXiv:${arxivId}`, statusId);
    } catch (error: any) {
      console.error("arXiv error:", error);
      updateStatusMessage(statusId, "error", error.message || "Failed to add arXiv paper", 0, {
        estimatedRemainingMs: 0,
      });
    } finally {
      setUploadingFile(false);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, statusMessages]);

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>DashRAG Chat</title>
        <meta
          name="description"
          content="Chat interface for DashRAG - Document-based AI assistant with knowledge graph"
        />
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1"
        />
        <link
          rel="icon"
          href="/favicon.ico"
        />
      </Head>

      <div className="flex flex-col h-screen">
        <Navbar isHome={false}/>

        <div className="flex-1 overflow-auto sm:px-10 pb-4 sm:pb-10">
          <div className="max-w-[800px] mx-auto mt-4 sm:mt-12">
            {/* Session Title */}
            {sessionId && sessionTitle && (
              <div className="mb-6">
                <h1 className="text-2xl font-bold text-gray-900 mb-2">
                  {sessionTitle}
                </h1>
                <div className="h-px bg-gray-200"></div>
              </div>
            )}
            
            {sessionId ? (
              <Chat
                messages={messages}
                statusMessages={statusMessages}
                documents={documents}
                loading={loading}
                uploadingFile={uploadingFile}
                queryMode={queryMode}
                arxivSearchOpen={arxivSearchOpen}
                arxivQuery={arxivQuery}
                arxivResults={arxivResults}
                arxivSearching={arxivSearching}
                arxivError={arxivError}
                onSend={handleSend}
                onReset={handleReset}
                onFileUpload={handleFileUpload}
                onQueryModeChange={setQueryMode}
                onRefreshDocuments={handleRefreshDocuments}
                onArxivSearchToggle={() => setArxivSearchOpen(!arxivSearchOpen)}
                onArxivQueryChange={setArxivQuery}
                onArxivSearch={handleArxivSearch}
                onAddArxivPaper={handleAddArxivPaper}
              />
            ) : (
              <div className="text-center text-neutral-500 mt-10">
                Initializing session...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>
        <Footer />
      </div>
    </>
  );
}