"use client";

import Link from "next/link";
import { useState } from "react";

import { PriorityBadge, StatusBadge } from "@/components/Badge";
import { ErrorState, LoadingState } from "@/components/QueryState";
import { formatCurrency, formatDateTime, formatLabel } from "@/lib/format";
import { useOpportunities } from "@/lib/hooks";
import type { FailureCategory, Priority } from "@/lib/types";

const PAGE_SIZE = 25;

const PRIORITIES: Priority[] = ["high", "medium", "low"];
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

  const { data, isLoading, error } = useOpportunities({
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
      <div>
        <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">Recovery Opportunities</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Every eligible payment Phase 3 detected, with the action Phase 4 planned (if any).
        </p>
      </div>

      <div className="flex flex-wrap gap-3 rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
        <FilterSelect label="Priority" value={priority} onChange={resetAndSet(setPriority)} options={PRIORITIES} />
        <FilterSelect label="Status" value={status} onChange={resetAndSet(setStatus)} options={STATUSES} />
        <FilterSelect
          label="Failure category"
          value={failureCategory}
          onChange={resetAndSet(setFailureCategory)}
          options={FAILURE_CATEGORIES}
        />
        <label className="flex flex-col gap-1 text-xs font-medium text-zinc-600 dark:text-zinc-400">
          Min amount
          <input
            type="number"
            value={minAmount}
            onChange={(e) => resetAndSet(setMinAmount)(e.target.value)}
            className="w-28 rounded-md border border-zinc-300 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            placeholder="0"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium text-zinc-600 dark:text-zinc-400">
          Max amount
          <input
            type="number"
            value={maxAmount}
            onChange={(e) => resetAndSet(setMaxAmount)(e.target.value)}
            className="w-28 rounded-md border border-zinc-300 px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
            placeholder="Any"
          />
        </label>
      </div>

      {isLoading ? <LoadingState /> : null}
      {error ? <ErrorState message={(error as Error).message} /> : null}

      {data ? (
        <>
          <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
            <table className="min-w-full divide-y divide-zinc-200 text-sm dark:divide-zinc-800">
              <thead className="bg-zinc-50 dark:bg-zinc-900">
                <tr>
                  {["Case ID", "Priority", "Status", "Failure category", "Amount at risk", "Action", "Detected"].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200 bg-white dark:divide-zinc-800 dark:bg-black">
                {data.opportunities.map((opp) => (
                  <tr key={opp.recovery_case_id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900">
                    <td className="px-4 py-2 font-mono text-xs">
                      <Link
                        href={`/opportunities/${opp.recovery_case_id}`}
                        className="text-blue-600 hover:underline dark:text-blue-400"
                      >
                        {opp.recovery_case_id}
                      </Link>
                    </td>
                    <td className="px-4 py-2">
                      <PriorityBadge priority={opp.priority} />
                    </td>
                    <td className="px-4 py-2">
                      <StatusBadge status={opp.status} />
                    </td>
                    <td className="px-4 py-2 text-zinc-700 dark:text-zinc-300">
                      {formatLabel(opp.failure_category)}
                    </td>
                    <td className="px-4 py-2 font-medium">{formatCurrency(opp.amount_at_risk)}</td>
                    <td className="px-4 py-2 text-zinc-700 dark:text-zinc-300">{formatLabel(opp.action)}</td>
                    <td className="px-4 py-2 text-zinc-500 dark:text-zinc-400">{formatDateTime(opp.created_at)}</td>
                  </tr>
                ))}
                {data.opportunities.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-zinc-500">
                      No opportunities match these filters.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between text-sm text-zinc-600 dark:text-zinc-400">
            <span>
              Showing {data.opportunities.length === 0 ? 0 : offset + 1}–{offset + data.opportunities.length} of{" "}
              {data.total.toLocaleString()}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
                className="rounded-md border border-zinc-300 px-3 py-1.5 disabled:cursor-not-allowed disabled:opacity-40 dark:border-zinc-700"
              >
                Previous
              </button>
              <button
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= data.total}
                className="rounded-md border border-zinc-300 px-3 py-1.5 disabled:cursor-not-allowed disabled:opacity-40 dark:border-zinc-700"
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

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
}) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-zinc-600 dark:text-zinc-400">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
      >
        <option value="">All</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {formatLabel(opt)}
          </option>
        ))}
      </select>
    </label>
  );
}
