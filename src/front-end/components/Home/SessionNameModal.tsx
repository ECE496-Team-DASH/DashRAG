interface SessionNameModalProps {
  isOpen: boolean;
  sessionName: string;
  creatingSession: boolean;
  onClose: () => void;
  onSessionNameChange: (name: string) => void;
  onCreateSession: () => void;
}

export const SessionNameModal = ({
  isOpen,
  sessionName,
  creatingSession,
  onClose,
  onSessionNameChange,
  onCreateSession
}: SessionNameModalProps) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-96 mx-4">
        <h3 className="text-lg font-semibold mb-4">Create New Chat</h3>
        <input
          type="text"
          value={sessionName}
          onChange={(e) => onSessionNameChange(e.target.value)}
          placeholder="Enter chat name (or leave empty for default)"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              onCreateSession();
            } else if (e.key === 'Escape') {
              onClose();
            }
          }}
          autoFocus
        />
        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={onCreateSession}
            disabled={creatingSession}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-blue-400"
          >
            {creatingSession ? "Creating..." : "Create Chat"}
          </button>
        </div>
      </div>
    </div>
  );
};