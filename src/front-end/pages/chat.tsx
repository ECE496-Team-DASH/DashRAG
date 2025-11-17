import { Chat } from "@/components/Chat/Chat";
import { Footer } from "@/components/Layout/Footer";
import { Navbar } from "@/components/Layout/Navbar";
import { Message, Document, QueryMode, StatusMessage as StatusMsg, ProcessingPhase, ArXivPaper } from "@/types";
import { dashragAPI } from "@/utils/dashrag-api";
import Head from "next/head";
import { useEffect, useRef, useState } from "react";

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

  // Initialize or restore session
  useEffect(() => {
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
  }, []);

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
    progress?: number
  ) => {
    const statusMsg: StatusMsg = {
      type: "status",
      status,
      message,
      progress,
    };
    setStatusMessages((prev) => [...prev, statusMsg]);
    setTimeout(() => scrollToBottom(), 100);
  };

  const updateLastStatusMessage = (
    status: "uploading" | "processing" | "ready" | "error",
    message: string,
    progress?: number
  ) => {
    setStatusMessages((prev) => {
      const updated = [...prev];
      if (updated.length > 0) {
        updated[updated.length - 1] = {
          type: "status",
          status,
          message,
          progress,
        };
      }
      return updated;
    });
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
    addStatusMessage("uploading", `📤 Uploading ${file.name}...`, 0);

    try {
      // Upload the file
      const doc = await dashragAPI.uploadDocument(sessionId, file);
      
      updateLastStatusMessage("processing", `⏳ Processing ${file.name}...`, 5);

      // Use SSE to stream progress updates
      const API_BASE = process.env.NEXT_PUBLIC_DASHRAG_API_URL || "http://localhost:8000";
      const eventSource = new EventSource(
        `${API_BASE}/documents/progress-stream?sid=${sessionId}&doc_id=${doc.id}`
      );

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.event === "complete") {
            if (data.status === "ready") {
              updateLastStatusMessage("ready", `✅ ${file.name} is ready!`, 100);
            } else if (data.status === "error") {
              updateLastStatusMessage("error", `❌ Failed to process ${file.name}`, 0);
            }
            eventSource.close();
            loadDocuments(sessionId);
            setUploadingFile(false);
          } else if (data.event === "error") {
            updateLastStatusMessage("error", data.message || "Processing failed", 0);
            eventSource.close();
            setUploadingFile(false);
          } else {
            // Regular progress update
            const phaseMsg = getPhaseDescription(data.processing_phase);
            const progress = data.progress_percent || 10;
            updateLastStatusMessage("processing", phaseMsg, progress);
          }
        } catch (e) {
          console.error("Error parsing SSE data:", e);
        }
      };

      eventSource.onerror = (error) => {
        console.error("SSE error:", error);
        updateLastStatusMessage("error", "Connection error during processing", 0);
        eventSource.close();
        setUploadingFile(false);
      };

    } catch (error: any) {
      console.error("Upload error:", error);
      updateLastStatusMessage("error", error.message || "Upload failed");
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

    try {
      // Call the API through Next.js API route
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          sessionId,
          content: messageText,
          mode: queryMode,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to send message");
      }

      const data = await response.json();
      
      // API returns {message: {content: {text: "..."}}}
      if (data.message && data.message.content) {
        const assistantMessage: Message = {
          role: "assistant",
          content: typeof data.message.content === "string" 
            ? data.message.content 
            : data.message.content.text,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        throw new Error("Invalid response format from API");
      }
    } catch (error: any) {
      console.error("Send message error:", error);
      const errorMessage: Message = {
        role: "assistant",
        content: `Error: ${error.message || "Failed to get response"}`,
      };
      setMessages((prev) => [...prev, errorMessage]);
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
    addStatusMessage("uploading", `📥 Adding arXiv paper ${arxivId}...`, 0);

    try {
      const doc = await dashragAPI.addArxivPaper(sessionId, arxivId);
      
      updateLastStatusMessage("processing", `⏳ Downloading arXiv:${arxivId}...`, 5);

      // Use SSE to stream progress updates
      const API_BASE = process.env.NEXT_PUBLIC_DASHRAG_API_URL || "http://localhost:8000";
      const eventSource = new EventSource(
        `${API_BASE}/documents/progress-stream?sid=${sessionId}&doc_id=${doc.id}`
      );

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.event === "complete") {
            if (data.status === "ready") {
              updateLastStatusMessage("ready", `✅ arXiv:${arxivId} is ready!`, 100);
            } else if (data.status === "error") {
              updateLastStatusMessage("error", `❌ Failed to process arXiv:${arxivId}`, 0);
            }
            eventSource.close();
            loadDocuments(sessionId);
            setUploadingFile(false);
          } else if (data.event === "error") {
            updateLastStatusMessage("error", data.message || "Processing failed", 0);
            eventSource.close();
            setUploadingFile(false);
          } else {
            // Regular progress update
            const phaseMsg = getPhaseDescription(data.processing_phase);
            const progress = data.progress_percent || 10;
            updateLastStatusMessage("processing", `${phaseMsg} (arXiv:${arxivId})`, progress);
          }
        } catch (e) {
          console.error("Error parsing SSE data:", e);
        }
      };

      eventSource.onerror = (error) => {
        console.error("SSE error:", error);
        updateLastStatusMessage("error", "Connection error during processing", 0);
        eventSource.close();
        setUploadingFile(false);
      };

    } catch (error: any) {
      console.error("arXiv error:", error);
      updateLastStatusMessage("error", error.message || "Failed to add arXiv paper");
      setUploadingFile(false);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, statusMessages]);

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
        <Navbar />

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