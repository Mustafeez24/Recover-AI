import Link from "next/link";

import { formatCurrency, formatDateTime, formatLabel } from "@/lib/format";
import type { RecoveryOpportunity } from "@/lib/types";

import { PriorityBadge, StatusBadge } from "./Badge";

const COLUMNS = ["Case ID", "Priority", "Status", "Failure Category", "Amount at Risk", "Recommended Action", "Detected"];

export function OpportunityTable({ opportunities }: { opportunities: RecoveryOpportunity[] }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-border-subtle bg-surface shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <table className="min-w-full divide-y divide-border-subtle text-sm">
        <thead className="sticky top-0 z-10 bg-slate-50/90 backdrop-blur-sm dark:bg-white/[0.03]">
          <tr>
            {COLUMNS.map((h) => (
              <th
                key={h}
                className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border-subtle">
          {opportunities.map((opp) => (
            <tr key={opp.recovery_case_id} className="transition-colors hover:bg-slate-50 dark:hover:bg-white/[0.03]">
              <td className="whitespace-nowrap px-4 py-3 font-mono text-xs">
                <Link
                  href={`/opportunities/${opp.recovery_case_id}`}
                  className="font-medium text-accent-600 hover:underline dark:text-accent-400"
                >
                  {opp.recovery_case_id}
                </Link>
              </td>
              <td className="whitespace-nowrap px-4 py-3">
                <PriorityBadge priority={opp.priority} />
              </td>
              <td className="whitespace-nowrap px-4 py-3">
                <StatusBadge status={opp.status} />
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-foreground/80">{formatLabel(opp.failure_category)}</td>
              <td className="whitespace-nowrap px-4 py-3 font-semibold text-foreground">
                {formatCurrency(opp.amount_at_risk)}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-foreground/80">{formatLabel(opp.action)}</td>
              <td className="whitespace-nowrap px-4 py-3 text-text-muted">{formatDateTime(opp.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
