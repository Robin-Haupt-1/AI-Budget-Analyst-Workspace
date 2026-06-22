import { Widget } from "@/lib/types";
import { DataTable } from "./widgets/DataTable";
import { ChartWidget } from "./widgets/ChartWidget";
import { StatCard } from "./widgets/StatCard";

// Single switch from agent-chosen widget kind -> presentational component.
// All three are generic and reusable: a table for any rows, a chart for any
// series, a card for any label/value stats. Adding a data tool needs no new widget.
export function WidgetRenderer({ widget }: { widget: Widget }) {
  switch (widget.kind) {
    case "data_table": return <DataTable data={widget.data} />;
    case "chart": return <ChartWidget data={widget.data} />;
    case "stat_card": return <StatCard data={widget.data} />;
    default: return null;
  }
}
