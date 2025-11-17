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
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<Session | null>(null);

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
      let title = newSessionName.trim() || "New Chat";
      
      // Check if session name already exists and find a unique name
      const existingTitles = sessions.map(session => session.title.toLowerCase());
      let finalTitle = title;
      let counter = 1;
      
      while (existingTitles.includes(finalTitle.toLowerCase())) {
        finalTitle = `${title}(${counter})`;
        counter++;
      }

      const newSession = await dashragAPI.createSession(finalTitle);
      
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
    const session = sessions.find(s => s.id === sessionId);
    if (!session) {
      return;
    }
    
    setSessionToDelete(session);
    setShowDeleteModal(true);
  };

  const confirmDelete = async () => {
    if (!sessionToDelete) return;
    
    setShowDeleteModal(false);
    
    try {
      await dashragAPI.deleteSession(sessionToDelete.id);
      
      setSessions(prev => prev.filter(session => session.id !== sessionToDelete.id));
      
      const currentSessionId = localStorage.getItem("dashrag_session_id");
      if (currentSessionId === sessionToDelete.id.toString()) {
        localStorage.removeItem("dashrag_session_id");
      }
    } catch (err: any) {
      console.error("Failed to delete session:", err);
      alert(err.message || "Failed to delete chat");
    } finally {
      setSessionToDelete(null);
    }
  };

  const cancelDelete = () => {
    setShowDeleteModal(false);
    setSessionToDelete(null);
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
  };
};