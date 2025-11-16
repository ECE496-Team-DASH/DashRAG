export interface Message {
  role: Role;
  content: string | { text: string };
}

export type Role = "assistant" | "user" | "system";

// DashRAG API Types
export type DocumentStatus = "pending" | "downloading" | "inserting" | "ready" | "error";
export type ProcessingPhase = 
  | "pdf_extraction"
  | "text_chunking"
  | "entity_extraction"
  | "graph_clustering"
  | "community_reports"
  | "finalizing";
export type QueryMode = "local" | "global" | "naive";

export interface Session {
  id: string;
  title: string;
  settings: Record<string, any>;
  stats: {
    document_count: number;
    message_count: number;
  };
  created_at: string;
}

export interface Document {
  id: string;
  session_id: string;
  title: string;
  source_type: "upload" | "arxiv";
  status: DocumentStatus;
  processing_phase?: ProcessingPhase;
  progress_percent?: number;
  arxiv_id?: string;
  authors?: string[];
  published_at?: string;
  pages?: number;
  created_at: string;
}

export interface DashRAGMessage {
  id: string;
  session_id: string;
  role: Role;
  content: {
    text: string;
  };
  token_usage?: {
    prompt: number;
    completion: number;
    total: number;
  };
  created_at: string;
}

export interface StatusMessage {
  type: "status";
  status: "uploading" | "processing" | "ready" | "error";
  message: string;
  progress?: number;
  documentId?: string;
}

export interface ArXivPaper {
  arxiv_id: string;
  title: string;
  authors: string;
  abstract: string;
  published_at: string;
  pdf_url: string;
}
