export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return <p className="py-12 text-center text-sm text-zinc-500 dark:text-zinc-400">{label}</p>;
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
      {message}
    </div>
  );
}
