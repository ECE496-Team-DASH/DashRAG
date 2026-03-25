import { Message, Citation } from "@/types";
import { FC, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

interface Props {
  message: Message;
}

export const ChatMessage: FC<Props> = ({ message }) => {
  const [showAllCitations, setShowAllCitations] = useState(false);

  const structuredContent = typeof message.content === "string" ? null : message.content;

  // Handle both string content and object content
  const messageText = typeof message.content === "string" 
    ? message.content 
    : structuredContent?.text || "";

  const citations = useMemo(() => structuredContent?.citations || [], [structuredContent]);
  const durationMs = structuredContent?.timing?.duration_ms;

  const formatDuration = (ms?: number) => {
    if (typeof ms !== "number" || ms < 0) return null;
    const totalSeconds = Math.round(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
  };

  const citationSummary = useMemo(() => {
    if (!citations.length) {
      return "";
    }
    const counts = citations.reduce((acc, citation) => {
      acc[citation.type] = (acc[citation.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const parts: string[] = [];
    if (counts.document) parts.push(`${counts.document} document${counts.document > 1 ? "s" : ""}`);
    if (counts.community) parts.push(`${counts.community} communit${counts.community > 1 ? "ies" : "y"}`);
    if (counts.entity) parts.push(`${counts.entity} node${counts.entity > 1 ? "s" : ""}`);
    if (counts.relationship) parts.push(`${counts.relationship} edge${counts.relationship > 1 ? "s" : ""}`);
    if (counts.text_chunk) parts.push(`${counts.text_chunk} text chunk${counts.text_chunk > 1 ? "s" : ""}`);
    return `Sources: ${parts.join(", ")}`;
  }, [citations]);

  const visibleCitations = showAllCitations ? citations : citations.slice(0, 5);

  const formatType = (citation: Citation) => {
    if (citation.type === "text_chunk") return "chunk";
    return citation.type;
  };

  const formatScore = (score?: number) => {
    if (typeof score !== "number") return null;
    return score.toFixed(score >= 1 ? 2 : 3).replace(/\.0+$/, "").replace(/(\.\d*[1-9])0+$/, "$1");
  };

  const formatMetaLine = (citation: Citation) => {
    const parts: string[] = [];
    const score = formatScore(citation.score);
    if (score !== null) {
      parts.push(`score: ${score}`);
    }

    const occurrence = citation.metadata?.occurrence;
    if (typeof occurrence === "number") {
      parts.push(`occurrence: ${occurrence.toFixed(2).replace(/\.00$/, "")}`);
    }

    const chunkCount = citation.metadata?.chunk_count;
    if (typeof chunkCount === "number") {
      parts.push(`chunks: ${chunkCount}`);
    }

    const entityType = citation.metadata?.entity_type;
    if (entityType) {
      parts.push(`type: ${entityType}`);
    }

    return parts.join(" | ");
  };

  return (
    <div className={`flex flex-col ${message.role === "assistant" ? "items-start" : "items-end"}`}>
      <div
        className={`flex items-start ${message.role === "assistant" ? "bg-neutral-200 text-neutral-900" : "bg-blue-500 text-white"} rounded-2xl px-3 py-2 max-w-[67%]`}
        style={{ overflowWrap: "anywhere" }}
      >
        {message.role === "assistant" ? (
          <div className="prose-sm leading-relaxed [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&>h1]:font-bold [&>h2]:font-bold [&>h3]:font-bold [&>ul]:list-disc [&>ul]:pl-4 [&>ol]:list-decimal [&>ol]:pl-4 [&>li]:ml-1 [&_code]:font-mono [&_code]:bg-neutral-300 [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_pre]:bg-neutral-300 [&_pre]:rounded [&_pre]:p-2 [&_pre]:overflow-x-auto [&_pre>code]:bg-transparent [&_pre>code]:p-0 [&>p]:mb-2 [&>blockquote]:border-l-2 [&>blockquote]:border-neutral-400 [&>blockquote]:pl-2 [&>blockquote]:italic">
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[rehypeKatex]}
            >
              {messageText}
            </ReactMarkdown>
          </div>
        ) : (
          <span className="whitespace-pre-wrap">{messageText}</span>
        )}
      </div>

      {message.role === "assistant" && formatDuration(durationMs) && (
        <div className="mt-1 text-[11px] text-neutral-500 max-w-[67%]">
          Answered in {formatDuration(durationMs)}
        </div>
      )}

      {message.role === "assistant" && citations.length > 0 && (
        <div className="mt-2 w-full max-w-[67%] rounded-xl border border-neutral-300 bg-white px-3 py-2 text-xs text-neutral-700">
          <div className="mb-2 font-medium text-neutral-800">{citationSummary}</div>
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {visibleCitations.map((citation) => (
              <div key={citation.id} className="rounded-md border border-neutral-200 bg-neutral-50 px-2 py-1.5">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-neutral-900">{citation.label}</span>
                  <span className="rounded bg-neutral-200 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-neutral-700">
                    {formatType(citation)}
                  </span>
                </div>
                {formatMetaLine(citation) && (
                  <div className="mt-1 text-[11px] text-neutral-500">{formatMetaLine(citation)}</div>
                )}
                {citation.snippet && (
                  <div className="mt-1 text-neutral-600 line-clamp-2">{citation.snippet}</div>
                )}
              </div>
            ))}
          </div>
          {citations.length > 5 && (
            <button
              type="button"
              onClick={() => setShowAllCitations((prev) => !prev)}
              className="mt-2 text-xs font-medium text-blue-700 hover:text-blue-800"
            >
              {showAllCitations ? "Show fewer citations" : `Show ${citations.length - 5} more citations`}
            </button>
          )}
        </div>
      )}
    </div>
  );
};
