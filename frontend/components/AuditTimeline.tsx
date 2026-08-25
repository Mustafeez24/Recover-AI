import { formatCurrency, formatDateTime, formatLabel } from "@/lib/format";
import type { HistoryEvent } from "@/lib/types";

import { CheckCircleIcon, ClockIcon, XCircleIcon } from "./icons";

const TERMINAL_POSITIVE = new Set(["recovered"]);
const TERMINAL_NEGATIVE = new Set(["failed", "escalated", "exhausted"]);

function EventIcon({ newState }: { newState: string }) {
  const className = "h-3.5 w-3.5";
  if (TERMINAL_POSITIVE.has(newState)) return <CheckCircleIcon className={className} />;
  if (TERMINAL_NEGATIVE.has(newState)) return <XCircleIcon className={className} />;
  return <ClockIcon className={className} />;
}

function eventTone(newState: string): { dot: string; ring: string } {
  if (TERMINAL_POSITIVE.has(newState)) return { dot: "bg-success-fg text-white", ring: "ring-success-border" };
  if (TERMINAL_NEGATIVE.has(newState)) return { dot: "bg-danger-fg text-white", ring: "ring-danger-border" };
  return { dot: "bg-accent-500 text-white", ring: "ring-accent-500/30" };
}

export function AuditTimeline({ events }: { events: HistoryEvent[] }) {
  if (events.length === 0) {
    return <p className="py-6 text-sm text-text-muted">No recovery actions have been taken on this case yet.</p>;
  }

  return (
    <ol className="mt-4 space-y-5">
      {events.map((event, i) => {
        const tone = eventTone(event.new_state);
        return (
          <li key={i} className="relative flex gap-3 pb-1">
            {i < events.length - 1 ? (
              <span className="absolute left-3.5 top-8 h-[calc(100%-1rem)] w-px bg-border-subtle" aria-hidden="true" />
            ) : null}
            <span
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ring-4 ring-offset-0 ${tone.dot} ${tone.ring}`}
            >
              <EventIcon newState={event.new_state} />
            </span>
            <div className="min-w-0 flex-1 pt-0.5">
              <p className="text-sm">
                <span className="font-semibold text-foreground">{formatLabel(event.previous_state)}</span>
                <span className="mx-1.5 text-text-muted">→</span>
                <span className="font-semibold text-foreground">{formatLabel(event.new_state)}</span>
                {event.action ? <span className="ml-1.5 text-text-muted">({formatLabel(event.action)})</span> : null}
              </p>
              {event.reason ? <p className="mt-0.5 text-xs text-text-muted">{event.reason}</p> : null}
              {event.amount ? (
                <p className="mt-0.5 text-xs font-medium text-success-fg">
                  Simulated amount: {formatCurrency(event.amount)}
                </p>
              ) : null}
              <p className="mt-1 text-[11px] text-text-muted/80">{formatDateTime(event.created_at)}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
