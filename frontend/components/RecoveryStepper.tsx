import { AlertIcon, CheckCircleIcon, ClockIcon, XCircleIcon } from "./icons";

export type StepState = "pending" | "completed" | "failed" | "action_required";

export interface StepperStep {
  label: string;
  description: string;
  state: StepState;
  detail?: React.ReactNode;
  action?: React.ReactNode;
}

const STATE_STYLES: Record<StepState, { ring: string; badgeBg: string; badgeFg: string; label: string }> = {
  pending: {
    ring: "border-border-subtle",
    badgeBg: "bg-slate-100 dark:bg-white/5",
    badgeFg: "text-text-muted",
    label: "Pending",
  },
  completed: {
    ring: "border-success-border",
    badgeBg: "bg-success-bg",
    badgeFg: "text-success-fg",
    label: "Completed",
  },
  failed: {
    ring: "border-danger-border",
    badgeBg: "bg-danger-bg",
    badgeFg: "text-danger-fg",
    label: "Failed",
  },
  action_required: {
    ring: "border-warning-border",
    badgeBg: "bg-warning-bg",
    badgeFg: "text-warning-fg",
    label: "Action Required",
  },
};

function StateIcon({ state }: { state: StepState }) {
  const className = "h-4 w-4";
  switch (state) {
    case "completed":
      return <CheckCircleIcon className={className} />;
    case "failed":
      return <XCircleIcon className={className} />;
    case "action_required":
      return <AlertIcon className={className} />;
    default:
      return <ClockIcon className={className} />;
  }
}

export function RecoveryStepper({ steps }: { steps: StepperStep[] }) {
  return (
    <ol className="space-y-3">
      {steps.map((step, i) => {
        const style = STATE_STYLES[step.state];
        return (
          <li key={step.label} className={`rounded-xl border p-4 transition-colors ${style.ring}`}>
            <div className="flex items-start gap-3">
              <span
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${style.badgeBg} ${style.badgeFg}`}
              >
                {step.state === "pending" ? i + 1 : <StateIcon state={step.state} />}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-foreground">{step.label}</p>
                  <span
                    className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${style.badgeBg} ${style.badgeFg}`}
                  >
                    {style.label}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-text-muted">{step.description}</p>
                {step.detail ? <div className="mt-2 text-sm">{step.detail}</div> : null}
                {step.action ? <div className="mt-3">{step.action}</div> : null}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
