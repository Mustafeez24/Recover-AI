"use client";

import { ActionButton } from "@/components/ActionButton";
import { BarChartCard } from "@/components/BarChartCard";
import {
  CheckCircleIcon,
  CoinsIcon,
  CpuIcon,
  GaugeIcon,
  MagnifierScanIcon,
  PlayIcon,
  ShieldIcon,
  TargetIcon,
  TrendUpIcon,
  UsersIcon,
} from "@/components/icons";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState } from "@/components/QueryState";
import { KpiGridSkeleton } from "@/components/LoadingSkeleton";
import { RecoveryPipeline, type PipelineStage } from "@/components/RecoveryPipeline";
import { SectionCard } from "@/components/SectionCard";
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

  const retry = () => {
    dataSummary.refetch();
    detectionSummary.refetch();
    actionSummary.refetch();
    aiSummary.refetch();
  };

  const headerActions = (
    <>
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
        variant="primary"
      >
        Run AI Batch
      </ActionButton>
    </>
  );

  if (loading) {
    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow="RecoverAI"
          title="Revenue Recovery Intelligence"
          subtitle="Detect payment leakage, prioritize recovery opportunities, and turn failed payments into recovered revenue."
          actions={headerActions}
        />
        <KpiGridSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow="RecoverAI"
          title="Revenue Recovery Intelligence"
          subtitle="Detect payment leakage, prioritize recovery opportunities, and turn failed payments into recovered revenue."
          actions={headerActions}
        />
        <ErrorState message={`Could not reach the RecoverAI API: ${(error as Error).message}`} onRetry={retry} />
      </div>
    );
  }

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

  const pipelineStages: PipelineStage[] = [
    {
      label: "Detect",
      description: "Scans payments for recoverable failures.",
      value: detection.total_payments_analyzed.toLocaleString(),
      icon: MagnifierScanIcon,
    },
    {
      label: "Analyze",
      description: "Prioritizes leakage by risk and customer value.",
      value: detection.recovery_opportunities.toLocaleString(),
      icon: TargetIcon,
    },
    {
      label: "Recommend",
      description: "Advisory AI suggests a recovery action.",
      value: ai.cases_analyzed.toLocaleString(),
      icon: CpuIcon,
    },
    {
      label: "Validate",
      description: "Deterministic safety rules approve or reject.",
      value: actions.actions_validated.toLocaleString(),
      icon: ShieldIcon,
    },
    {
      label: "Execute",
      description: "Simulated execution — no payment provider called.",
      value: actions.actions_executed.toLocaleString(),
      icon: PlayIcon,
    },
    {
      label: "Measure",
      description: "Tracks simulated recovered revenue.",
      value: formatCurrency(actions.simulated_recovered_revenue),
      icon: CoinsIcon,
    },
  ];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="RecoverAI"
        title="Revenue Recovery Intelligence"
        subtitle="Detect payment leakage, prioritize recovery opportunities, and turn failed payments into recovered revenue."
        actions={headerActions}
      />

      {runDetection.data || runAIBatch.data ? (
        <div className="flex flex-col gap-2">
          {runDetection.data ? (
            <p className="flex items-center gap-2 rounded-lg border border-success-border bg-success-bg px-3 py-2 text-sm text-success-fg">
              <CheckCircleIcon className="h-4 w-4 shrink-0" />
              Detection run: {runDetection.data.run.opportunities_created} new opportunit
              {runDetection.data.run.opportunities_created === 1 ? "y" : "ies"} created,{" "}
              {runDetection.data.run.duplicates_skipped} already existed.
            </p>
          ) : null}
          {runAIBatch.data ? (
            <p className="flex items-center gap-2 rounded-lg border border-success-border bg-success-bg px-3 py-2 text-sm text-success-fg">
              <CheckCircleIcon className="h-4 w-4 shrink-0" />
              AI batch: {runAIBatch.data.cases_processed} case{runAIBatch.data.cases_processed === 1 ? "" : "s"}{" "}
              analyzed.
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Payments Analyzed"
          value={detection.total_payments_analyzed.toLocaleString()}
          icon={MagnifierScanIcon}
        />
        <StatCard
          label="Recovery Opportunities"
          value={detection.recovery_opportunities.toLocaleString()}
          sublabel={`${detection.non_recoverable_payments} non-recoverable`}
          icon={TargetIcon}
          tone="info"
        />
        <StatCard
          label="Revenue at Risk"
          value={formatCurrency(detection.total_revenue_at_risk)}
          tone="warning"
          icon={GaugeIcon}
        />
        <StatCard
          label="Simulated Recovered Revenue"
          value={formatCurrency(actions.simulated_recovered_revenue)}
          tone="positive"
          sublabel="Advisory only — no real payment executed"
          icon={CoinsIcon}
        />
        <StatCard label="Actions Executed" value={actions.actions_executed.toLocaleString()} icon={PlayIcon} />
        <StatCard
          label="Customers / Payments"
          value={`${data.customers.toLocaleString()} / ${data.payments.toLocaleString()}`}
          icon={UsersIcon}
        />
        <StatCard
          label="AI Recommendations"
          value={ai.cases_analyzed.toLocaleString()}
          sublabel={
            ai.average_confidence !== null ? `avg confidence ${Math.round(ai.average_confidence * 100)}%` : undefined
          }
          icon={CpuIcon}
        />
        <StatCard
          label="Ollama Status"
          value={ai.ollama_available ? "Available" : "Unavailable"}
          tone={ai.ollama_available ? "positive" : "warning"}
          sublabel={ai.ollama_available ? undefined : "Falling back to deterministic actions"}
          icon={TrendUpIcon}
        />
      </div>

      <SectionCard
        title="Recovery Pipeline"
        description="Detect → Analyze → Recommend → Validate → Execute → Measure — AI is advisory only; deterministic safety rules remain authoritative at every step."
      >
        <RecoveryPipeline stages={pipelineStages} />
      </SectionCard>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <BarChartCard title="Opportunities by Priority" data={priorityData} color="var(--color-warning-fg)" />
        <BarChartCard title="Recovery Outcomes" data={outcomeData} color="var(--color-success-fg)" />
      </div>
    </div>
  );
}
