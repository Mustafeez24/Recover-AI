export function ActionButton({
  onClick,
  isPending,
  pendingLabel,
  children,
  variant = "primary",
  disabled,
}: {
  onClick: () => void;
  isPending: boolean;
  pendingLabel?: string;
  children: React.ReactNode;
  variant?: "primary" | "secondary" | "danger";
  disabled?: boolean;
}) {
  const variantClasses: Record<string, string> = {
    primary:
      "bg-brand-900 text-white shadow-sm hover:bg-brand-800 focus-visible:outline-accent-500 dark:bg-accent-500 dark:hover:bg-accent-400",
    secondary:
      "bg-surface text-foreground border border-border-subtle hover:bg-slate-50 focus-visible:outline-accent-500 dark:hover:bg-white/5",
    danger: "bg-danger-fg text-white shadow-sm hover:brightness-110 focus-visible:outline-danger-fg",
  };

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isPending || disabled}
      className={`inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-150 outline-offset-2 focus-visible:outline-2 disabled:cursor-not-allowed disabled:opacity-50 ${variantClasses[variant]}`}
    >
      {isPending ? (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : null}
      {isPending ? (pendingLabel ?? "Working…") : children}
    </button>
  );
}
