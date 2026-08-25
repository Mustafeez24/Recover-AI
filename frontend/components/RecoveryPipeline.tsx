import type { IconProps } from "./icons";
import { ArrowRightIcon } from "./icons";

export interface PipelineStage {
  label: string;
  description: string;
  value: string;
  icon: React.ComponentType<IconProps>;
}

export function RecoveryPipeline({ stages }: { stages: PipelineStage[] }) {
  return (
    <div className="grid grid-cols-1 gap-3 lg:grid-cols-[repeat(auto-fit,minmax(0,1fr))]">
      {stages.map((stage, i) => {
        const Icon = stage.icon;
        return (
          <div key={stage.label} className="flex items-center gap-3 lg:flex-col lg:items-stretch lg:gap-0">
            <div className="flex flex-1 flex-col gap-2.5 rounded-2xl border border-border-subtle bg-surface p-4 transition-shadow hover:shadow-md lg:min-h-[168px]">
              <div className="flex items-center justify-between">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-500/10 text-accent-600 dark:text-accent-400">
                  <Icon className="h-4.5 w-4.5" />
                </span>
                <span className="text-[11px] font-semibold text-text-muted">Step {i + 1}</span>
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">{stage.label}</p>
                <p className="mt-0.5 text-xs leading-relaxed text-text-muted">{stage.description}</p>
              </div>
              <p className="mt-auto text-lg font-semibold tracking-tight text-foreground">{stage.value}</p>
            </div>
            {i < stages.length - 1 ? (
              <ArrowRightIcon className="hidden h-4 w-4 shrink-0 text-text-muted lg:mx-auto lg:my-2 lg:block lg:rotate-0" />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
