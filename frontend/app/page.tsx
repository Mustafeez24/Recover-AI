export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 px-6 text-center dark:bg-black">
      <h1 className="text-4xl font-semibold tracking-tight text-black dark:text-zinc-50">
        RecoverAI
      </h1>
      <p className="mt-4 max-w-xl text-lg text-zinc-600 dark:text-zinc-400">
        AI-powered revenue recovery: detect leakage, analyze, recommend
        recovery actions, execute, and measure recovered revenue.
      </p>
      <p className="mt-8 text-sm text-zinc-500 dark:text-zinc-500">
        Backend health check:{" "}
        <code className="rounded bg-black/[.06] px-1.5 py-0.5 font-mono dark:bg-white/[.08]">
          GET /health
        </code>
      </p>
    </div>
  );
}
