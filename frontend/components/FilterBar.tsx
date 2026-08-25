import { formatLabel } from "@/lib/format";
import type { Priority } from "@/lib/types";

const PRIORITY_OPTIONS: Array<{ value: Priority | ""; label: string }> = [
  { value: "", label: "All" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

function Segmented({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-text-muted">Priority</span>
      <div className="inline-flex rounded-lg border border-border-subtle bg-slate-50 p-0.5 dark:bg-white/5">
        {PRIORITY_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              value === opt.value
                ? "bg-surface text-foreground shadow-sm"
                : "text-text-muted hover:text-foreground"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
}) {
  return (
    <label className="flex flex-col gap-1.5 text-xs font-medium text-text-muted">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-border-subtle bg-surface px-2.5 py-1.5 text-sm text-foreground shadow-sm focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
      >
        <option value="">All</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {formatLabel(opt)}
          </option>
        ))}
      </select>
    </label>
  );
}

export function FilterBar({
  priority,
  onPriorityChange,
  status,
  onStatusChange,
  failureCategory,
  onFailureCategoryChange,
  minAmount,
  onMinAmountChange,
  maxAmount,
  onMaxAmountChange,
  statuses,
  failureCategories,
}: {
  priority: string;
  onPriorityChange: (value: string) => void;
  status: string;
  onStatusChange: (value: string) => void;
  failureCategory: string;
  onFailureCategoryChange: (value: string) => void;
  minAmount: string;
  onMinAmountChange: (value: string) => void;
  maxAmount: string;
  onMaxAmountChange: (value: string) => void;
  statuses: string[];
  failureCategories: string[];
}) {
  return (
    <div className="flex flex-wrap items-end gap-4 rounded-2xl border border-border-subtle bg-surface p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <Segmented value={priority} onChange={onPriorityChange} />
      <Select label="Status" value={status} onChange={onStatusChange} options={statuses} />
      <Select
        label="Failure category"
        value={failureCategory}
        onChange={onFailureCategoryChange}
        options={failureCategories}
      />
      <label className="flex flex-col gap-1.5 text-xs font-medium text-text-muted">
        Min amount
        <input
          type="number"
          value={minAmount}
          onChange={(e) => onMinAmountChange(e.target.value)}
          className="w-28 rounded-lg border border-border-subtle bg-surface px-2.5 py-1.5 text-sm text-foreground shadow-sm focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
          placeholder="0"
        />
      </label>
      <label className="flex flex-col gap-1.5 text-xs font-medium text-text-muted">
        Max amount
        <input
          type="number"
          value={maxAmount}
          onChange={(e) => onMaxAmountChange(e.target.value)}
          className="w-28 rounded-lg border border-border-subtle bg-surface px-2.5 py-1.5 text-sm text-foreground shadow-sm focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500"
          placeholder="Any"
        />
      </label>
    </div>
  );
}
