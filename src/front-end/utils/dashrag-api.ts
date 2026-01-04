import { Session, Document, DashRAGMessage, QueryMode, ArXivPaper } from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_DASHRAG_API_URL || "http://localhost:8000";

export const dashragAPI = {
  // Session Management
  async createSession(title: string = "New Chat"): Promise<Session> {
    const response = await fetch(`${API_BASE_URL}/sessions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.statusText}`);
    }
    
    return response.json();
  },

  async getSession(sessionId: string): Promise<Session> {
    const response = await fetch(`${API_BASE_URL}/sessions/detail?sid=${sessionId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get session: ${response.statusText}`);
    }
    
    return response.json();
  },

  async listSessions(): Promise<Session[]> {
    const response = await fetch(`${API_BASE_URL}/sessions`);
    
    if (!response.ok) {
      throw new Error(`Failed to list sessions: ${response.statusText}`);
    }
    
    return response.json();
  },

  async deleteSession(sessionId: string | number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/sessions?sid=${sessionId}`, {
      method: "DELETE",
    });
    
    if (!response.ok) {
      throw new Error(`Failed to delete session: ${response.statusText}`);
    }
  },

  async renameSession(sessionId: string | number, title: string): Promise<Session> {
    const response = await fetch(`${API_BASE_URL}/sessions?sid=${sessionId}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to rename session: ${response.statusText}`);
    }
    
    return response.json();
  },

  // Document Management
  async uploadDocument(sessionId: string, file: File): Promise<Document> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/documents/upload?sid=${sessionId}`, {
      method: "POST",
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to upload document: ${error}`);
    }
    
    return response.json();
  },

  async addArxivPaper(sessionId: string, arxivId: string): Promise<Document> {
    const response = await fetch(`${API_BASE_URL}/documents/add-arxiv?sid=${sessionId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ arxiv_id: arxivId }),
    });
    
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to add arXiv paper: ${error}`);
    }
    
    return response.json();
  },

  async getDocuments(sessionId: string): Promise<Document[]> {
    const response = await fetch(`${API_BASE_URL}/documents?sid=${sessionId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get documents: ${response.statusText}`);
    }
    
    return response.json();
  },

  // Message/Query
  async sendMessage(
    sessionId: string,
    content: string,
    mode: QueryMode = "local"
  ): Promise<DashRAGMessage> {
    const response = await fetch(`${API_BASE_URL}/messages?sid=${sessionId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ content, mode }),
    });
    
    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Failed to send message: ${error}`);
    }
    
    const data = await response.json();
    return data.message;
  },

  async getMessages(sessionId: string): Promise<DashRAGMessage[]> {
    const response = await fetch(`${API_BASE_URL}/messages?sid=${sessionId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get messages: ${response.statusText}`);
    }
    
    return response.json();
  },

  // ArXiv Search
  async searchArxiv(query: string, maxResults: number = 5): Promise<ArXivPaper[]> {
    const response = await fetch(
      `${API_BASE_URL}/papers/search?query=${encodeURIComponent(query)}&max_results=${maxResults}`
    );
    
    if (!response.ok) {
      throw new Error(`Failed to search arXiv: ${response.statusText}`);
    }
    
    return response.json();
  },

  // Utility function to poll document status
  async pollDocumentStatus(
    sessionId: string,
    documentId: string,
    onStatusUpdate: (status: string, progress: number) => void,
    maxAttempts: number = 60
  ): Promise<Document> {
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      const documents = await this.getDocuments(sessionId);
      const doc = documents.find(d => d.id === documentId);
      
      if (!doc) {
        throw new Error("Document not found");
      }
      
      // Calculate simulated progress based on status
      let progress = 0;
      if (doc.status === "pending") progress = 10;
      else if (doc.status === "downloading") progress = 30;
      else if (doc.status === "inserting") progress = 50 + (attempts * 2); // Simulate 50-90%
      else if (doc.status === "ready") progress = 100;
      else if (doc.status === "error") progress = 0;
      
      onStatusUpdate(doc.status, Math.min(progress, 90));
      
      if (doc.status === "ready" || doc.status === "error") {
        onStatusUpdate(doc.status, 100);
        return doc;
      }
      
      await new Promise(resolve => setTimeout(resolve, 2000)); // Poll every 2 seconds
      attempts++;
    }
    
    throw new Error("Document processing timeout");
  }
};
