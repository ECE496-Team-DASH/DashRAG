import { Document, DocumentStatus } from "@/types";
import { FC, useState } from "react";

interface Props {
  documents: Document[];
  onRefresh: () => void;
}

export const DocumentList: FC<Props> = ({ documents, onRefresh }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const getStatusBadge = (status: DocumentStatus) => {
    const badges = {
      pending: { color: "bg-gray-400", text: "Pending" },
      downloading: { color: "bg-blue-500", text: "Downloading" },
      inserting: { color: "bg-yellow-500", text: "Processing" },
      ready: { color: "bg-green-500", text: "Ready" },
      error: { color: "bg-red-500", text: "Error" },
    };

    const badge = badges[status];
    return (
      <span
        className={`${badge.color} text-white text-xs px-2 py-1 rounded-full`}
      >
        {badge.text}
      </span>
    );
  };

  if (documents.length === 0) {
    return null;
  }

  return (
    <div className="mb-4 border border-neutral-300 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full flex justify-between items-center p-3 bg-neutral-100 hover:bg-neutral-200 transition-colors"
      >
        <span className="font-semibold text-sm">
          Documents ({documents.length})
        </span>
        <span className="text-lg">
          {isCollapsed ? "▶" : "▼"}
        </span>
      </button>

      {!isCollapsed && (
        <div className="p-3 space-y-2 max-h-60 overflow-y-auto">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex justify-between items-center p-2 bg-white border border-neutral-200 rounded"
            >
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">
                  {doc.title}
                </div>
                {doc.arxiv_id && (
                  <div className="text-xs text-neutral-500">
                    arXiv: {doc.arxiv_id}
                  </div>
                )}
                {doc.authors && doc.authors.length > 0 && (
                  <div className="text-xs text-neutral-500 truncate">
                    {doc.authors.slice(0, 2).join(", ")}
                    {doc.authors.length > 2 && ` +${doc.authors.length - 2} more`}
                  </div>
                )}
              </div>
              <div className="ml-2">
                {getStatusBadge(doc.status)}
              </div>
            </div>
          ))}
          
          <button
            onClick={onRefresh}
            className="w-full mt-2 text-sm text-blue-600 hover:text-blue-800 py-1"
          >
            🔄 Refresh Status
          </button>
        </div>
      )}
    </div>
  );
};
