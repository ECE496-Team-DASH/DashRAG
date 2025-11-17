import { Footer } from "@/components/Layout/Footer";
import { Navbar } from "@/components/Layout/Navbar";
import { DraggableChatCard } from "@/components/Home/DraggableChatCard";
import { SessionNameModal } from "@/components/Home/SessionNameModal";
import { EmptyState } from "@/components/Home/EmptyState";
import { useSessionManager } from "@/utils/useSessionManager";
import Head from "next/head";

export default function Home() {
  const {
    // State
    sessions,
    loading,
    error,
    creatingSession,
    showNameModal,
    newSessionName,
    
    // Actions
    loadSessions,
    handleCreateNewChat,
    handleCreateWithName,
    handleSelectSession,
    handleDeleteSession,
    handleCloseModal,
    handleSessionNameChange,
  } = useSessionManager();

  return (
    <>
      <Head>
        <title>DashRAG - Chat Management</title>
        <meta
          name="description"
          content="Manage your DashRAG chat sessions with drag-and-drop interface"
        />
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1"
        />
        <link
          rel="icon"
          href="/favicon.ico"
        />
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
            <div className="relative bg-white rounded-lg border border-gray-200 min-h-[600px] p-6">
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
                  <div className="absolute top-4 right-4 text-sm text-gray-500">
                    💡 Drag the cards around to organize them
                  </div>
                  
                  {sessions.map((session, index) => (
                    <DraggableChatCard
                      key={session.id}
                      session={session}
                      index={index}
                      onSelect={handleSelectSession}
                      onDelete={handleDeleteSession}
                    />
                  ))}
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

        <Footer />
      </div>
    </>
  );
}
