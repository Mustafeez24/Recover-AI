"use client";

import { BarChartCard } from "@/components/BarChartCard";
import { ErrorState, LoadingState } from "@/components/QueryState";
import { StatCard } from "@/components/StatCard";
import { formatLabel } from "@/lib/format";
import { useAISummary } from "@/lib/hooks";

export default function AIAnalyticsPage() {
  const { data, isLoading, error } = useAISummary();

  if (isLoading) return <LoadingState label="Loading AI analytics…" />;
  if (error) return <ErrorState message={(error as Error).message} />;

  const ai = data!;

  const actionData = Object.entries(ai.recommendations_by_action).map(([label, value]) => ({
    label: formatLabel(label),
    value,
  }));
  const riskData = Object.entries(ai.recommendations_by_risk_level).map(([label, value]) => ({ label, value }));

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">AI Intelligence Analytics</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Local Ollama (Qwen 2.5 3B) recommendations vs. the deterministic Phase 4 baseline — advisory only.
          </p>
        </div>
        <div
          className={`rounded-full px-4 py-1.5 text-sm font-medium ${
            ai.ollama_available
              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
              : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
          }`}
        >
          Ollama: {ai.ollama_available ? "Available" : "Unavailable — falling back to deterministic actions"}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Cases Analyzed" value={ai.cases_analyzed.toLocaleString()} />
        <StatCard
          label="Successful AI Calls"
          value={ai.successful_recommendations.toLocaleString()}
          tone="positive"
        />
        <StatCard label="AI Failures" value={ai.ai_failures.toLocaleString()} tone={ai.ai_failures > 0 ? "warning" : "default"} />
        <StatCard
          label="Average Confidence"
          value={ai.average_confidence !== null ? `${Math.round(ai.average_confidence * 100)}%` : "—"}
        />
        <StatCard label="Agreements" value={ai.agreements.toLocaleString()} tone="positive" />
        <StatCard label="Disagreements" value={ai.disagreements.toLocaleString()} tone="warning" />
        <StatCard
          label="Rejected by Safety Validator"
          value={ai.rejected_recommendations.toLocaleString()}
          tone={ai.rejected_recommendations > 0 ? "negative" : "default"}
        />
        <StatCard label="Fallback Used" value={ai.fallback_count.toLocaleString()} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <BarChartCard title="AI Recommendations by Action" data={actionData} color="#6366f1" />
        <BarChartCard title="AI Recommendations by Risk Level" data={riskData} color="#ec4899" />
      </div>

      <p className="text-xs text-zinc-400">
        Every AI recommendation is validated against the same deterministic safety rules Phase 4 uses before it is
        ever considered. A rejected or failed AI call always falls back to the deterministic action — AI never
        executes anything on its own.
      </p>
    </div>
  );
}
