"use client";

import { MenuIcon, ShieldIcon } from "./icons";

export function Topbar({ onMenuClick }: { onMenuClick: () => void }) {
  return (
    <header className="sticky top-0 z-20 flex items-center gap-4 border-b border-border-subtle bg-surface/80 px-4 py-3.5 backdrop-blur-sm sm:px-6 lg:px-10">
      <button
        type="button"
        onClick={onMenuClick}
        aria-label="Open navigation"
        className="rounded-lg p-1.5 text-foreground hover:bg-slate-100 dark:hover:bg-white/10 lg:hidden"
      >
        <MenuIcon className="h-5 w-5" />
      </button>

      <div className="flex-1" />

      <span className="inline-flex items-center gap-1.5 rounded-full border border-info-border bg-info-bg px-3 py-1 text-xs font-semibold uppercase tracking-wide text-info-fg">
        <ShieldIcon className="h-3.5 w-3.5" />
        Simulation Mode
      </span>

      <div className="flex items-center gap-2.5 border-l border-border-subtle pl-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-900 text-xs font-semibold text-white dark:bg-accent-500">
          M
        </span>
        <span className="hidden text-sm font-medium text-foreground sm:inline">Mustafeez</span>
      </div>
    </header>
  );
}
