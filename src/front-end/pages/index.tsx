import { Footer } from "@/components/Layout/Footer";
import { Navbar } from "@/components/Layout/Navbar";
import { ChatCard } from "@/components/Home/ChatCard";
import { FolderCard } from "@/components/Home/FolderCard";
import { SessionNameModal } from "@/components/Home/SessionNameModal";
import { DeleteConfirmationModal } from "@/components/Home/DeleteConfirmationModal";
import { EmptyState } from "@/components/Home/EmptyState";
import { useSessionManager } from "@/utils/useSessionManager";
import Head from "next/head";
import { DndContext, DragEndEvent, DragOverlay, DragStartEvent, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { useState } from "react";
import { Session } from "@/types";

export default function Home() {
  const {
    // State
    sessions,
    folders,
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

    // Folder actions
    createFolder,
    addToFolder,
    removeFromFolder,
    deleteFolder,
    renameFolder,
  } = useSessionManager();

  const [activeSession, setActiveSession] = useState<Session | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  // Get sessions that are not in any folder
  const unfolderSessionIds = folders.flatMap(f => f.sessionIds);
  const standaloneSessions = sessions.filter(s => !unfolderSessionIds.includes(s.id));

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    if (active.data.current?.type === 'session') {
      setActiveSession(active.data.current.session);
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveSession(null);

    if (!over) return;

    const activeData = active.data.current;
    const overData = over.data.current;

    if (!activeData || !overData) return;

    // Dragging a session
    if (activeData.type === 'session') {
      const draggedSessionId = activeData.session.id;

      // Dropped on another session -> create folder
      if (overData.type === 'session') {
        const targetSessionId = overData.session.id;
        if (draggedSessionId !== targetSessionId) {
          createFolder(draggedSessionId, targetSessionId);
        }
      }
      // Dropped on a folder -> add to folder
      else if (overData.type === 'folder') {
        addToFolder(draggedSessionId, overData.folder.id);
      }
    }
  };

  const totalItems = folders.length + standaloneSessions.length;

  return (
    <>
      <Head>
        <title>DashRAG - Chat Management</title>
        <meta
          name="description"
          content="Manage your DashRAG chat sessions"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="flex flex-col min-h-screen bg-gray-50">
        <Navbar isHome={true}/>

        <main className="flex-1 p-6">
          <div className="max-w-6xl mx-auto">
            {/* Header */}
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Your Chat Sessions
              </h1>
              <p className="text-gray-600 mb-4">
                Click to open or create new conversations. Drag and drop sessions onto each other to create folders.
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
                <DndContext
                  sensors={sensors}
                  onDragStart={handleDragStart}
                  onDragEnd={handleDragEnd}
                >
                  {/* Header with count */}
                  <div className="sticky top-0 bg-white z-10 p-6 pb-4 border-b border-gray-100">
                    <div className="flex items-center justify-between text-sm text-gray-500">
                      <span>📚 Your chat sessions</span>
                      <span className="bg-gray-100 px-2 py-1 rounded-full text-xs font-medium">
                        {sessions.length} session{sessions.length !== 1 ? 's' : ''} • {folders.length} folder{folders.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </div>

                  {/* Folders and Chat cards in grid */}
                  <div className="p-6 pt-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {/* Render folders first */}
                      {folders.map((folder) => (
                        <FolderCard
                          key={folder.id}
                          folder={folder}
                          sessions={sessions}
                          onSelectSession={handleSelectSession}
                          onDeleteSession={handleDeleteSession}
                          onDeleteFolder={deleteFolder}
                          onRenameFolder={renameFolder}
                          onRemoveFromFolder={removeFromFolder}
                        />
                      ))}
                      {/* Render standalone sessions */}
                      {standaloneSessions.map((session, index) => (
                        <ChatCard
                          key={session.id}
                          session={session}
                          index={index}
                          onSelect={handleSelectSession}
                          onDelete={handleDeleteSession}
                        />
                      ))}
                    </div>
                  </div>

                  <DragOverlay>
                    {activeSession ? (
                      <div className="bg-white rounded-lg shadow-2xl border-2 border-blue-500 p-4 opacity-90 w-72">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                          <h3 className="font-semibold text-gray-800 truncate">
                            {activeSession.title}
                          </h3>
                        </div>
                      </div>
                    ) : null}
                  </DragOverlay>
                </DndContext>
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
