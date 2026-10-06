export type ApiErrorBody = {
  success: false;
  error: {
    code: string;
    message: string;
    details: Array<Record<string, unknown>>;
  };
};

export type LlmProviderName = "groq";

export type LlmProviderAvailability = {
  name: LlmProviderName;
  configured: boolean;
};

export type HealthResponse = {
  status: "healthy";
  service: string;
  version: string;
  default_llm_provider: LlmProviderName;
  llm_providers: LlmProviderAvailability[];
};

export type DocumentUploadData = {
  filename: string;
  size: number;
  content_type: string;
  status: "uploaded" | "processed" | "indexed";
  indexed_count: number;
};

export type DocumentUploadResponse = {
  success: true;
  data: DocumentUploadData;
};

export type DocumentSummary = {
  filename: string;
  chunk_count: number;
};

export type DocumentListResponse = {
  success: true;
  data: {
    documents: DocumentSummary[];
  };
};

export type DocumentDeleteResponse = {
  success: true;
  data: {
    filename: string;
    deleted_chunks: number;
    deleted_files: number;
  };
};

export type ChatSource = {
  filename: string;
  page_number: number;
};

export type ChatResponse = {
  answer: string;
  sources: ChatSource[];
};
