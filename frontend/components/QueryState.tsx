import { AlertIcon } from "./icons";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-sm text-text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-accent-500 border-t-transparent" />
      {label}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-danger-border bg-danger-bg px-4 py-3.5 text-sm text-danger-fg">
      <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">
        <p className="font-medium">Unable to load recovery data.</p>
        <p className="mt-0.5 text-danger-fg/80">{message}</p>
      </div>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="shrink-0 rounded-lg border border-danger-border bg-white/50 px-3 py-1.5 text-xs font-medium text-danger-fg transition-colors hover:bg-white dark:bg-white/5 dark:hover:bg-white/10"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}
