import { Fragment } from "react";

// Generic, reusable card: a title + a list of label/value items, each with an
// optional tone that colours the value. Any tool can emit one (the what-if is
// just the first user). Numbers are computed server-side; this only presents.
const tone: Record<string, string> = {
  good: "text-green-600",
  bad: "text-red-600",
  neutral: "",
};

const fmt = (v: unknown) =>
  typeof v === "number" ? v.toLocaleString("de-DE", { maximumFractionDigits: 0 }) : String(v ?? "");

export function StatCard(
  { data }: { data: { title?: string; items: { label: string; value: any; tone?: string }[] } },
) {
  return (
    <div className="rounded border p-3 space-y-1 bg-blue-50/40">
      {data.title && <div className="font-medium">{data.title}</div>}
      <div className="grid grid-cols-2 gap-x-4 text-sm">
        {(data.items ?? []).map((it, i) => {
          const signed = typeof it.value === "number" && it.value > 0 && it.tone;
          return (
            <Fragment key={i}>
              <span className="text-gray-500">{it.label}</span>
              <span className={`text-right ${it.tone ? tone[it.tone] ?? "" : ""}`}>
                {signed ? "+" : ""}{fmt(it.value)}
              </span>
            </Fragment>
          );
        })}
      </div>
    </div>
  );
}
