"use client";
import { useState } from "react";

export interface ScenarioValues {
  name: string;
  period: string;
  description: string;
}

/**
 * Shared create/edit form for a scenario's own fields. Used twice from page.tsx
 * (new scenario vs. editing the selected one) so the two paths can't drift.
 */
export function ScenarioForm(
  { initial, submitLabel, onSubmit, onCancel }: {
    initial: ScenarioValues;
    submitLabel: string;
    onSubmit: (values: ScenarioValues) => Promise<void> | void;
    onCancel: () => void;
  },
) {
  const [values, setValues] = useState<ScenarioValues>(initial);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!values.name.trim()) return;
    setBusy(true);
    try { await onSubmit(values); } finally { setBusy(false); }
  };

  return (
    <div className="border-b p-4 space-y-2 bg-gray-50">
      <input autoFocus placeholder="Scenario name" value={values.name}
        onChange={(e) => setValues({ ...values, name: e.target.value })}
        className="w-full rounded border px-2 py-1 text-sm" />
      <input placeholder="Period (e.g. Q4 2026)" value={values.period}
        onChange={(e) => setValues({ ...values, period: e.target.value })}
        className="w-full rounded border px-2 py-1 text-sm" />
      <input placeholder="Description (optional)" value={values.description}
        onChange={(e) => setValues({ ...values, description: e.target.value })}
        className="w-full rounded border px-2 py-1 text-sm" />
      <div className="flex gap-2">
        <button onClick={submit} disabled={busy || !values.name.trim()}
          className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-40">
          {submitLabel}
        </button>
        <button onClick={onCancel} className="rounded border px-3 py-1 text-sm hover:bg-gray-100">
          Cancel
        </button>
      </div>
    </div>
  );
}
