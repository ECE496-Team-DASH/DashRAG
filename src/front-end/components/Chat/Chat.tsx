import { Message, Document, QueryMode, StatusMessage as StatusMsg, ArXivPaper } from "@/types";
import { FC, useRef } from "react";
import { ChatInput } from "./ChatInput";
import { ChatLoader } from "./ChatLoader";
import { ChatMessage } from "./ChatMessage";
import { ResetChat } from "./ResetChat";
import { StatusMessage } from "./StatusMessage";
import { DocumentList } from "./DocumentList";

interface Props {
  messages: Message[];
  statusMessages: StatusMsg[];
  documents: Document[];
  loading: boolean;
  uploadingFile: boolean;
  queryMode: QueryMode;
  arxivSearchOpen: boolean;
  arxivQuery: string;
  arxivResults: ArXivPaper[];
  arxivSearching: boolean;
  arxivError: string | null;
  onSend: (message: Message) => void;
  onReset: () => void;
  onFileUpload: (file: File) => void;
  onQueryModeChange: (mode: QueryMode) => void;
  onRefreshDocuments: () => void;
  onArxivSearchToggle: () => void;
  onArxivQueryChange: (query: string) => void;
  onArxivSearch: () => void;
  onAddArxivPaper: (arxivId: string) => void;
}

export const Chat: FC<Props> = ({
  messages,
  statusMessages,
  documents,
  loading,
  uploadingFile,
  queryMode,
  arxivSearchOpen,
  arxivQuery,
  arxivResults,
  arxivSearching,
  arxivError,
  onSend,
  onReset,
  onFileUpload,
  onQueryModeChange,
  onRefreshDocuments,
  onArxivSearchToggle,
  onArxivQueryChange,
  onArxivSearch,
  onAddArxivPaper,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onFileUpload(file);
      // Reset input so same file can be uploaded again
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <>
      <div className="flex flex-row justify-between items-center mb-4 sm:mb-8">
        <ResetChat onReset={onReset} />
      </div>

      <DocumentList documents={documents} onRefresh={onRefreshDocuments} />

      {/* Controls Panel */}
      <div className="mb-4 p-3 border border-neutral-300 rounded-lg bg-neutral-50">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* File Upload */}
          <div>
            <label className="block text-xs font-semibold text-neutral-700 mb-1">
              Upload PDF
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileSelect}
              disabled={uploadingFile}
              className="text-sm w-full file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:text-sm file:bg-blue-500 file:text-white hover:file:bg-blue-600 file:cursor-pointer disabled:opacity-50"
            />
          </div>

          {/* Query Mode */}
          <div>
            <label className="block text-xs font-semibold text-neutral-700 mb-1">
              Query Mode
            </label>
            <select
              value={queryMode}
              onChange={(e) => onQueryModeChange(e.target.value as QueryMode)}
              className="text-sm w-full px-3 py-1.5 border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="local">Local (Specific)</option>
              <option value="global">Global (Synthesis)</option>
              <option value="naive">Naive (Quick)</option>
            </select>
          </div>
        </div>
      </div>

      {/* ArXiv Search Section */}
      <div className="mb-4 border border-neutral-300 rounded-lg bg-white overflow-hidden">
        <button
          onClick={onArxivSearchToggle}
          className="w-full px-4 py-3 flex items-center justify-between text-left bg-neutral-50 hover:bg-neutral-100 transition-colors"
        >
          <span className="font-semibold text-neutral-700">
            📚 Browse arXiv Papers
          </span>
          <span className="text-neutral-500">
            {arxivSearchOpen ? '▼' : '▶'}
          </span>
        </button>
        
        {arxivSearchOpen && (
          <div className="p-4 space-y-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={arxivQuery}
                onChange={(e) => onArxivQueryChange(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !arxivSearching) {
                    onArxivSearch();
                  }
                }}
                placeholder="Search arXiv (e.g., 'transformer attention mechanism')"
                disabled={arxivSearching || uploadingFile}
                className="flex-1 px-3 py-2 border border-neutral-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 text-sm"
              />
              <button
                onClick={onArxivSearch}
                disabled={arxivSearching || uploadingFile || !arxivQuery.trim()}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm"
              >
                {arxivSearching ? 'Searching...' : 'Search'}
              </button>
            </div>

            {arxivError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                {arxivError}
              </div>
            )}

            {arxivResults.length > 0 && (
              <div className="space-y-3">
                <p className="text-sm text-neutral-600">
                  Found {arxivResults.length} paper{arxivResults.length !== 1 ? 's' : ''}:
                </p>
                {arxivResults.map((paper) => (
                  <div
                    key={paper.arxiv_id}
                    className="p-3 border border-neutral-200 rounded-lg hover:border-neutral-300 transition-colors"
                  >
                    <div className="flex justify-between items-start gap-3">
                      <div className="flex-1 min-w-0">
                        <h4 className="font-semibold text-neutral-800 text-sm mb-1">
                          {paper.title}
                        </h4>
                        <p className="text-xs text-neutral-600 mb-1">
                          {paper.authors.split(',').slice(0, 3).join(',')}
                          {paper.authors.split(',').length > 3 && ', et al.'}
                        </p>
                        <p className="text-xs text-neutral-500 mb-2">
                          arXiv:{paper.arxiv_id} • {new Date(paper.published_at).toLocaleDateString()}
                        </p>
                        <p className="text-xs text-neutral-700 line-clamp-2">
                          {paper.abstract}
                        </p>
                      </div>
                      <button
                        onClick={() => onAddArxivPaper(paper.arxiv_id)}
                        disabled={uploadingFile || documents.some(d => d.arxiv_id === paper.arxiv_id)}
                        className="flex-shrink-0 px-3 py-1.5 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed text-xs font-medium"
                      >
                        {documents.some(d => d.arxiv_id === paper.arxiv_id) ? 'Added' : 'Add'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex flex-col rounded-lg px-2 sm:p-4 sm:border border-neutral-300">
        {messages.map((message, index) => (
          <div
            key={index}
            className="my-1 sm:my-1.5"
          >
            <ChatMessage message={message} />
          </div>
        ))}

        {statusMessages.map((statusMsg, index) => (
          <div key={`status-${index}`}>
            <StatusMessage
              status={statusMsg.status}
              message={statusMsg.message}
              progress={statusMsg.progress}
            />
          </div>
        ))}

        {loading && (
          <div className="my-1 sm:my-1.5">
            <ChatLoader />
          </div>
        )}

        <div className="mt-4 sm:mt-8 bottom-[56px] left-0 w-full">
          <ChatInput onSend={onSend} />
        </div>
      </div>
    </>
  );
};
