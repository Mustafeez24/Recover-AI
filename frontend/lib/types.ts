// Types mirror the existing FastAPI response shapes exactly (see
// backend/app/api/data.py and backend/app/api/recovery.py). No business
// logic lives here -- this is a thin typed reflection of the backend
// contract the UI reads, per the "don't duplicate business logic in the
// frontend" constraint.

export type Priority = "high" | "medium" | "low";

export type FailureCategory =
  | "temporary_failure"
  | "insufficient_funds"
  | "payment_timeout"
  | "subscription_failure"
  | "abandoned_checkout"
  | "repeated_failure";

export type RecoveryAction =
  | "retry_payment"
  | "schedule_retry"
  | "send_payment_reminder"
  | "request_payment_method_update"
  | "escalate";

export type RecoveryCaseStatus =
  | "detected"
  | "planned"
  | "validated"
  | "executing"
  | "recovered"
  | "failed"
  | "escalated"
  | "exhausted";

export interface DataSummary {
  customers: number;
  subscriptions: number;
  payments: number;
  payments_by_status: Record<string, number>;
  recovery_cases: number;
}

export interface DetectionSummary {
  total_payments_analyzed: number;
  failed_payments_analyzed: number;
  recovery_opportunities: number;
  total_revenue_at_risk: number;
  high_priority_opportunities: number;
  medium_priority_opportunities: number;
  low_priority_opportunities: number;
  non_recoverable_payments: number;
}

export interface ActionSummary {
  total_opportunities: number;
  actions_planned: number;
  actions_validated: number;
  actions_executed: number;
  recovered_cases: number;
  failed_cases: number;
  escalated_cases: number;
  simulated_recovered_revenue: number;
}

export interface AISummary {
  cases_analyzed: number;
  total_ai_calls: number;
  successful_recommendations: number;
  ai_failures: number;
  agreements: number;
  disagreements: number;
  rejected_recommendations: number;
  fallback_count: number;
  average_confidence: number | null;
  recommendations_by_action: Record<string, number>;
  recommendations_by_risk_level: Record<string, number>;
  ollama_available: boolean;
}

export interface RecoveryOpportunity {
  recovery_case_id: string;
  payment_id: string;
  customer_id: string;
  status: RecoveryCaseStatus;
  priority: Priority;
  amount_at_risk: number;
  customer_value: number;
  failure_category: FailureCategory;
  detection_reason: string;
  recommended_next_step: string;
  created_at: string;
  action: RecoveryAction | null;
  action_reason: string | null;
  last_validation_result: "passed" | "rejected" | null;
  execution_status: string | null;
  recovered_amount: number;
  recovery_attempts: number;
}

export interface OpportunityListResponse {
  total: number;
  limit: number;
  offset: number;
  opportunities: RecoveryOpportunity[];
}

export interface OpportunityDetail extends RecoveryOpportunity {
  payment: {
    payment_id: string;
    amount: number;
    currency: string;
    payment_status: string;
    failure_reason: string | null;
    retry_count: number;
    subscription_id: string | null;
    created_at: string;
  };
  customer: {
    customer_id: string;
    total_successful_payments: number;
    total_failed_payments: number;
    lifetime_value: number;
  };
}

export interface PlanResult {
  already_planned: boolean;
  action: RecoveryAction;
  reason: string;
  status: RecoveryCaseStatus;
}

export interface ValidateResult {
  already_validated: boolean;
  allowed: boolean;
  rejection_reason: string | null;
  status: RecoveryCaseStatus;
}

export interface ExecuteResult {
  already_executed: boolean;
  execution_status: string;
  recovered_amount: number;
  status: RecoveryCaseStatus;
  failure_reason: string | null;
}

export interface HistoryEvent {
  action: RecoveryAction | null;
  previous_state: string;
  new_state: string;
  reason: string | null;
  validation_result: "passed" | "rejected" | null;
  execution_result: string | null;
  amount: number | null;
  created_at: string;
}

export interface HistoryResponse {
  recovery_case_id: string;
  current_status: RecoveryCaseStatus;
  history: HistoryEvent[];
}

export interface AIRecommendResult {
  recovery_case_id: string;
  deterministic_action: RecoveryAction;
  deterministic_reason: string;
  ai_status: "ok" | "unavailable" | "timeout" | "provider_error" | "invalid_json" | "invalid_schema";
  ai_error: string | null;
  ai_recommended_action: RecoveryAction | null;
  ai_confidence: number | null;
  ai_reason: string | null;
  ai_risk_level: "LOW" | "MEDIUM" | "HIGH" | null;
  ai_customer_context: string | null;
  ai_alternative_action: RecoveryAction | null;
  agreement: boolean | null;
  safety_validation_result: "passed" | "rejected" | null;
  safety_rejection_reason: string | null;
  fallback_used: boolean;
  effective_action: RecoveryAction;
  ai_model: string;
}

export interface DetectResult {
  run: {
    payments_scanned: number;
    failed_payments_scanned: number;
    opportunities_created: number;
    duplicates_skipped: number;
    ineligible_skipped: number;
  };
  summary: DetectionSummary;
}

export interface AIBatchResult {
  batch_size: number;
  cases_processed: number;
  results: AIRecommendResult[];
}

export interface OpportunityFilters {
  priority?: Priority;
  status?: string;
  failure_category?: FailureCategory;
  min_amount?: number;
  max_amount?: number;
  limit?: number;
  offset?: number;
}
