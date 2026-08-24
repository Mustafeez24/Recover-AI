// A thin typed wrapper over the existing FastAPI backend. Every function
// here maps 1:1 to an existing endpoint (see backend/app/api/) -- no
// business logic is duplicated here, this only shapes requests/responses.

import type {
  ActionSummary,
  AIBatchResult,
  AIRecommendResult,
  AISummary,
  DataSummary,
  DetectResult,
  DetectionSummary,
  ExecuteResult,
  HistoryResponse,
  OpportunityDetail,
  OpportunityFilters,
  OpportunityListResponse,
  PlanResult,
  ValidateResult,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // response body wasn't JSON -- fall back to statusText
    }
    throw new ApiError(response.status, detail);
  }

  return response.json() as Promise<T>;
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

// --- Phase 1/2: health + data ---

export function getHealth() {
  return request<{ status: string }>("/health");
}

export function getDataSummary() {
  return request<DataSummary>("/api/data/summary");
}

// --- Phase 3: detection ---

export function runDetection() {
  return request<DetectResult>("/api/recovery/detect", { method: "POST" });
}

export function getDetectionSummary() {
  return request<DetectionSummary>("/api/recovery/summary");
}

export function listOpportunities(filters: OpportunityFilters = {}) {
  const query = buildQuery({
    priority: filters.priority,
    status: filters.status,
    failure_category: filters.failure_category,
    min_amount: filters.min_amount,
    max_amount: filters.max_amount,
    limit: filters.limit ?? 25,
    offset: filters.offset ?? 0,
  });
  return request<OpportunityListResponse>(`/api/recovery/opportunities${query}`);
}

export function getOpportunity(id: string) {
  return request<OpportunityDetail>(`/api/recovery/opportunities/${encodeURIComponent(id)}`);
}

// --- Phase 4: plan / validate / execute / history (per-case only --
// there is deliberately no bulk-execute endpoint) ---

export function planAction(id: string) {
  return request<PlanResult>(`/api/recovery/opportunities/${encodeURIComponent(id)}/plan`, {
    method: "POST",
  });
}

export function validateAction(id: string) {
  return request<ValidateResult>(`/api/recovery/opportunities/${encodeURIComponent(id)}/validate`, {
    method: "POST",
  });
}

export function executeAction(id: string) {
  return request<ExecuteResult>(`/api/recovery/opportunities/${encodeURIComponent(id)}/execute`, {
    method: "POST",
  });
}

export function getHistory(id: string) {
  return request<HistoryResponse>(`/api/recovery/opportunities/${encodeURIComponent(id)}/history`);
}

export function getActionSummary() {
  return request<ActionSummary>("/api/recovery/action-summary");
}

// --- Phase 5: AI recommendations (advisory only) ---

export function getAIRecommendation(id: string) {
  return request<AIRecommendResult>(`/api/recovery/opportunities/${encodeURIComponent(id)}/ai-recommend`, {
    method: "POST",
  });
}

export function runAIBatchAnalysis(batchSize = 10) {
  return request<AIBatchResult>(`/api/recovery/ai/analyze${buildQuery({ batch_size: batchSize })}`, {
    method: "POST",
  });
}

export function getAISummary() {
  return request<AISummary>("/api/recovery/ai-summary");
}
