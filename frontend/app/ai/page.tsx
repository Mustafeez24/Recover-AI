"use client";

import { AIStatusCard } from "@/components/AIStatusCard";
import { BarChartCard } from "@/components/BarChartCard";
import {
  AlertIcon,
  CheckCircleIcon,
  CpuIcon,
  GaugeIcon,
  ShieldIcon,
  TrendUpIcon,
  XCircleIcon,
} from "@/components/icons";
import { KpiGridSkeleton } from "@/components/LoadingSkeleton";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState } from "@/components/QueryState";
import { StatCard } from "@/components/StatCard";
import { formatLabel } from "@/lib/format";
import { useAISummary } from "@/lib/hooks";

export default function AIAnalyticsPage() {
  const { data, isLoading, error, refetch } = useAISummary();

  if (isLoading) {
    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow="RecoverAI"
          title="AI Recovery Intelligence"
          subtitle="Advisory AI recommendations compared against deterministic recovery rules."
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
          title="AI Recovery Intelligence"
          subtitle="Advisory AI recommendations compared against deterministic recovery rules."
        />
        <ErrorState message={(error as Error).message} onRetry={() => refetch()} />
      </div>
    );
  }

  const ai = data!;

  const actionData = Object.entries(ai.recommendations_by_action).map(([label, value]) => ({
    label: formatLabel(label),
    value,
  }));
  const riskData = Object.entries(ai.recommendations_by_risk_level).map(([label, value]) => ({ label, value }));

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="RecoverAI"
        title="AI Recovery Intelligence"
        subtitle="Advisory AI recommendations compared against deterministic recovery rules."
      />

      <AIStatusCard available={ai.ollama_available} />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Cases Analyzed" value={ai.cases_analyzed.toLocaleString()} icon={CpuIcon} />
        <StatCard
          label="Successful AI Calls"
          value={ai.successful_recommendations.toLocaleString()}
          tone="positive"
          icon={CheckCircleIcon}
        />
        <StatCard
          label="AI Failures"
          value={ai.ai_failures.toLocaleString()}
          tone={ai.ai_failures > 0 ? "warning" : "default"}
          icon={XCircleIcon}
        />
        <StatCard
          label="Average Confidence"
          value={ai.average_confidence !== null ? `${Math.round(ai.average_confidence * 100)}%` : "—"}
          icon={GaugeIcon}
        />
        <StatCard label="Agreements" value={ai.agreements.toLocaleString()} tone="positive" icon={CheckCircleIcon} />
        <StatCard
          label="Disagreements"
          value={ai.disagreements.toLocaleString()}
          tone="warning"
          icon={TrendUpIcon}
        />
        <StatCard
          label="Rejected by Safety Validator"
          value={ai.rejected_recommendations.toLocaleString()}
          tone={ai.rejected_recommendations > 0 ? "negative" : "default"}
          icon={ShieldIcon}
        />
        <StatCard label="Fallback Used" value={ai.fallback_count.toLocaleString()} icon={AlertIcon} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <BarChartCard
          title="AI Recommendations by Action"
          description="What the AI advised, before safety validation."
          data={actionData}
          color="var(--color-accent-500)"
        />
        <BarChartCard
          title="AI Recommendations by Risk Level"
          description="AI-assessed risk level per recommendation."
          data={riskData}
          color="var(--color-accent-600)"
        />
      </div>

      <p className="max-w-3xl text-xs text-text-muted">
        Every AI recommendation is validated against the same deterministic safety rules the recovery engine uses
        before it is ever considered. A rejected or failed AI call always falls back to the deterministic action —
        AI never executes anything on its own.
      </p>
    </div>
  );
}
