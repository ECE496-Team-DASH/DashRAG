export type CitationType = "document" | "community" | "entity" | "relationship" | "text_chunk";

export interface Citation {
  id: string;
  type: CitationType;
  label: string;
  snippet?: string;
  score?: number;
  metadata?: {
    file_name?: string;
    occurrence?: number;
    chunk_count?: number;
    full_doc_id?: string;
    chunk_order_index?: string | number;
    entity_type?: string;
    weight?: number;
    community_id?: string;
    [key: string]: any;
  };
}

export interface MessageContent {
  text: string;
  citations?: Citation[];
}

export interface Message {
  role: Role;
  content: string | MessageContent;
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
  stats?: {
    document_count?: number;
    message_count?: number;
    graph_exists?: boolean;
  };
  created_at: string;
  updated_at: string;
  folderId?: string; // ID of folder this session belongs to
}

export interface Folder {
  id: string;
  name: string;
  sessionIds: string[];
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
  content: MessageContent;
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
  pdf_size_mb?: number;
}

export interface User {
  id: number;
  email: string;
  created_at?: string;
}
