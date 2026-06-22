"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { Scenario, LineItem } from "@/lib/types";

const fmt = (s: string | number) =>
  Number(s).toLocaleString("de-DE", { maximumFractionDigits: 0 });

const EMPTY_DRAFT = { department: "", category: "", budget_amount: "", actual_amount: "", notes: "" };
type Draft = typeof EMPTY_DRAFT;

/**
 * Full CRUD over a scenario's line items: add, inline-edit (update), and delete.
 * This is the reviewer's data-entry surface; the AI side only ever reads it.
 * Totals here are a plain display sum of the stored rows — all *analysis* numbers
 * (variance/severity/what-if) come from the backend's deterministic module.
 */
export function ScenarioManager(
  { scenario, onReload }: { scenario: Scenario | null; onReload: () => void },
) {
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<Draft>(EMPTY_DRAFT);
  const [busy, setBusy] = useState(false);

  if (!scenario) return <p className="text-sm text-gray-500 p-4">No scenario selected.</p>;

  const items = scenario.line_items;
  const totalBudget = items.reduce((s, li) => s + Number(li.budget_amount), 0);
  const totalActual = items.reduce((s, li) => s + Number(li.actual_amount), 0);
  const totalVariance = totalActual - totalBudget;

  const add = async () => {
    if (!draft.department || !draft.category) return;
    setBusy(true);
    try {
      await api.createLineItem({
        scenario: scenario.id,
        ...draft,
        budget_amount: draft.budget_amount || "0",
        actual_amount: draft.actual_amount || "0",
      } as Partial<LineItem>);
      setDraft(EMPTY_DRAFT);
      onReload();
    } finally { setBusy(false); }
  };

  const startEdit = (li: LineItem) => {
    setEditingId(li.id);
    setEditDraft({
      department: li.department, category: li.category,
      budget_amount: li.budget_amount, actual_amount: li.actual_amount,
      notes: li.notes ?? "",
    });
  };

  const saveEdit = async (id: number) => {
    setBusy(true);
    try {
      await api.updateLineItem(id, editDraft as Partial<LineItem>);
      setEditingId(null);
      onReload();
    } finally { setBusy(false); }
  };

  const del = async (id: number) => { await api.deleteLineItem(id); onReload(); };

  const editField = (key: keyof Draft, extra = "") => (
    <input
      value={editDraft[key]}
      onChange={(e) => setEditDraft({ ...editDraft, [key]: e.target.value })}
      className={`w-full rounded border px-1 py-0.5 text-sm ${extra}`}
    />
  );

  return (
    <div className="p-4 space-y-3">
      <div>
        <h2 className="font-medium">
          {scenario.name}{" "}
          <span className="text-gray-400 text-sm">· {scenario.period}</span>
        </h2>
        {scenario.description && (
          <p className="text-xs text-gray-500">{scenario.description}</p>
        )}
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 border-b">
            <th className="py-1">Dept</th><th>Category</th>
            <th className="text-right">Budget</th><th className="text-right">Actual</th>
            <th className="text-right">Variance</th><th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((li) => {
            const variance = Number(li.actual_amount) - Number(li.budget_amount);
            if (editingId === li.id) {
              return (
                <tr key={li.id} className="border-b last:border-0 bg-amber-50/50">
                  <td className="py-1 pr-1">{editField("department")}</td>
                  <td className="pr-1">{editField("category")}</td>
                  <td className="pr-1">{editField("budget_amount", "text-right")}</td>
                  <td className="pr-1">{editField("actual_amount", "text-right")}</td>
                  <td colSpan={2} className="align-top text-right whitespace-nowrap">
                    <button disabled={busy} onClick={() => saveEdit(li.id)}
                      className="text-xs text-green-700 px-1">save</button>
                    <button onClick={() => setEditingId(null)}
                      className="text-xs text-gray-400 px-1">cancel</button>
                    <div className="pt-1">{editField("notes")}</div>
                  </td>
                </tr>
              );
            }
            return (
              <tr key={li.id} className="border-b last:border-0 group align-top">
                <td className="py-1">
                  {li.department}
                  {li.notes && (
                    <p className="text-xs font-normal text-gray-500 italic">{li.notes}</p>
                  )}
                </td>
                <td>{li.category}</td>
                <td className="text-right">{fmt(li.budget_amount)}</td>
                <td className="text-right">{fmt(li.actual_amount)}</td>
                <td className={`text-right ${variance > 0 ? "text-red-600" : "text-green-600"}`}>
                  {variance > 0 ? "+" : ""}{fmt(variance)}
                </td>
                <td className="text-right whitespace-nowrap">
                  <button onClick={() => startEdit(li)}
                    className="text-xs text-blue-500 px-1 opacity-0 group-hover:opacity-100">edit</button>
                  <button onClick={() => del(li.id)}
                    className="text-xs text-red-500 px-1">✕</button>
                </td>
              </tr>
            );
          })}
        </tbody>
        <tfoot>
          <tr className="border-t font-medium">
            <td className="py-1" colSpan={2}>Total</td>
            <td className="text-right">{fmt(totalBudget)}</td>
            <td className="text-right">{fmt(totalActual)}</td>
            <td className={`text-right ${totalVariance > 0 ? "text-red-600" : "text-green-600"}`}>
              {totalVariance > 0 ? "+" : ""}{fmt(totalVariance)}
            </td>
            <td></td>
          </tr>
        </tfoot>
      </table>

      {/* Add a line item */}
      <div className="space-y-1">
        <div className="grid grid-cols-5 gap-1 text-sm">
          {(["department", "category", "budget_amount", "actual_amount"] as const).map((f) => (
            <input key={f} placeholder={f.split("_")[0]} value={draft[f]}
              onChange={(e) => setDraft({ ...draft, [f]: e.target.value })}
              className="rounded border px-2 py-1" />
          ))}
          <button onClick={add} disabled={busy}
            className="rounded bg-gray-800 text-white text-sm disabled:opacity-40">Add</button>
        </div>
        <input placeholder="notes (optional)" value={draft.notes}
          onChange={(e) => setDraft({ ...draft, notes: e.target.value })}
          className="w-full rounded border px-2 py-1 text-sm" />
      </div>
    </div>
  );
}
