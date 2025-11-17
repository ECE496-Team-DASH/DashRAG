import { Session } from "@/types";
import Draggable from "react-draggable";

interface DraggableChatCardProps {
  session: Session;
  index: number; // Add index back for grid positioning
  onSelect: (sessionId: string | number) => void;
  onDelete: (sessionId: string | number) => void;
}

export const DraggableChatCard = ({ session, index, onSelect, onDelete }: DraggableChatCardProps) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Safely handle potentially undefined stats
  const documentCount = session.stats?.document_count ?? 0;
  const messageCount = session.stats?.message_count ?? 0;

  // Simple grid positioning: 3 cards per row
  const cardsPerRow = 3;
  const cardWidth = 300; // card width + spacing
  const cardHeight = 280; // card height + spacing
  const startOffset = 20; // offset from container edges

  const gridPosition = {
    x: startOffset + (index % cardsPerRow) * cardWidth,
    y: startOffset + Math.floor(index / cardsPerRow) * cardHeight
  };

  return (
    <Draggable
      handle=".drag-handle"
      bounds="parent"
      defaultPosition={gridPosition}
    >
      <div className="absolute bg-white rounded-lg shadow-lg border border-gray-200 p-4 w-64 cursor-move hover:shadow-xl transition-shadow duration-200">
        <div className="drag-handle mb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <h3 className="font-semibold text-gray-800 truncate flex-1">
                {session.title}
              </h3>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(session.id);
              }}
              className="text-gray-400 hover:text-red-500 text-sm p-1"
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
    </Draggable>
  );
};