"use client";

import Link from "next/link";
import { use } from "react";

import { ActionButton } from "@/components/ActionButton";
import { AuditTimeline } from "@/components/AuditTimeline";
import { PriorityBadge, RiskBadge, StatusBadge } from "@/components/Badge";
import { ArrowRightIcon, CpuIcon, ShieldIcon } from "@/components/icons";
import { CardSkeleton } from "@/components/LoadingSkeleton";
import { ErrorState, LoadingState } from "@/components/QueryState";
import { RecoveryStepper, type StepState, type StepperStep } from "@/components/RecoveryStepper";
import { SectionCard } from "@/components/SectionCard";
import { formatCurrency, formatDateTime, formatLabel, formatPercent } from "@/lib/format";
import {
  useAIRecommendation,
  useExecuteAction,
  useHistory,
  useOpportunity,
  usePlanAction,
  useValidateAction,
} from "@/lib/hooks";

export default function OpportunityDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  const opportunity = useOpportunity(id);
  const history = useHistory(id);

  const plan = usePlanAction(id);
  const validate = useValidateAction(id);
  const execute = useExecuteAction(id);
  const aiRecommend = useAIRecommendation(id);

  if (opportunity.isLoading) return <LoadingState label="Loading case…" />;
  if (opportunity.error)
    return <ErrorState message={(opportunity.error as Error).message} onRetry={() => opportunity.refetch()} />;

  const c = opportunity.data!;

  // Gating for each action button mirrors the backend's own preconditions
  // exactly (see backend/app/recovery/workflow.py): plan() and validate()
  // are always safe to call and never error, but execute() only succeeds
  // when the case is currently VALIDATED -- everything else is a 400. Using
  // the authoritative `status` (refetched after every mutation) rather than
  // inferring from possibly-stale per-attempt fields like `execution_status`
  // keeps the UI from ever offering an action the backend would reject.
  const status = c.status;
  const canPlan = status === "detected" || status === "failed";
  const canValidate = status === "planned";
  const canExecute = status === "validated";

  let planState: StepState = "pending";
  if (status === "exhausted") planState = "failed";
  else if (!canPlan) planState = "completed";
  const planStep: StepperStep = {
    label: "1. Plan",
    description: "Selects a deterministic recovery action for this case.",
    state: planState,
    detail: plan.data ? (
      <p className="text-foreground/80">
        <strong>{formatLabel(plan.data.action)}</strong> — {plan.data.reason}
        {plan.data.already_planned ? " (already planned)" : ""}
      </p>
    ) : c.action ? (
      <p className="text-foreground/80">
        <strong>{formatLabel(c.action)}</strong>
        {c.action_reason ? ` — ${c.action_reason}` : ""}
      </p>
    ) : undefined,
    action: canPlan ? (
      <ActionButton onClick={() => plan.mutate()} isPending={plan.isPending} pendingLabel="Planning…">
        Plan Action
      </ActionButton>
    ) : undefined,
  };
  if (plan.error) planStep.detail = <ErrorState message={(plan.error as Error).message} />;

  let validateState: StepState = "pending";
  if (["validated", "executing", "recovered"].includes(status)) validateState = "completed";
  else if (status === "failed" && c.last_validation_result === "rejected") validateState = "action_required";
  else if (status === "escalated") validateState = "action_required";
  const validateStep: StepperStep = {
    label: "2. Validate",
    description: "Deterministic safety rules approve or reject the planned action.",
    state: validateState,
    detail:
      validate.data || c.last_validation_result ? (
        <p className={validate.data?.allowed || c.last_validation_result === "passed" ? "text-success-fg" : "text-warning-fg"}>
          <strong>{(validate.data?.allowed ?? c.last_validation_result === "passed") ? "Passed" : "Rejected"}</strong>
          {validate.data?.rejection_reason ? ` — ${validate.data.rejection_reason}` : ""}
        </p>
      ) : undefined,
    action: canValidate ? (
      <ActionButton onClick={() => validate.mutate()} isPending={validate.isPending} pendingLabel="Validating…">
        Validate Action
      </ActionButton>
    ) : undefined,
  };
  if (validate.error) validateStep.detail = <ErrorState message={(validate.error as Error).message} />;

  let executeState: StepState = "pending";
  if (status === "recovered") executeState = "completed";
  else if (status === "failed" && c.execution_status) executeState = "failed";
  else if (status === "escalated" || status === "exhausted") executeState = "failed";
  const executeStep: StepperStep = {
    label: "3. Execute (Simulated)",
    description: "Simulated execution only — no real payment provider is ever called.",
    state: executeState,
    detail: execute.data ? (
      <p className={execute.data.execution_status === "success" ? "text-success-fg" : "text-foreground/80"}>
        <strong>{formatLabel(execute.data.execution_status)}</strong> — simulated recovery of{" "}
        {formatCurrency(execute.data.recovered_amount)}
        {execute.data.failure_reason ? ` — ${execute.data.failure_reason}` : ""}
      </p>
    ) : c.execution_status ? (
      <p className="text-foreground/80">
        <strong>{formatLabel(c.execution_status)}</strong> — simulated recovery of {formatCurrency(c.recovered_amount)}
      </p>
    ) : undefined,
    action: canExecute ? (
      <ActionButton
        onClick={() => execute.mutate()}
        isPending={execute.isPending}
        pendingLabel="Executing (simulated)…"
        variant="danger"
      >
        Execute (Simulated)
      </ActionButton>
    ) : undefined,
  };
  if (execute.error) executeStep.detail = <ErrorState message={(execute.error as Error).message} />;

  return (
    <div className="space-y-8">
      <div>
        <Link
          href="/opportunities"
          className="inline-flex items-center gap-1 text-sm text-accent-600 hover:underline dark:text-accent-400"
        >
          ← Back to opportunities
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="font-mono text-xl font-semibold tracking-tight text-foreground">{c.recovery_case_id}</h1>
          <PriorityBadge priority={c.priority} />
          <StatusBadge status={c.status} />
        </div>
        <p className="mt-1 text-xs text-text-muted">
          All actions below are advisory and simulated — no payment provider is called and no real money moves.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* LEFT: Payment / Customer / Detection */}
        <div className="space-y-4 lg:col-span-1">
          <SectionCard title="Payment">
            <Field label="Amount" value={formatCurrency(c.payment.amount)} />
            <Field label="Status" value={formatLabel(c.payment.payment_status)} />
            <Field label="Failure reason" value={formatLabel(c.payment.failure_reason)} />
            <Field label="Retry count" value={String(c.payment.retry_count)} />
            <Field label="Subscription" value={c.payment.subscription_id ?? "—"} />
            <Field label="Payment date" value={formatDateTime(c.payment.created_at)} />
          </SectionCard>

          <SectionCard title="Customer">
            <Field label="Customer ID" value={c.customer.customer_id} />
            <Field label="Lifetime value" value={formatCurrency(c.customer.lifetime_value)} />
            <Field label="Successful payments" value={String(c.customer.total_successful_payments)} />
            <Field label="Failed payments" value={String(c.customer.total_failed_payments)} />
          </SectionCard>

          <SectionCard title="Detection">
            <Field label="Failure category" value={formatLabel(c.failure_category)} />
            <Field label="Amount at risk" value={formatCurrency(c.amount_at_risk)} />
            <p className="mt-2 text-xs text-text-muted">{c.detection_reason}</p>
          </SectionCard>
        </div>

        {/* RIGHT: Recovery workflow + AI recommendation */}
        <div className="space-y-4 lg:col-span-2">
          <SectionCard
            title="Recovery Workflow"
            description="Each step calls the existing per-case backend endpoint directly — there is no bulk or skip-ahead action, and execution only ever runs after validation passes."
          >
            <RecoveryStepper steps={[planStep, validateStep, executeStep]} />
          </SectionCard>

          <SectionCard
            title="AI Recommendation"
            description="Advisory only — the AI never plans, validates, or executes anything itself. Its suggestion is only ever compared against the deterministic action and checked by the same safety validator."
            action={
              <ActionButton
                onClick={() => aiRecommend.mutate()}
                isPending={aiRecommend.isPending}
                pendingLabel="Asking Ollama…"
                variant="secondary"
              >
                Get AI Recommendation
              </ActionButton>
            }
          >
            {aiRecommend.data ? (
              <AIComparisonPanel result={aiRecommend.data} />
            ) : (
              <p className="text-sm text-text-muted">No AI recommendation requested for this case yet.</p>
            )}
            {aiRecommend.error ? <ErrorState message={(aiRecommend.error as Error).message} /> : null}
          </SectionCard>
        </div>
      </div>

      <SectionCard title="Audit History" description="A full, append-only record of every state transition on this case.">
        {history.isLoading ? <CardSkeleton lines={3} /> : null}
        {history.error ? <ErrorState message={(history.error as Error).message} onRetry={() => history.refetch()} /> : null}
        {history.data ? <AuditTimeline events={history.data.history} /> : null}
      </SectionCard>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 py-1 text-sm">
      <span className="text-text-muted">{label}</span>
      <span className="text-right font-medium text-foreground">{value}</span>
    </div>
  );
}

function AIComparisonPanel({ result }: { result: NonNullable<ReturnType<typeof useAIRecommendation>["data"]> }) {
  if (result.ai_status !== "ok") {
    return (
      <div className="rounded-xl border border-info-border bg-info-bg p-4 text-sm">
        <p className="flex items-center gap-2 font-medium text-info-fg">
          <CpuIcon className="h-4 w-4 shrink-0" />
          AI call did not succeed (status: {result.ai_status}) — fell back to the deterministic action.
        </p>
        {result.ai_error ? <p className="mt-1 text-xs text-info-fg/80">{result.ai_error}</p> : null}
        <p className="mt-2 text-info-fg">
          Effective action: <strong>{formatLabel(result.effective_action)}</strong> (deterministic)
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 items-center gap-3 md:grid-cols-[1fr_auto_1fr]">
        <div className="rounded-xl border border-border-subtle p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">Deterministic</p>
          <p className="mt-1 text-sm font-semibold text-foreground">{formatLabel(result.deterministic_action)}</p>
          <p className="mt-1 text-xs text-text-muted">{result.deterministic_reason}</p>
        </div>
        <ArrowRightIcon className="mx-auto hidden h-5 w-5 rotate-90 text-text-muted md:block md:rotate-0" />
        <div className="rounded-xl border border-accent-500/30 bg-accent-500/5 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-accent-600 dark:text-accent-400">
            AI Suggestion
          </p>
          <div className="mt-1 flex items-center gap-2">
            <p className="text-sm font-semibold text-foreground">{formatLabel(result.ai_recommended_action)}</p>
            {result.ai_risk_level ? <RiskBadge risk={result.ai_risk_level} /> : null}
          </div>
          <p className="mt-1 text-xs text-text-muted">{result.ai_reason}</p>
          {result.ai_confidence !== null ? (
            <p className="mt-1 text-xs text-text-muted">Confidence: {formatPercent(result.ai_confidence)}</p>
          ) : null}
          {result.ai_customer_context ? (
            <p className="mt-1 text-xs italic text-text-muted">{result.ai_customer_context}</p>
          ) : null}
        </div>
      </div>

      <div className="flex flex-wrap gap-x-6 gap-y-2 rounded-xl bg-slate-50 p-4 text-sm dark:bg-white/5">
        <span>
          Agreement:{" "}
          <strong className={result.agreement ? "text-success-fg" : "text-warning-fg"}>
            {result.agreement ? "Agree" : "Disagree"}
          </strong>
        </span>
        <span className="inline-flex items-center gap-1">
          <ShieldIcon className="h-3.5 w-3.5" />
          Safety validation:{" "}
          <strong className={result.safety_validation_result === "passed" ? "text-success-fg" : "text-danger-fg"}>
            {formatLabel(result.safety_validation_result)}
          </strong>
        </span>
        <span>
          Fallback used: <strong>{result.fallback_used ? "Yes" : "No"}</strong>
        </span>
        <span>
          Effective action: <strong>{formatLabel(result.effective_action)}</strong>
        </span>
        {result.safety_rejection_reason ? (
          <span className="w-full text-xs text-danger-fg">{result.safety_rejection_reason}</span>
        ) : null}
      </div>
    </div>
  );
}
