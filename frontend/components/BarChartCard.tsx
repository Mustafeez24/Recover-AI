"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function BarChartCard({
  title,
  description,
  data,
  dataKey = "value",
  labelKey = "label",
  color = "var(--color-accent-500)",
  formatValue,
}: {
  title: string;
  description?: string;
  data: Array<Record<string, string | number>>;
  dataKey?: string;
  labelKey?: string;
  color?: string;
  formatValue?: (value: number) => string;
}) {
  return (
    <div className="rounded-2xl border border-border-subtle bg-surface p-6 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <p className="text-sm font-semibold text-foreground">{title}</p>
      {description ? <p className="mt-1 text-xs text-text-muted">{description}</p> : null}
      {data.length === 0 ? (
        <p className="py-14 text-center text-sm text-text-muted">No data yet</p>
      ) : (
        <div className="mt-4 h-64 w-full animate-fade-in">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 6" stroke="var(--color-border-subtle)" />
              <XAxis
                dataKey={labelKey}
                tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
                axisLine={{ stroke: "var(--color-border-subtle)" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 12, fill: "var(--color-text-muted)" }}
                axisLine={false}
                tickLine={false}
                width={40}
              />
              <Tooltip
                cursor={{ fill: "var(--color-border-subtle)", opacity: 0.4 }}
                formatter={(value) => (formatValue ? formatValue(Number(value)) : value)}
                contentStyle={{
                  fontSize: 12,
                  borderRadius: 10,
                  border: "1px solid var(--color-border-subtle)",
                  boxShadow: "0 4px 12px rgba(15,23,42,0.08)",
                }}
              />
              <Bar dataKey={dataKey} fill={color} radius={[6, 6, 0, 0]} maxBarSize={56} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
