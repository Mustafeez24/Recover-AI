import type { IconProps } from "./icons";

type Tone = "default" | "positive" | "warning" | "negative" | "info";

const TONE_VALUE: Record<Tone, string> = {
  default: "text-foreground",
  positive: "text-success-fg",
  warning: "text-warning-fg",
  negative: "text-danger-fg",
  info: "text-info-fg",
};

const TONE_ICON_WRAP: Record<Tone, string> = {
  default: "bg-brand-900/5 text-brand-900 dark:bg-white/5 dark:text-slate-200",
  positive: "bg-success-bg text-success-fg",
  warning: "bg-warning-bg text-warning-fg",
  negative: "bg-danger-bg text-danger-fg",
  info: "bg-info-bg text-info-fg",
};

export function StatCard({
  label,
  value,
  sublabel,
  tone = "default",
  icon: Icon,
}: {
  label: string;
  value: string;
  sublabel?: string;
  tone?: Tone;
  icon?: React.ComponentType<IconProps>;
}) {
  return (
    <div className="group rounded-2xl border border-border-subtle bg-surface p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-text-muted">{label}</p>
        {Icon ? (
          <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${TONE_ICON_WRAP[tone]}`}>
            <Icon className="h-4 w-4" />
          </span>
        ) : null}
      </div>
      <p className={`mt-3 text-2xl font-semibold tracking-tight ${TONE_VALUE[tone]}`}>{value}</p>
      {sublabel ? <p className="mt-1.5 text-xs text-text-muted">{sublabel}</p> : null}
    </div>
  );
}
