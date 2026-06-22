"use client";
import {
  ResponsiveContainer, Tooltip, Cell,
  BarChart, Bar, LineChart, Line, PieChart, Pie,
  XAxis, YAxis,
} from "recharts";

// Generic chart driven entirely by a backend spec {chart_type, x, y, rows}.
// The agent picks the chart type + columns; this just renders. One component
// covers bar/line/pie, so "add a chart" needs no new frontend code.
const COLORS = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed", "#0891b2"];
const fmt = (v: any) => (typeof v === "number" ? v.toLocaleString("de-DE") : v);

export function ChartWidget(
  { data }: { data: { chart_type: string; x: string; y: string; title?: string; rows: any[] } },
) {
  const { chart_type, x, y, rows = [] } = data;

  if (!rows.length || !x || !y) {
    return <p className="text-sm text-gray-500">Nothing to chart.</p>;
  }

  return (
    <div className="w-full">
      {data.title && <div className="mb-1 text-sm font-medium capitalize">{data.title}</div>}
      <div className="h-64 w-full">
        <ResponsiveContainer>
          {chart_type === "pie" ? (
            <PieChart>
              <Tooltip formatter={fmt} />
              <Pie data={rows} dataKey={y} nameKey={x} outerRadius={90} label>
                {rows.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
            </PieChart>
          ) : chart_type === "line" ? (
            <LineChart data={rows} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
              <XAxis dataKey={x} fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip formatter={fmt} />
              <Line dataKey={y} stroke={COLORS[0]} strokeWidth={2} dot />
            </LineChart>
          ) : (
            <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
              <XAxis dataKey={x} fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip formatter={fmt} />
              <Bar dataKey={y}>
                {rows.map((r, i) => (
                  <Cell key={i} fill={typeof r[y] === "number" && r[y] < 0 ? "#16a34a" : COLORS[0]} />
                ))}
              </Bar>
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
