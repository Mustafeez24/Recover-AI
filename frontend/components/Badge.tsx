import { formatLabel } from "@/lib/format";

const PRIORITY_CLASSES: Record<string, string> = {
  high: "bg-danger-bg text-danger-fg ring-1 ring-inset ring-danger-border",
  medium: "bg-warning-bg text-warning-fg ring-1 ring-inset ring-warning-border",
  low: "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-200 dark:bg-white/5 dark:text-slate-300 dark:ring-white/10",
};

const STATUS_CLASSES: Record<string, string> = {
  detected: "bg-info-bg text-info-fg ring-1 ring-inset ring-info-border",
  planned: "bg-accent-500/10 text-accent-600 ring-1 ring-inset ring-accent-500/20 dark:text-accent-400",
  validated: "bg-accent-500/10 text-accent-600 ring-1 ring-inset ring-accent-500/20 dark:text-accent-400",
  executing: "bg-warning-bg text-warning-fg ring-1 ring-inset ring-warning-border",
  recovered: "bg-success-bg text-success-fg ring-1 ring-inset ring-success-border",
  failed: "bg-danger-bg text-danger-fg ring-1 ring-inset ring-danger-border",
  escalated: "bg-warning-bg text-warning-fg ring-1 ring-inset ring-warning-border",
  exhausted: "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-200 dark:bg-white/5 dark:text-slate-300 dark:ring-white/10",
};

const RISK_CLASSES: Record<string, string> = {
  LOW: "bg-success-bg text-success-fg ring-1 ring-inset ring-success-border",
  MEDIUM: "bg-warning-bg text-warning-fg ring-1 ring-inset ring-warning-border",
  HIGH: "bg-danger-bg text-danger-fg ring-1 ring-inset ring-danger-border",
};

function Badge({ text, className }: { text: string; className: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}>
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
