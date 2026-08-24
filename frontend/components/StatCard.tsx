export function StatCard({
  label,
  value,
  sublabel,
  tone = "default",
}: {
  label: string;
  value: string;
  sublabel?: string;
  tone?: "default" | "positive" | "warning" | "negative";
}) {
  const toneClasses: Record<string, string> = {
    default: "text-black dark:text-zinc-50",
    positive: "text-emerald-600 dark:text-emerald-400",
    warning: "text-amber-600 dark:text-amber-400",
    negative: "text-red-600 dark:text-red-400",
  };

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
      <p className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${toneClasses[tone]}`}>{value}</p>
      {sublabel ? <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">{sublabel}</p> : null}
    </div>
  );
}
