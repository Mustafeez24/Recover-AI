"use client";

import { useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { FilterBar } from "@/components/FilterBar";
import { ListIcon } from "@/components/icons";
import { OpportunityTable } from "@/components/OpportunityTable";
import { PageHeader } from "@/components/PageHeader";
import { ErrorState } from "@/components/QueryState";
import { TableRowSkeleton } from "@/components/LoadingSkeleton";
import { useOpportunities } from "@/lib/hooks";
import type { FailureCategory, Priority } from "@/lib/types";

const PAGE_SIZE = 25;

const STATUSES = ["detected", "planned", "validated", "executing", "recovered", "failed", "escalated", "exhausted"];
const FAILURE_CATEGORIES: FailureCategory[] = [
  "temporary_failure",
  "insufficient_funds",
  "payment_timeout",
  "subscription_failure",
  "abandoned_checkout",
  "repeated_failure",
];

export default function OpportunitiesPage() {
  const [priority, setPriority] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [failureCategory, setFailureCategory] = useState<string>("");
  const [minAmount, setMinAmount] = useState<string>("");
  const [maxAmount, setMaxAmount] = useState<string>("");
  const [offset, setOffset] = useState(0);

  const { data, isLoading, error, refetch } = useOpportunities({
    priority: (priority || undefined) as Priority | undefined,
    status: status || undefined,
    failure_category: (failureCategory || undefined) as FailureCategory | undefined,
    min_amount: minAmount ? Number(minAmount) : undefined,
    max_amount: maxAmount ? Number(maxAmount) : undefined,
    limit: PAGE_SIZE,
    offset,
  });

  function resetAndSet(setter: (value: string) => void) {
    return (value: string) => {
      setter(value);
      setOffset(0);
    };
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Recovery Opportunities"
        subtitle="Prioritized payment failures with recommended recovery actions."
      />

      <FilterBar
        priority={priority}
        onPriorityChange={resetAndSet(setPriority)}
        status={status}
        onStatusChange={resetAndSet(setStatus)}
        statuses={STATUSES}
        failureCategory={failureCategory}
        onFailureCategoryChange={resetAndSet(setFailureCategory)}
        failureCategories={FAILURE_CATEGORIES}
        minAmount={minAmount}
        onMinAmountChange={resetAndSet(setMinAmount)}
        maxAmount={maxAmount}
        onMaxAmountChange={resetAndSet(setMaxAmount)}
      />

      {error ? <ErrorState message={(error as Error).message} onRetry={() => refetch()} /> : null}

      {isLoading ? (
        <div className="overflow-x-auto rounded-2xl border border-border-subtle bg-surface">
          <table className="min-w-full divide-y divide-border-subtle text-sm">
            <tbody className="divide-y divide-border-subtle">
              {Array.from({ length: 8 }).map((_, i) => (
                <TableRowSkeleton key={i} />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {data ? (
        <>
          {data.opportunities.length === 0 ? (
            <EmptyState
              title="No recovery opportunities found."
              description="Try widening your filters, or run detection from the dashboard to scan for new leakage."
              icon={ListIcon}
            />
          ) : (
            <div className="animate-fade-in">
              <OpportunityTable opportunities={data.opportunities} />
            </div>
          )}

          <div className="flex items-center justify-between text-sm text-text-muted">
            <span>
              Showing {data.opportunities.length === 0 ? 0 : offset + 1}–{offset + data.opportunities.length} of{" "}
              {data.total.toLocaleString()}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
                className="rounded-lg border border-border-subtle bg-surface px-3 py-1.5 font-medium transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 dark:hover:bg-white/5"
              >
                Previous
              </button>
              <button
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= data.total}
                className="rounded-lg border border-border-subtle bg-surface px-3 py-1.5 font-medium transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 dark:hover:bg-white/5"
              >
                Next
              </button>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
