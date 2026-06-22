// Generic table for any data/calculation tool result. Columns come from the
// backend (or are inferred from the first row), so adding a new data tool needs
// no new frontend component — this renders whatever rows it's given.
const sevColor: Record<string, string> = {
  High: "bg-red-100 text-red-800",
  Medium: "bg-amber-100 text-amber-800",
  Low: "bg-gray-100 text-gray-600",
};

const isNum = (v: unknown): v is number => typeof v === "number";
const fmt = (v: unknown) =>
  isNum(v) ? v.toLocaleString("de-DE", { maximumFractionDigits: 0 }) : String(v ?? "");
const label = (c: string) => c.replace(/_/g, " ");

export function DataTable(
  { data }: { data: { title?: string; columns?: string[]; rows: any[] } },
) {
  const rows = data.rows ?? [];
  const columns = data.columns?.length ? data.columns : Object.keys(rows[0] ?? {});

  return (
    <div>
      {data.title && <div className="mb-1 text-sm font-medium">{data.title}</div>}
      {rows.length === 0 ? (
        <p className="text-sm text-gray-500">No data.</p>
      ) : (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b text-left text-gray-500">
              {columns.map((c) => (
                <th key={c}
                  className={`py-1 pr-3 capitalize ${isNum(rows[0]?.[c]) ? "text-right" : ""}`}>
                  {label(c)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b last:border-0">
                {columns.map((c) => {
                  const v = r[c];
                  if (c === "severity") {
                    return (
                      <td key={c} className="pr-3">
                        <span className={`rounded px-2 py-0.5 text-xs ${sevColor[v] ?? ""}`}>{v}</span>
                      </td>
                    );
                  }
                  const num = isNum(v);
                  const variance = c === "variance" && num;
                  return (
                    <td key={c}
                      className={`pr-3 ${num ? "text-right tabular-nums" : ""} ${
                        variance ? (v > 0 ? "text-red-600" : "text-green-600") : ""}`}>
                      {variance && v > 0 ? "+" : ""}{fmt(v)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
