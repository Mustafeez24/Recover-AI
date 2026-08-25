import type { IconProps } from "./icons";
import { ListIcon } from "./icons";

export function EmptyState({
  title = "No recovery opportunities found.",
  description,
  icon: Icon = ListIcon,
}: {
  title?: string;
  description?: string;
  icon?: React.ComponentType<IconProps>;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-border-subtle py-16 text-center">
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-text-muted dark:bg-white/5">
        <Icon className="h-5 w-5" />
      </span>
      <p className="text-sm font-medium text-foreground">{title}</p>
      {description ? <p className="max-w-sm text-xs text-text-muted">{description}</p> : null}
    </div>
  );
}
