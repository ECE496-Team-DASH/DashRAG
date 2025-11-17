import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { Session } from '@/types';
import { dashragAPI } from '@/utils/dashrag-api';

export const useSessionManager = () => {
  const router = useRouter();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creatingSession, setCreatingSession] = useState(false);
  const [showNameModal, setShowNameModal] = useState(false);
  const [newSessionName, setNewSessionName] = useState("");

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      setError(null);
      const sessionList = await dashragAPI.listSessions();
      setSessions(sessionList);
    } catch (err: any) {
      console.error("Failed to load sessions:", err);
      setError(err.message || "Failed to load sessions");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNewChat = () => {
    setNewSessionName("");
    setShowNameModal(true);
  };

  const handleCreateWithName = async () => {
    setShowNameModal(false);
    try {
      setCreatingSession(true);
      // Use "New Chat" as default if name is empty or just whitespace
      const title = newSessionName.trim() || "New Chat";
      const newSession = await dashragAPI.createSession(title);
      
      localStorage.setItem("dashrag_session_id", newSession.id.toString());
      router.push("/chat");
    } catch (err: any) {
      console.error("Failed to create session:", err);
      alert(err.message || "Failed to create new chat");
    } finally {
      setCreatingSession(false);
    }
  };

  const handleSelectSession = (sessionId: string | number) => {
    localStorage.setItem("dashrag_session_id", sessionId.toString());
    router.push("/chat");
  };

  const handleDeleteSession = async (sessionId: string | number) => {
    if (!confirm("Are you sure you want to delete this chat? This action cannot be undone.")) {
      return;
    }

    try {
      // Actually delete from the API/database
      await dashragAPI.deleteSession(sessionId);
      
      // Remove from UI state after successful deletion
      setSessions(prev => prev.filter(session => session.id !== sessionId));
      
      // Clear localStorage if this was the active session
      const currentSessionId = localStorage.getItem("dashrag_session_id");
      if (currentSessionId === sessionId.toString()) {
        localStorage.removeItem("dashrag_session_id");
      }
    } catch (err: any) {
      console.error("Failed to delete session:", err);
      alert(err.message || "Failed to delete chat");
    }
  };

  const handleCloseModal = () => {
    setShowNameModal(false);
  };

  const handleSessionNameChange = (name: string) => {
    setNewSessionName(name);
  };

  return {
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
  };
};