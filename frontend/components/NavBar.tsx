"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/opportunities", label: "Opportunities" },
  { href: "/ai", label: "AI Analytics" },
];

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="border-b border-zinc-200 bg-white dark:border-zinc-800 dark:bg-black">
      <div className="mx-auto flex max-w-7xl items-center gap-8 px-6 py-4">
        <Link href="/" className="text-lg font-semibold text-black dark:text-zinc-50">
          RecoverAI
        </Link>
        <nav className="flex gap-6">
          {LINKS.map((link) => {
            const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm font-medium transition-colors ${
                  active
                    ? "text-black dark:text-zinc-50"
                    : "text-zinc-500 hover:text-black dark:text-zinc-400 dark:hover:text-zinc-50"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
