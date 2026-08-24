"use client";

import Link from "next/link";
import { use } from "react";

import { ActionButton } from "@/components/ActionButton";
import { PriorityBadge, RiskBadge, StatusBadge } from "@/components/Badge";
import { ErrorState, LoadingState } from "@/components/QueryState";
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
  if (opportunity.error) return <ErrorState message={(opportunity.error as Error).message} />;

  const c = opportunity.data!;

  return (
    <div className="space-y-8">
      <div>
        <Link href="/opportunities" className="text-sm text-blue-600 hover:underline dark:text-blue-400">
          ← Back to opportunities
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="font-mono text-xl font-semibold text-black dark:text-zinc-50">{c.recovery_case_id}</h1>
          <PriorityBadge priority={c.priority} />
          <StatusBadge status={c.status} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <InfoCard title="Payment">
          <Field label="Amount" value={formatCurrency(c.payment.amount)} />
          <Field label="Status" value={formatLabel(c.payment.payment_status)} />
          <Field label="Failure reason" value={formatLabel(c.payment.failure_reason)} />
          <Field label="Retry count" value={String(c.payment.retry_count)} />
          <Field label="Subscription" value={c.payment.subscription_id ?? "—"} />
          <Field label="Payment date" value={formatDateTime(c.payment.created_at)} />
        </InfoCard>

        <InfoCard title="Customer">
          <Field label="Customer ID" value={c.customer.customer_id} />
          <Field label="Lifetime value" value={formatCurrency(c.customer.lifetime_value)} />
          <Field label="Successful payments" value={String(c.customer.total_successful_payments)} />
          <Field label="Failed payments" value={String(c.customer.total_failed_payments)} />
        </InfoCard>

        <InfoCard title="Detection (Phase 3)">
          <Field label="Failure category" value={formatLabel(c.failure_category)} />
          <Field label="Amount at risk" value={formatCurrency(c.amount_at_risk)} />
          <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">{c.detection_reason}</p>
        </InfoCard>
      </div>

      <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
          Recovery Actions — Plan → Validate → Execute (simulated)
        </h2>
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
          Each step calls the existing per-case backend endpoint directly. There is no bulk or skip-ahead action —
          execution only ever runs after validation passes, and only ever simulates the outcome locally.
        </p>

        <div className="mt-4 flex flex-wrap gap-3">
          <ActionButton onClick={() => plan.mutate()} isPending={plan.isPending} pendingLabel="Planning…">
            1. Plan
          </ActionButton>
          <ActionButton onClick={() => validate.mutate()} isPending={validate.isPending} pendingLabel="Validating…">
            2. Validate
          </ActionButton>
          <ActionButton
            onClick={() => execute.mutate()}
            isPending={execute.isPending}
            pendingLabel="Executing…"
            variant="danger"
          >
            3. Execute (simulated)
          </ActionButton>
        </div>

        <div className="mt-4 space-y-2 text-sm">
          {plan.data ? (
            <ResultLine>
              Plan: <strong>{formatLabel(plan.data.action)}</strong> — {plan.data.reason}
              {plan.data.already_planned ? " (already planned)" : ""}
            </ResultLine>
          ) : null}
          {validate.data ? (
            <ResultLine tone={validate.data.allowed ? "positive" : "negative"}>
              Validation: <strong>{validate.data.allowed ? "Passed" : "Rejected"}</strong>
              {validate.data.rejection_reason ? ` — ${validate.data.rejection_reason}` : ""}
            </ResultLine>
          ) : null}
          {execute.data ? (
            <ResultLine tone={execute.data.execution_status === "success" ? "positive" : "default"}>
              Execution: <strong>{formatLabel(execute.data.execution_status)}</strong> — recovered{" "}
              {formatCurrency(execute.data.recovered_amount)}
              {execute.data.failure_reason ? ` — ${execute.data.failure_reason}` : ""}
            </ResultLine>
          ) : null}
          {plan.error ? <ErrorState message={(plan.error as Error).message} /> : null}
          {validate.error ? <ErrorState message={(validate.error as Error).message} /> : null}
          {execute.error ? <ErrorState message={(execute.error as Error).message} /> : null}
        </div>
      </section>

      <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
              AI Recommendation (Phase 5 — advisory only)
            </h2>
            <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
              The AI never plans, validates, or executes anything itself. Its suggestion is only ever compared
              against the deterministic action and checked by the same safety validator.
            </p>
          </div>
          <ActionButton
            onClick={() => aiRecommend.mutate()}
            isPending={aiRecommend.isPending}
            pendingLabel="Asking Ollama…"
            variant="secondary"
          >
            Get AI Recommendation
          </ActionButton>
        </div>

        {aiRecommend.data ? <AIResultPanel result={aiRecommend.data} /> : null}
        {aiRecommend.error ? <ErrorState message={(aiRecommend.error as Error).message} /> : null}
      </section>

      <section className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">Audit History</h2>
        {history.isLoading ? <LoadingState /> : null}
        {history.error ? <ErrorState message={(history.error as Error).message} /> : null}
        {history.data ? (
          <ol className="mt-4 space-y-3 border-l border-zinc-200 pl-4 dark:border-zinc-800">
            {history.data.history.length === 0 ? (
              <p className="text-sm text-zinc-500">No recovery actions have been taken on this case yet.</p>
            ) : (
              history.data.history.map((event, i) => (
                <li key={i} className="relative">
                  <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-zinc-400" />
                  <p className="text-sm">
                    <span className="font-medium">{formatLabel(event.previous_state)}</span>
                    {" → "}
                    <span className="font-medium">{formatLabel(event.new_state)}</span>
                    {event.action ? <span className="text-zinc-500"> ({formatLabel(event.action)})</span> : null}
                  </p>
                  {event.reason ? <p className="text-xs text-zinc-500 dark:text-zinc-400">{event.reason}</p> : null}
                  {event.amount ? (
                    <p className="text-xs text-emerald-600 dark:text-emerald-400">
                      Amount: {formatCurrency(event.amount)}
                    </p>
                  ) : null}
                  <p className="text-xs text-zinc-400">{formatDateTime(event.created_at)}</p>
                </li>
              ))
            )}
          </ol>
        ) : null}
      </section>
    </div>
  );
}

function InfoCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">{title}</h2>
      <div className="mt-3 space-y-1.5">{children}</div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-zinc-500 dark:text-zinc-400">{label}</span>
      <span className="font-medium text-black dark:text-zinc-50">{value}</span>
    </div>
  );
}

function ResultLine({
  children,
  tone = "default",
}: {
  children: React.ReactNode;
  tone?: "default" | "positive" | "negative";
}) {
  const toneClasses = {
    default: "text-zinc-700 dark:text-zinc-300",
    positive: "text-emerald-700 dark:text-emerald-400",
    negative: "text-red-700 dark:text-red-400",
  };
  return <p className={toneClasses[tone]}>{children}</p>;
}

function AIResultPanel({ result }: { result: NonNullable<ReturnType<typeof useAIRecommendation>["data"]> }) {
  if (result.ai_status !== "ok") {
    return (
      <div className="mt-4 rounded-md bg-amber-50 p-4 text-sm dark:bg-amber-950">
        <p className="font-medium text-amber-900 dark:text-amber-200">
          AI call did not succeed (status: {result.ai_status}) — fell back to the deterministic action.
        </p>
        {result.ai_error ? <p className="mt-1 text-xs text-amber-800 dark:text-amber-300">{result.ai_error}</p> : null}
        <p className="mt-2 text-amber-900 dark:text-amber-200">
          Effective action: <strong>{formatLabel(result.effective_action)}</strong> (deterministic)
        </p>
      </div>
    );
  }

  return (
    <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
      <div className="rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
        <p className="text-xs font-medium uppercase text-zinc-500">Deterministic (Phase 4)</p>
        <p className="mt-1 font-medium">{formatLabel(result.deterministic_action)}</p>
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">{result.deterministic_reason}</p>
      </div>
      <div className="rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
        <p className="text-xs font-medium uppercase text-zinc-500">AI Suggestion (Phase 5)</p>
        <div className="mt-1 flex items-center gap-2">
          <p className="font-medium">{formatLabel(result.ai_recommended_action)}</p>
          {result.ai_risk_level ? <RiskBadge risk={result.ai_risk_level} /> : null}
        </div>
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">{result.ai_reason}</p>
        {result.ai_confidence !== null ? (
          <p className="mt-1 text-xs text-zinc-500">Confidence: {formatPercent(result.ai_confidence)}</p>
        ) : null}
        {result.ai_customer_context ? (
          <p className="mt-1 text-xs italic text-zinc-500">{result.ai_customer_context}</p>
        ) : null}
      </div>

      <div className="md:col-span-2 flex flex-wrap gap-4 rounded-md bg-zinc-50 p-4 text-sm dark:bg-zinc-900">
        <span>
          Agreement:{" "}
          <strong className={result.agreement ? "text-emerald-600" : "text-amber-600"}>
            {result.agreement ? "Agree" : "Disagree"}
          </strong>
        </span>
        <span>
          Safety validation:{" "}
          <strong className={result.safety_validation_result === "passed" ? "text-emerald-600" : "text-red-600"}>
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
          <span className="w-full text-xs text-red-600">{result.safety_rejection_reason}</span>
        ) : null}
      </div>
    </div>
  );
}
