import { CheckCircleIcon, CpuIcon } from "./icons";

export function AIStatusCard({ available }: { available: boolean }) {
  if (available) {
    return (
      <div className="flex items-center gap-4 rounded-2xl border border-success-border bg-success-bg p-5">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/60 text-success-fg dark:bg-black/20">
          <CheckCircleIcon className="h-5.5 w-5.5" />
        </span>
        <div>
          <p className="text-sm font-semibold text-success-fg">AI Provider Available</p>
          <p className="mt-0.5 text-xs text-success-fg/80">
            Local Ollama (Qwen 2.5 3B) is reachable and producing advisory recommendations.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-4 rounded-2xl border border-info-border bg-info-bg p-5">
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/60 text-info-fg dark:bg-black/20">
        <CpuIcon className="h-5.5 w-5.5" />
      </span>
      <div>
        <p className="text-sm font-semibold text-info-fg">AI Provider Unavailable</p>
        <p className="mt-0.5 text-xs text-info-fg/80">
          RecoverAI is safely falling back to deterministic recovery actions. No advisory recommendations are lost
          — every case still gets a validated, rules-based action.
        </p>
      </div>
    </div>
  );
}
