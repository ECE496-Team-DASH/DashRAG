import { Footer } from "@/components/Layout/Footer";
import { Navbar } from "@/components/Layout/Navbar";
import { DraggableChatCard } from "@/components/Home/DraggableChatCard";
import { SessionNameModal } from "@/components/Home/SessionNameModal";
import { DeleteConfirmationModal } from "@/components/Home/DeleteConfirmationModal";
import { EmptyState } from "@/components/Home/EmptyState";
import { useSessionManager } from "@/utils/useSessionManager";
import { useState } from "react";
import Head from "next/head";
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
} from "@dnd-kit/core";

export default function Home() {
  const {
    // State
    sessions,
    loading,
    error,
    creatingSession,
    showNameModal,
    newSessionName,
    showDeleteModal,
    sessionToDelete,

    // Actions
    loadSessions,
    handleCreateNewChat,
    handleCreateWithName,
    handleSelectSession,
    handleDeleteSession,
    handleCloseModal,
    handleSessionNameChange,
    confirmDelete,
    cancelDelete,
  } = useSessionManager();

  const [activeId, setActiveId] = useState<string | null>(null);

  // Configure sensors for better drag experience
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor)
  );

  function handleDragStart(event: DragStartEvent) {
    setActiveId(event.active.id as string);
  }

  function handleDragEnd(event: DragEndEvent) {
    // For now, just clear the activeId - you can add your own logic here
    setActiveId(null);
  }

  const getDragOverlayContent = () => {
    if (!activeId) return null;

    // Find the session being dragged
    const session = sessions.find(s => s.id.toString() === activeId);

    if (session) {
      const documentCount = session.stats?.document_count ?? 0;
      const messageCount = session.stats?.message_count ?? 0;
      
      const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        });
      };

      return (
        <div className="bg-white rounded-lg shadow-xl border-2 border-blue-300 p-4 w-64 opacity-90">
          <div className="mb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <h3 className="font-semibold text-gray-800 truncate flex-1">
                  {session.title}
                </h3>
              </div>
              <div className="text-gray-400 text-sm">✕</div>
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
          
          <div className="w-full bg-blue-600 text-white py-2 px-4 rounded-md text-sm font-medium text-center">
            Open Chat
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <>
      <Head>
        <title>DashRAG - Chat Management</title>
        <meta
          name="description"
          content="Manage your DashRAG chat sessions with drag-and-drop interface"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="flex flex-col min-h-screen bg-gray-50">
        <Navbar />

        <main className="flex-1 p-6">
          <div className="max-w-6xl mx-auto">
            {/* Header */}
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Your Chat Sessions
              </h1>
              <p className="text-gray-600 mb-4">
                Drag and drop your chat cards to organize them. Click to open or create new conversations.
              </p>

              <div className="flex gap-4">
                <button
                  onClick={handleCreateNewChat}
                  disabled={creatingSession}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold py-2 px-6 rounded-lg transition-colors duration-200 flex items-center gap-2"
                >
                  {creatingSession ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                      Creating...
                    </>
                  ) : (
                    <>
                      <span className="text-lg">+</span>
                      New Chat
                    </>
                  )}
                </button>

                <button
                  onClick={loadSessions}
                  disabled={loading}
                  className="border border-gray-300 hover:border-gray-400 text-gray-700 font-medium py-2 px-4 rounded-lg transition-colors duration-200"
                >
                  {loading ? "Loading..." : "Refresh"}
                </button>
              </div>
            </div>

            {/* Chat Cards Area */}
            <div className="bg-white rounded-lg border border-gray-200 min-h-[600px] max-h-[600px] overflow-y-auto">
              <EmptyState
                loading={loading}
                error={error}
                sessionsCount={sessions.length}
                creatingSession={creatingSession}
                onRetry={loadSessions}
                onCreateFirst={handleCreateNewChat}
              />

              {sessions.length > 0 && (
                <>
                  {/* Header with tip and count */}
                  <div className="sticky top-0 bg-white z-10 p-6 pb-4 border-b border-gray-100">
                    <div className="flex items-center justify-between text-sm text-gray-500">
                      <span>💡 Drag the cards around to organize them</span>
                      <span className="bg-gray-100 px-2 py-1 rounded-full text-xs font-medium">
                        {sessions.length} session{sessions.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </div>

                  {/* Chat cards in grid */}
                  <div className="p-6 pt-4">
                    <DndContext
                      sensors={sensors}
                      collisionDetection={closestCenter}
                      onDragStart={handleDragStart}
                      onDragEnd={handleDragEnd}
                    >
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {sessions.map((session, index) => (
                          <DraggableChatCard
                            key={session.id}
                            session={session}
                            index={index}
                            onSelect={handleSelectSession}
                            onDelete={handleDeleteSession}
                          />
                        ))}
                      </div>

                      <DragOverlay>
                        {getDragOverlayContent()}
                      </DragOverlay>
                    </DndContext>
                  </div>
                </>
              )}
            </div>
          </div>
        </main>

        <SessionNameModal
          isOpen={showNameModal}
          sessionName={newSessionName}
          creatingSession={creatingSession}
          onClose={handleCloseModal}
          onSessionNameChange={handleSessionNameChange}
          onCreateSession={handleCreateWithName}
        />

        <DeleteConfirmationModal
          isOpen={showDeleteModal}
          sessionTitle={sessionToDelete?.title || ""}
          onConfirm={confirmDelete}
          onCancel={cancelDelete}
        />

        <Footer />
      </div>
    </>
  );
}
