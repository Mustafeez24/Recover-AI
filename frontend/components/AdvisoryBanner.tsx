import { ShieldIcon } from "./icons";

export function AdvisoryBanner() {
  return (
    <div className="w-full border-b border-info-border bg-info-bg px-4 py-2">
      <div className="mx-auto flex max-w-[1400px] items-center justify-center gap-2 text-center text-sm text-info-fg">
        <ShieldIcon className="h-4 w-4 shrink-0" />
        <span className="font-semibold">Simulation Mode</span>
        <span className="hidden text-info-fg/80 sm:inline">
          — All recovery actions are advisory and simulated. No real payments are executed.
        </span>
      </div>
    </div>
  );
}
