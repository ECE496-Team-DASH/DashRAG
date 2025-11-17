interface EmptyStateProps {
  loading: boolean;
  error: string | null;
  sessionsCount: number;
  creatingSession: boolean;
  onRetry: () => void;
  onCreateFirst: () => void;
}

export const EmptyState = ({
  loading,
  error,
  sessionsCount,
  creatingSession,
  onRetry,
  onCreateFirst
}: EmptyStateProps) => {
  if (loading && sessionsCount === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent mx-auto mb-4"></div>
          <p className="text-gray-500">Loading your chats...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="text-red-500 text-4xl mb-4">⚠️</div>
          <p className="text-red-600 font-medium mb-2">Error loading chats</p>
          <p className="text-gray-500 mb-4">{error}</p>
          <button
            onClick={onRetry}
            className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (sessionsCount === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="text-gray-400 text-6xl mb-4">💬</div>
          <h3 className="text-lg font-medium text-gray-700 mb-2">No chats yet</h3>
          <p className="text-gray-500 mb-4">Create your first chat to get started</p>
          <button
            onClick={onCreateFirst}
            disabled={creatingSession}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-2 px-6 rounded-lg"
          >
            {creatingSession ? "Creating..." : "New Chat"}
          </button>
        </div>
      </div>
    );
  }

  return null;
};