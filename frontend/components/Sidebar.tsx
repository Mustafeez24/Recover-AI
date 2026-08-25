"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { CloseIcon, CpuIcon, DashboardIcon, ListIcon, SparkleIcon } from "./icons";

const LINKS = [
  { href: "/", label: "Dashboard", icon: DashboardIcon },
  { href: "/opportunities", label: "Opportunities", icon: ListIcon },
  { href: "/ai", label: "AI Analytics", icon: CpuIcon },
];

const LOWER_LINKS = ["Settings", "Documentation"];

export function Wordmark() {
  return (
    <span className="flex items-center gap-2">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-accent-500 to-accent-600 text-white shadow-sm">
        <SparkleIcon className="h-4.5 w-4.5" />
      </span>
      <span className="text-base font-semibold tracking-tight text-white">
        Recover<span className="text-accent-400">AI</span>
      </span>
    </span>
  );
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav className="flex flex-1 flex-col gap-1">
      {LINKS.map((link) => {
        const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
        const Icon = link.icon;
        return (
          <Link
            key={link.href}
            href={link.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
              active
                ? "bg-white/10 text-white"
                : "text-slate-400 hover:bg-white/5 hover:text-white"
            }`}
          >
            <Icon className="h-4.5 w-4.5 shrink-0" />
            {link.label}
            {active ? <span className="ml-auto h-1.5 w-1.5 rounded-full bg-accent-400" /> : null}
          </Link>
        );
      })}
    </nav>
  );
}

function LowerNav() {
  return (
    <div className="mt-auto space-y-1 border-t border-white/10 pt-4">
      {LOWER_LINKS.map((label) => (
        <span
          key={label}
          aria-disabled="true"
          className="flex cursor-not-allowed items-center justify-between rounded-lg px-3 py-2 text-sm text-slate-500"
        >
          {label}
          <span className="rounded-full bg-white/5 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">
            Soon
          </span>
        </span>
      ))}
    </div>
  );
}

export function Sidebar({ mobileOpen, onClose }: { mobileOpen: boolean; onClose: () => void }) {
  return (
    <>
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col bg-brand-950 px-4 py-6 lg:flex">
        <div className="px-2">
          <Wordmark />
        </div>
        <div className="mt-8 flex flex-1 flex-col">
          <NavLinks />
          <LowerNav />
        </div>
      </aside>

      {/* Mobile drawer */}
      {mobileOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />
          <aside className="absolute inset-y-0 left-0 flex w-72 flex-col bg-brand-950 px-4 py-6 shadow-xl animate-fade-in">
            <div className="flex items-center justify-between px-2">
              <Wordmark />
              <button
                type="button"
                onClick={onClose}
                aria-label="Close navigation"
                className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white"
              >
                <CloseIcon className="h-5 w-5" />
              </button>
            </div>
            <div className="mt-8 flex flex-1 flex-col">
              <NavLinks onNavigate={onClose} />
              <LowerNav />
            </div>
          </aside>
        </div>
      ) : null}
    </>
  );
}
