import { useState } from "react";
import { Session, Folder } from "@/types";
import { useDroppable } from "@dnd-kit/core";
import { ChatCard } from "./ChatCard";

interface FolderCardProps {
  folder: Folder;
  sessions: Session[];
  onSelectSession: (sessionId: string | number) => void;
  onDeleteSession: (sessionId: string | number) => void;
  onDeleteFolder: (folderId: string) => void;
  onRenameFolder: (folderId: string, newName: string) => void;
  onRemoveFromFolder: (sessionId: string) => void;
}

export const FolderCard = ({
  folder,
  sessions,
  onSelectSession,
  onDeleteSession,
  onDeleteFolder,
  onRenameFolder,
  onRemoveFromFolder,
}: FolderCardProps) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(folder.name);

  const { setNodeRef, isOver } = useDroppable({
    id: `folder-${folder.id}`,
    data: { type: 'folder', folder },
  });

  const folderSessions = sessions.filter(s => folder.sessionIds.includes(s.id));

  const handleRename = () => {
    if (editName.trim()) {
      onRenameFolder(folder.id, editName.trim());
    }
    setIsEditing(false);
  };

  return (
    <div
      ref={setNodeRef}
      className={`bg-amber-50 rounded-lg shadow-lg border-2 p-4 transition-all duration-200 ${
        isOver ? 'border-blue-500 bg-blue-50 scale-105' : 'border-amber-300'
      }`}
    >
      <div className="mb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-1">
            <span className="text-xl">📁</span>
            {isEditing ? (
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onBlur={handleRename}
                onKeyDown={(e) => e.key === 'Enter' && handleRename()}
                className="font-semibold text-gray-800 bg-white border rounded px-2 py-1 flex-1"
                autoFocus
              />
            ) : (
              <h3
                className="font-semibold text-gray-800 truncate flex-1 cursor-pointer"
                onDoubleClick={() => setIsEditing(true)}
                title="Double-click to rename"
              >
                {folder.name}
              </h3>
            )}
          </div>
          <button
            onClick={() => onDeleteFolder(folder.id)}
            className="text-gray-400 hover:text-red-500 text-sm p-1 cursor-pointer ml-2"
            title="Delete folder (keeps sessions)"
          >
            ✕
          </button>
        </div>
        <div className="text-xs text-gray-500 mt-1">
          {folderSessions.length} session{folderSessions.length !== 1 ? 's' : ''}
        </div>
      </div>

      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full bg-amber-500 hover:bg-amber-600 text-white py-2 px-4 rounded-md text-sm font-medium transition-colors duration-200 flex items-center justify-center gap-2"
      >
        {isExpanded ? '▼ Collapse' : '▶ Expand'}
      </button>

      {isExpanded && (
        <div className="mt-4 space-y-3">
          {folderSessions.map((session, index) => (
            <div key={session.id} className="relative">
              <button
                onClick={() => onRemoveFromFolder(session.id)}
                className="absolute -top-2 -right-2 z-10 bg-gray-200 hover:bg-gray-300 rounded-full w-6 h-6 text-xs flex items-center justify-center"
                title="Remove from folder"
              >
                ↗
              </button>
              <ChatCard
                session={session}
                index={index}
                onSelect={onSelectSession}
                onDelete={onDeleteSession}
                isDragDisabled={true}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
