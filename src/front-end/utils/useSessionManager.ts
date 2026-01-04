import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { Session, Folder } from '@/types';
import { dashragAPI } from '@/utils/dashrag-api';

const FOLDERS_STORAGE_KEY = 'dashrag_folders';

export const useSessionManager = () => {
  const router = useRouter();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creatingSession, setCreatingSession] = useState(false);
  const [showNameModal, setShowNameModal] = useState(false);
  const [newSessionName, setNewSessionName] = useState("");
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<Session | null>(null);

  // Load folders from localStorage
  const loadFolders = () => {
    try {
      const stored = localStorage.getItem(FOLDERS_STORAGE_KEY);
      if (stored) {
        setFolders(JSON.parse(stored));
      }
    } catch (err) {
      console.error("Failed to load folders:", err);
    }
  };

  // Save folders to localStorage
  const saveFolders = (newFolders: Folder[]) => {
    localStorage.setItem(FOLDERS_STORAGE_KEY, JSON.stringify(newFolders));
    setFolders(newFolders);
  };

  useEffect(() => {
    loadFolders();
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

  // Create a new folder when two sessions are combined
  const createFolder = (session1Id: string, session2Id: string) => {
    const session1 = sessions.find(s => s.id === session1Id);
    const session2 = sessions.find(s => s.id === session2Id);
    
    if (!session1 || !session2) return;

    // Check if either session is already in a folder
    const existingFolder = folders.find(f => 
      f.sessionIds.includes(session1Id) || f.sessionIds.includes(session2Id)
    );

    if (existingFolder) {
      // Add the other session to the existing folder
      const sessionToAdd = existingFolder.sessionIds.includes(session1Id) ? session2Id : session1Id;
      if (!existingFolder.sessionIds.includes(sessionToAdd)) {
        const updatedFolders = folders.map(f => 
          f.id === existingFolder.id 
            ? { ...f, sessionIds: [...f.sessionIds, sessionToAdd] }
            : f
        );
        saveFolders(updatedFolders);
      }
    } else {
      // Create a new folder
      const newFolder: Folder = {
        id: `folder_${Date.now()}`,
        name: `${session1.title} & ${session2.title}`,
        sessionIds: [session1Id, session2Id],
        created_at: new Date().toISOString(),
      };
      saveFolders([...folders, newFolder]);
    }
  };

  // Add a session to an existing folder
  const addToFolder = (sessionId: string, folderId: string) => {
    const folder = folders.find(f => f.id === folderId);
    if (!folder || folder.sessionIds.includes(sessionId)) return;

    // Remove from any other folder first
    let updatedFolders = folders.map(f => ({
      ...f,
      sessionIds: f.sessionIds.filter(id => id !== sessionId)
    }));

    // Add to target folder
    updatedFolders = updatedFolders.map(f =>
      f.id === folderId
        ? { ...f, sessionIds: [...f.sessionIds, sessionId] }
        : f
    );

    // Remove empty folders
    updatedFolders = updatedFolders.filter(f => f.sessionIds.length > 0);

    saveFolders(updatedFolders);
  };

  // Remove a session from its folder
  const removeFromFolder = (sessionId: string) => {
    let updatedFolders = folders.map(f => ({
      ...f,
      sessionIds: f.sessionIds.filter(id => id !== sessionId)
    }));

    // Remove folders with less than 2 sessions
    updatedFolders = updatedFolders.filter(f => f.sessionIds.length >= 2);

    saveFolders(updatedFolders);
  };

  // Delete a folder (sessions remain)
  const deleteFolder = (folderId: string) => {
    const updatedFolders = folders.filter(f => f.id !== folderId);
    saveFolders(updatedFolders);
  };

  // Rename a folder
  const renameFolder = (folderId: string, newName: string) => {
    const updatedFolders = folders.map(f =>
      f.id === folderId ? { ...f, name: newName } : f
    );
    saveFolders(updatedFolders);
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
      
      // Also remove from any folder
      removeFromFolder(sessionToDelete.id);
      
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
  };
};