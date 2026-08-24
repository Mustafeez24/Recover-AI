import { formatLabel } from "@/lib/format";

const PRIORITY_CLASSES: Record<string, string> = {
  high: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  medium: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  low: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
};

const STATUS_CLASSES: Record<string, string> = {
  detected: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
  planned: "bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-300",
  validated: "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300",
  executing: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  recovered: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  failed: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  escalated: "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300",
  exhausted: "bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
};

const RISK_CLASSES: Record<string, string> = {
  LOW: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  MEDIUM: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  HIGH: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
};

function Badge({ text, className }: { text: string; className: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}>
      {text}
    </span>
  );
}

export function PriorityBadge({ priority }: { priority: string }) {
  return <Badge text={formatLabel(priority)} className={PRIORITY_CLASSES[priority] ?? PRIORITY_CLASSES.low} />;
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge text={formatLabel(status)} className={STATUS_CLASSES[status] ?? STATUS_CLASSES.exhausted} />;
}

export function RiskBadge({ risk }: { risk: string }) {
  return <Badge text={risk} className={RISK_CLASSES[risk] ?? RISK_CLASSES.MEDIUM} />;
}
