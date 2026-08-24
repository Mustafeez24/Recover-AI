"use client";

import { ActionButton } from "@/components/ActionButton";
import { BarChartCard } from "@/components/BarChartCard";
import { ErrorState, LoadingState } from "@/components/QueryState";
import { StatCard } from "@/components/StatCard";
import { formatCurrency } from "@/lib/format";
import {
  useActionSummary,
  useAISummary,
  useDataSummary,
  useDetectionSummary,
  useRunAIBatch,
  useRunDetection,
} from "@/lib/hooks";

export default function DashboardPage() {
  const dataSummary = useDataSummary();
  const detectionSummary = useDetectionSummary();
  const actionSummary = useActionSummary();
  const aiSummary = useAISummary();

  const runDetection = useRunDetection();
  const runAIBatch = useRunAIBatch();

  const loading =
    dataSummary.isLoading || detectionSummary.isLoading || actionSummary.isLoading || aiSummary.isLoading;
  const error = dataSummary.error || detectionSummary.error || actionSummary.error || aiSummary.error;

  if (loading) return <LoadingState label="Loading dashboard…" />;
  if (error) return <ErrorState message={`Could not reach the RecoverAI API: ${(error as Error).message}`} />;

  const detection = detectionSummary.data!;
  const actions = actionSummary.data!;
  const ai = aiSummary.data!;
  const data = dataSummary.data!;

  const priorityData = [
    { label: "High", value: detection.high_priority_opportunities },
    { label: "Medium", value: detection.medium_priority_opportunities },
    { label: "Low", value: detection.low_priority_opportunities },
  ];

  const outcomeData = [
    { label: "Recovered", value: actions.recovered_cases },
    { label: "Failed", value: actions.failed_cases },
    { label: "Escalated", value: actions.escalated_cases },
  ];

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">Executive Recovery Dashboard</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Deterministic leakage detection + recovery engine, with advisory AI recommendations.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <ActionButton
            onClick={() => runDetection.mutate()}
            isPending={runDetection.isPending}
            pendingLabel="Running detection…"
            variant="secondary"
          >
            Run Detection
          </ActionButton>
          <ActionButton
            onClick={() => runAIBatch.mutate(10)}
            isPending={runAIBatch.isPending}
            pendingLabel="Analyzing…"
            variant="secondary"
          >
            Run AI Batch (10)
          </ActionButton>
        </div>
      </div>

      {runDetection.data ? (
        <p className="text-sm text-emerald-700 dark:text-emerald-400">
          Detection run: {runDetection.data.run.opportunities_created} new opportunit
          {runDetection.data.run.opportunities_created === 1 ? "y" : "ies"} created,{" "}
          {runDetection.data.run.duplicates_skipped} already existed.
        </p>
      ) : null}
      {runAIBatch.data ? (
        <p className="text-sm text-emerald-700 dark:text-emerald-400">
          AI batch: {runAIBatch.data.cases_processed} case{runAIBatch.data.cases_processed === 1 ? "" : "s"}{" "}
          analyzed.
        </p>
      ) : null}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Payments Analyzed" value={detection.total_payments_analyzed.toLocaleString()} />
        <StatCard
          label="Recovery Opportunities"
          value={detection.recovery_opportunities.toLocaleString()}
          sublabel={`${detection.non_recoverable_payments} non-recoverable`}
        />
        <StatCard
          label="Revenue at Risk"
          value={formatCurrency(detection.total_revenue_at_risk)}
          tone="warning"
        />
        <StatCard
          label="Simulated Recovered Revenue"
          value={formatCurrency(actions.simulated_recovered_revenue)}
          tone="positive"
          sublabel="Advisory only — no real payment executed"
        />
        <StatCard label="Actions Executed" value={actions.actions_executed.toLocaleString()} />
        <StatCard
          label="Customers / Payments"
          value={`${data.customers.toLocaleString()} / ${data.payments.toLocaleString()}`}
        />
        <StatCard
          label="AI Recommendations"
          value={ai.cases_analyzed.toLocaleString()}
          sublabel={ai.average_confidence !== null ? `avg confidence ${Math.round(ai.average_confidence * 100)}%` : undefined}
        />
        <StatCard
          label="Ollama Status"
          value={ai.ollama_available ? "Available" : "Unavailable"}
          tone={ai.ollama_available ? "positive" : "warning"}
          sublabel={ai.ollama_available ? undefined : "Falling back to deterministic actions"}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <BarChartCard title="Opportunities by Priority" data={priorityData} color="#f59e0b" />
        <BarChartCard title="Recovery Outcomes" data={outcomeData} color="#10b981" />
      </div>
    </div>
  );
}
