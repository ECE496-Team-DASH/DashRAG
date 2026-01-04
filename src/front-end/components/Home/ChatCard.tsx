import { useState } from "react";
import { Session } from "@/types";
import { useDraggable, useDroppable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";

interface ChatCardProps {
  session: Session;
  index: number;
  onSelect: (sessionId: string | number) => void;
  onDelete: (sessionId: string | number) => void;
  onRename?: (sessionId: string, newName: string) => void;
  isDragDisabled?: boolean;
}

export const ChatCard = ({ 
  session, 
  index, 
  onSelect, 
  onDelete,
  onRename,
  isDragDisabled = false,
}: ChatCardProps) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(session.title);

  const { attributes, listeners, setNodeRef: setDragRef, transform, isDragging } = useDraggable({
    id: `session-${session.id}`,
    data: { type: 'session', session },
    disabled: isDragDisabled,
  });

  const { setNodeRef: setDropRef, isOver } = useDroppable({
    id: `drop-session-${session.id}`,
    data: { type: 'session', session },
    disabled: isDragDisabled,
  });

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleRename = () => {
    if (editName.trim() && editName.trim() !== session.title && onRename) {
      onRename(session.id, editName.trim());
    }
    setIsEditing(false);
  };

  const documentCount = session.stats?.document_count ?? 0;
  const messageCount = session.stats?.message_count ?? 0;

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={(node) => {
        setDragRef(node);
        setDropRef(node);
      }}
      style={style}
      className={`bg-white rounded-lg shadow-lg border-2 p-4 hover:shadow-xl transition-all duration-200 self-start ${
        isOver ? 'border-blue-500 bg-blue-50 scale-105' : 'border-gray-200'
      } ${isDragging ? 'cursor-grabbing z-50' : 'cursor-grab'}`}
      {...listeners}
      {...attributes}
    >
      <div className="mb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-1">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            {isEditing ? (
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onBlur={handleRename}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleRename();
                  if (e.key === 'Escape') {
                    setEditName(session.title);
                    setIsEditing(false);
                  }
                }}
                className="font-semibold text-gray-800 bg-white border rounded px-2 py-1 flex-1"
                autoFocus
                onClick={(e) => e.stopPropagation()}
                onMouseDown={(e) => e.stopPropagation()}
              />
            ) : (
              <h3
                className="font-semibold text-gray-800 truncate flex-1 cursor-pointer group"
                onDoubleClick={(e) => {
                  e.stopPropagation();
                  if (onRename) {
                    setEditName(session.title);
                    setIsEditing(true);
                  }
                }}
              >
                {session.title}
                {onRename && (
                  <span className="block text-xs text-gray-400 font-normal opacity-0 group-hover:opacity-100 transition-opacity">
                    (double click to edit title)
                  </span>
                )}
              </h3>
            )}
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              e.preventDefault();
              onDelete(session.id);
            }}
            className="text-gray-400 hover:text-red-500 text-sm p-1 cursor-pointer ml-2"
            type="button"
          >
            ✕
          </button>
        </div>
      </div>
      
      <div className="space-y-2 mb-4">
        <div className="flex justify-between text-sm text-gray-600">
          <span>Documents:</span>
          <span className="font-medium">{documentCount}</span>
        </div>
        <div className="flex justify-between text-sm text-gray-600">
          <span>Messages:</span>
          <span className="font-medium">{messageCount}</span>
        </div>
        <div className="text-xs text-gray-500">
          Updated: {formatDate(session.created_at)}
        </div>
      </div>
      
      <button
        onClick={() => onSelect(session.id)}
        className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md text-sm font-medium transition-colors duration-200"
      >
        Open Chat
      </button>
    </div>
  );
};