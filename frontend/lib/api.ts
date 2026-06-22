import { Scenario, LineItem } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}

export const api = {
  base: BASE,
  listScenarios: () => fetch(`${BASE}/api/scenarios/`).then(j<Scenario[]>),
  getScenario: (id: number) => fetch(`${BASE}/api/scenarios/${id}/`).then(j<Scenario>),
  createScenario: (body: Partial<Scenario>) =>
    fetch(`${BASE}/api/scenarios/`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<Scenario>),
  updateScenario: (id: number, body: Partial<Scenario>) =>
    fetch(`${BASE}/api/scenarios/${id}/`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<Scenario>),
  deleteScenario: (id: number) =>
    fetch(`${BASE}/api/scenarios/${id}/`, { method: "DELETE" }),
  createLineItem: (body: Partial<LineItem>) =>
    fetch(`${BASE}/api/line-items/`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<LineItem>),
  updateLineItem: (id: number, body: Partial<LineItem>) =>
    fetch(`${BASE}/api/line-items/${id}/`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<LineItem>),
  deleteLineItem: (id: number) =>
    fetch(`${BASE}/api/line-items/${id}/`, { method: "DELETE" }),
};
