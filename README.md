# AI Budget Analyst Workspace

A small full-stack workspace where a reviewer manages budget scenarios and asks
an AI assistant questions about them, getting back **interactive results**
(data tables, charts, stat cards) over a streaming chat.

## What I built
- **CRUD** for budget scenarios and line items (Django REST Framework): create,
  edit, and delete scenarios; add, inline-edit, and delete their line items, all
  from the workspace UI.
- **AI assistant** (OpenAI Agents SDK) that answers questions about a selected
  scenario by calling tools that compute over the saved data — never by guessing.
- **Streaming chat** over **Server-Sent Events** with a small, explicit event
  protocol between backend and frontend.
- **Generic, reusable display components**: three widget kinds cover everything —
  a **DataTable** (any rows/columns), a **ChartWidget** (Recharts bar/line/pie),
  and a **StatCard** (any label/value stats, e.g. the what-if). None are tied to a
  specific analysis.
- **Decoupled data ↔ charts**: data/calculation tools (`list_scenarios`,
  `load_scenario_data`, `get_variances`, `group_by`, `get_top_risks`) return data
  (rendered as tables) and can be **filtered** (e.g. `load_scenario_data(
  department="Marketing")` for "list just the marketing items"). Charting is
  separate: `show_chart` plots a loaded dataset, and `chart_values(labels, values)`
  plots specific numbers the agent gathered. The agent runs data tools, then
  decides which chart, if any, to draw.
- **Follow-up turns** (e.g. "group this by department", "show only high risk").
- **Persisted chat history**: each budget's conversation is saved per-scenario in
  the browser (localStorage) and restored on reload and when switching budgets,
  with a per-budget **"Clear history"** button.
- Bonus — **"How was this calculated?"** inspector: per answer, shows the
  deterministic tool calls (name + params) that produced it.

## How to run
```bash
cp .env.example .env        # add your OPENAI_API_KEY
docker-compose up
```
- Frontend: http://localhost:3000  ·  Backend API: http://localhost:8000
- On startup the backend runs `migrate`, which also applies a **data migration**
  (`budgets/migrations/0002_seed_demo_data.py`) that loads the demo data — so a
  plain `migrate` produces a ready-to-demo database with no extra step. You get
  two scenarios: **"Q2 2026 Operating Budget"** (contains the brief's example
  rows — Marketing/Paid Ads 50000/65000, etc.) and a **"Q3 2026 Forecast"** so
  the scenario selector is meaningful.
- **Dev setup:** the images bake only the dependency install layer; the app
  source is **bind-mounted** into each container (see `docker-compose.yml`
  `volumes:`), so editing files on the host hot-reloads both services
  (uvicorn `--reload` / Next dev) without a rebuild. The frontend keeps the
  image's `node_modules` via an anonymous volume so the host mount can't hide it.

### Required environment variables
Set in `.env` (copied from `.env.example`); `docker-compose` reads it.

| var | purpose | default |
|-----|---------|---------|
| `OPENAI_API_KEY` | OpenAI access for the agent | (required) |
| `OPENAI_MODEL`   | model for narration / tool choice | `gpt-4o` |
| `BACKEND_PORT`   | host port for the Django API | `8000` |
| `FRONTEND_PORT`  | host port for the Next.js app | `3000` |

### Tests
```bash
docker-compose run --rm backend python manage.py test
```
Runs Django's standard test runner inside the backend container (no local Python
setup needed). The data migration seeds the test database, so the API/seed tests
run against the demo scenarios. To run a subset, e.g. just the finance logic:
`docker-compose run --rm backend python manage.py test budgets.tests.test_analysis`.

## AI/agent approach and why
The brief preferred the **OpenAI Agents SDK**, which I used. The defining design
choice is the **model/computation boundary**: the LLM orchestrates and narrates,
but **every number is computed by deterministic Python** in `budgets/analysis.py`
and exposed to the agent as tools. In a finance product where every figure must
be correct, letting the model do arithmetic is unacceptable — so it structurally
can't. Tools return structured payloads that are *both* the UI widget and the
thing the model narrates (single source of truth), so the displayed numbers and
the spoken summary can never diverge.

**Charts are decoupled from calculation.** Data/calculation tools produce data
(shown as generic tables); a separate `show_chart` tool only *visualizes* a
dataset a data tool already cached in the run context — it picks chart type and
columns, never values. So the agent runs data tools first, then decides which
charts to show, and a chart can never contain a number its source table didn't.
The chart spec is built by a small pure module (`assistant/charts.py`),
unit-tested independently of the LLM.

## Architecture and trade-offs
- **Explicit SSE protocol over a vendor wire format.** I defined a small typed
  event protocol (`assistant/events.py` ⇄ `frontend/lib/types.ts`:
  `text_delta` / `widget` / `tool_call` / `done` / `error`) instead of coupling
  the Django backend to the AI SDK's stream format. Trade-off: I drive the chat
  with a small custom hook (`useBudgetChat`) rather than the AI SDK `useChat`
  hook; in return the backend boundary stays clean, typed, and independent of any
  frontend library. The chat UI itself is plain Tailwind (the `WidgetRenderer` +
  Recharts widgets), with no Vercel AI SDK / AI Elements components in the render
  path.
- **Deterministic analysis as a pure module.** `analysis.py` has no Django/LLM
  imports, which is why it's trivially unit-testable. The test suite centres on
  the *finance logic* (severity edges, zero-budget guard, what-if), and also
  covers the CRUD API surface, the seed loader's idempotency, the pure chart/card
  builders, and the SSE streaming bridge — mocking the Agents SDK so the
  event→protocol translation is verified with no live model
  (`test_analysis.py` / `test_api.py` / `test_seed.py` / `test_charts.py` /
  `test_cards.py` / `test_streaming.py` / `test_chat_stream.py`).
- **Severity policy is absolute-euros-first** (reproduces the brief's example
  table; a CFO cares first about money at risk), with a relative-% escalator so a
  small line that is massively over isn't hidden. Documented in `analysis.py`.
- **ASGI + uvicorn** so the async agent stream maps cleanly to SSE.
- **SQLite, no auth.** A time-boxed single-reviewer slice; both are out of scope
  per the brief. Swapping to Postgres is a settings change.

## Assumptions and known limitations
- One reviewer, no authentication or multi-tenancy (out of scope).
- Chat history is persisted per-budget in the browser (localStorage), so it
  survives reloads and budget switches — but it is client-local only: not shared
  across devices/browsers and not a server-side source of truth.
- The agent currently handles the documented question types well; very free-form
  questions fall back to a brief "not about this data" reply rather than a widget.
- Numbers are computed in floating point with rounding at the boundary; a real
  product would use Decimal end-to-end.

## What I'd improve with more time
- Persist chat to the database (server-side), instead of today's client-local
  localStorage — so history is durable and shared across devices/browsers.
- Give the agent more control over the rendered charts and cards, and reduce the
  redundancy between its narration and the displayed data. Today every data tool
  auto-renders a fixed table and the `RENDERS:` docstrings nudge the model to
  interpret rather than reprint; a tighter, agent-shaped layout would let it pick
  which columns/figures to surface and completely skip restating them in prose.
- Decimal money type throughout; property-based tests on the analysis module.
- Giving the agent the power to write back data to the database (e.g., to update
  the scenario).
- Cross-turn chart memory: `show_chart` reads datasets cached within a single run,
  so "show that as a pie chart" in a *new* message re-runs the data tool first;
  persisting datasets across turns would remove that extra call.
- A proper eval harness: a fixed set of question→expected-tool/expected-widget
  cases to guard against regressions in agent tool-selection.
- Improve frontend form handling with required fields and maybe use a library 
- for the AI components to improve consistency and save time.
