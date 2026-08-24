"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function BarChartCard({
  title,
  data,
  dataKey = "value",
  labelKey = "label",
  color = "#3b82f6",
  formatValue,
}: {
  title: string;
  data: Array<Record<string, string | number>>;
  dataKey?: string;
  labelKey?: string;
  color?: string;
  formatValue?: (value: number) => string;
}) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
      <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">{title}</p>
      {data.length === 0 ? (
        <p className="py-10 text-center text-sm text-zinc-400">No data yet</p>
      ) : (
        <div className="mt-4 h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-zinc-200 dark:stroke-zinc-800" />
              <XAxis dataKey={labelKey} tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip
                formatter={(value) => (formatValue ? formatValue(Number(value)) : value)}
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
              />
              <Bar dataKey={dataKey} fill={color} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
