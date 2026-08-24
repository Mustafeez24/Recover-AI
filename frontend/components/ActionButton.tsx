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
    primary: "bg-black text-white hover:bg-zinc-800 dark:bg-zinc-50 dark:text-black dark:hover:bg-zinc-200",
    secondary:
      "bg-white text-black border border-zinc-300 hover:bg-zinc-50 dark:bg-zinc-900 dark:text-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800",
    danger: "bg-red-600 text-white hover:bg-red-700",
  };

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isPending || disabled}
      className={`rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${variantClasses[variant]}`}
    >
      {isPending ? (pendingLabel ?? "Working…") : children}
    </button>
  );
}
