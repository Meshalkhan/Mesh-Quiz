import type {
  ApiErrorBody,
  ChatResponse,
  DocumentDeleteResponse,
  DocumentListResponse,
  DocumentUploadResponse,
  HealthResponse,
  LlmProviderName,
} from "@/types/api";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001/api/v1";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as ApiErrorBody;
    return new ApiError(
      body.error?.message ?? "Request failed",
      body.error?.code ?? "request_failed",
      response.status,
    );
  } catch {
    return new ApiError("Request failed", "request_failed", response.status);
  }
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: "GET",
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as HealthResponse;
}

export async function listDocuments(): Promise<DocumentListResponse> {
  const response = await fetch(`${API_BASE_URL}/documents`, {
    method: "GET",
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as DocumentListResponse;
}

export async function uploadDocument(
  file: File,
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as DocumentUploadResponse;
}

export async function deleteDocument(
  filename: string,
): Promise<DocumentDeleteResponse> {
  const response = await fetch(
    `${API_BASE_URL}/documents/${encodeURIComponent(filename)}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as DocumentDeleteResponse;
}

export async function askQuestion(
  question: string,
  filename: string,
  provider: LlmProviderName,
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question, filename, provider }),
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as ChatResponse;
}
