"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { SentimentAggregatePoint } from "../lib/api";

interface Props {
  data: SentimentAggregatePoint[];
}

export function SentimentChart({ data }: Props) {
  if (!data.length) {
    return (
      <p className="text-sm text-slate-400">
        No sentiment history available for this symbol yet.
      </p>
    );
  }

  const chartData = data.map((d) => ({
    ...d,
    // Map raw score (-1..1-ish) to 0–100 for easier reading
    scoreScaled: Math.round(((d.sentiment_score + 1) / 2) * 100),
  }));

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ left: 0, right: 8, top: 8 }}>
          <XAxis
            dataKey="date"
            tickLine={false}
            tickMargin={8}
            tick={{ fontSize: 11, fill: "#94a3b8" }}
          />
          <YAxis
            domain={[0, 100]}
            tickMargin={8}
            tick={{ fontSize: 11, fill: "#94a3b8" }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#020617",
              border: "1px solid #1e293b",
              borderRadius: 8,
              fontSize: 12,
            }}
            labelStyle={{ color: "#e2e8f0" }}
          />
          <ReferenceLine
            y={50}
            stroke="#64748b"
            strokeDasharray="3 3"
            ifOverflow="extendDomain"
          />
          <Line
            type="monotone"
            dataKey="scoreScaled"
            stroke="#38bdf8"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

