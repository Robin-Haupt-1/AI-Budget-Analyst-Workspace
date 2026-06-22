"use client";
import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { Scenario } from "@/lib/types";
import { ScenarioManager } from "@/components/ScenarioManager";
import { ScenarioForm } from "@/components/ScenarioForm";
import { Chat } from "@/components/Chat";

type Mode = "none" | "create" | "edit";

export default function Home() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [mode, setMode] = useState<Mode>("none");

  const loadList = useCallback(async () => {
    const list = await api.listScenarios();
    setScenarios(list);
    setSelectedId((cur) => (cur == null && list.length ? list[0].id : cur));
  }, []);

  const loadScenario = useCallback(async () => {
    if (selectedId != null) setScenario(await api.getScenario(selectedId));
    else setScenario(null);
  }, [selectedId]);

  useEffect(() => { loadList(); }, [loadList]);
  useEffect(() => { loadScenario(); }, [loadScenario]);

  const select = (id: number | null) => { setMode("none"); setSelectedId(id); };

  const deleteScenario = async () => {
    if (selectedId == null) return;
    if (!confirm(`Delete scenario "${scenario?.name}" and all its line items?`)) return;
    await api.deleteScenario(selectedId);
    setSelectedId(null);
    await loadList();
  };

  return (
    <main className="h-full flex">
      <section className="w-1/2 border-r bg-white overflow-y-auto">
        <header className="border-b p-4 flex flex-wrap items-center gap-2">
          <h1 className="font-semibold">AI Budget Analyst</h1>
          <select className="ml-auto rounded border px-2 py-1 text-sm"
            value={selectedId ?? ""} onChange={(e) => select(Number(e.target.value))}>
            {scenarios.length === 0 && <option value="">No scenarios</option>}
            {scenarios.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <button onClick={() => setMode((m) => (m === "create" ? "none" : "create"))}
            className="rounded border px-2 py-1 text-sm hover:bg-gray-50">
            {mode === "create" ? "Cancel" : "+ New"}
          </button>
          {selectedId != null && (
            <>
              <button onClick={() => setMode((m) => (m === "edit" ? "none" : "edit"))}
                className="rounded border px-2 py-1 text-sm hover:bg-gray-50">
                {mode === "edit" ? "Cancel" : "Edit"}
              </button>
              <button onClick={deleteScenario}
                className="rounded border px-2 py-1 text-sm text-red-600 hover:bg-red-50">
                Delete
              </button>
            </>
          )}
        </header>

        {mode === "create" && (
          <ScenarioForm
            initial={{ name: "", period: "", description: "" }}
            submitLabel="Create scenario"
            onCancel={() => setMode("none")}
            onSubmit={async (v) => {
              const created = await api.createScenario(v);
              setMode("none");
              await loadList();
              setSelectedId(created.id);
            }}
          />
        )}

        {mode === "edit" && scenario && (
          <ScenarioForm
            key={scenario.id}
            initial={{ name: scenario.name, period: scenario.period, description: scenario.description }}
            submitLabel="Save changes"
            onCancel={() => setMode("none")}
            onSubmit={async (v) => {
              await api.updateScenario(scenario.id, v);
              setMode("none");
              await loadList();
              await loadScenario();
            }}
          />
        )}

        <ScenarioManager scenario={scenario} onReload={loadScenario} />
      </section>
      <section className="w-1/2 bg-white">
        <Chat scenarioId={selectedId} />
      </section>
    </main>
  );
}
