// Typed client for the Sanad FastAPI backend.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type DocumentInfo = {
  id: string;
  filename: string;
  status: "processing" | "ready" | "failed";
  error: string | null;
  page_count: number | null;
};

export type Citation = {
  number: number;
  document_id: string;
  page: number;
  content: string;
};

export type AskResult = {
  answer: string;
  language: "en" | "ar";
  found: boolean;
  citations: Citation[];
};

export type EvalScores = {
  kind: "answerable" | "unanswerable";
  found: boolean;
  latency_ms: number;
  reference_answer?: string;
  retrieval_hit?: boolean;
  cited_expected?: boolean | null;
  faithful?: boolean | null;
  correct?: boolean | null;
};

export type EvalMetrics = {
  questions: number;
  retrieval_hit_rate: number | null;
  answer_rate: number | null;
  citation_accuracy: number | null;
  faithfulness: number | null;
  correctness: number | null;
  refusal_rate: number | null;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  by_language: Partial<Record<"en" | "ar", { questions: number; correctness: number | null }>>;
  error?: string;
};

export type EvalReport = {
  run_id: string;
  status: "running" | "done" | "failed";
  created_at: string;
  metrics: EvalMetrics | null;
  items: { question: string; language: "en" | "ar"; answer: string; scores: EvalScores }[];
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(0, "network");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : `Request failed (${response.status})`;
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  createDemo: () => request<{ public_key: string; expires_in_hours: number }>("/demo/workspaces", { method: "POST" }),

  listDocuments: (key: string) => request<DocumentInfo[]>(`/w/${key}/documents`),

  upload: (key: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentInfo>(`/w/${key}/documents`, { method: "POST", body: form });
  },

  ask: (key: string, question: string) => request<AskResult>(`/w/${key}/ask`, json({ question })),

  startEvaluation: (key: string) =>
    request<{ run_id: string; status: string }>(`/w/${key}/evaluations`, { method: "POST" }),

  getEvaluation: (key: string, runId: string) => request<EvalReport>(`/w/${key}/evaluations/${runId}`),
};
