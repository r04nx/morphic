# Morphic Frontend (React Dashboard) — Complete UI Generation Prompt

Copy/paste the prompt below into your UI/code-generation tool to generate the entire frontend for Morphic.

---

## UI Generation Prompt

You are building the **Morphic Dashboard**, a production-quality **React** frontend for an AI-driven self-healing incident assistant.

### 0) Product Goal (Non-Negotiable)
Build a dashboard that allows an engineer (and a non-engineer stakeholder) to:
- see a **live incident feed**
- drill into a **single trace timeline** (`trace_id`) and understand what happened
- read **RCA cards** that explain root cause + impact in plain English
- see which **automated actions** ran (email, PR creation, etc.), their status, and outputs

The UI must make it obvious:
- what is broken
- how severe it is
- what Morphic believes the root cause is
- what action has been taken (or is pending)

### 1) Tech Stack Requirements
- Framework: **React**
- Language: **TypeScript**
- Styling: **Tailwind CSS**
- Component primitives: **shadcn/ui**
- Icons: **lucide-react**
- Routing: **react-router**
- Data fetching: **@tanstack/react-query**
- State management: React Query + minimal local state; no Redux
- Charts (optional but recommended): **recharts**

### 2) UX Requirements (Must Implement)
- Responsive layout (desktop-first, works on laptop and tablet)
- Clean “operations console” aesthetic
- Clear hierarchy and scannability:
  - severity badges
  - status chips
  - readable typography
  - consistent spacing
- Fast interactions:
  - skeleton loaders
  - optimistic UI where appropriate (e.g., manual action trigger)
  - cached queries with background refresh
- Error handling:
  - global error boundary
  - toast notifications on failed network calls
  - empty states with clear call-to-action

### 3) Information Architecture / Routes
Implement these routes:

1. `/` → redirect to `/incidents`
2. `/incidents` (Live Incident Feed)
3. `/incidents/:incidentId` (Incident Detail)
4. `/traces/:traceId` (Trace Timeline View)
5. `/actions` (Action Execution History)
6. `/settings` (Configuration status, environment readiness)

### 4) Core Data Model (Frontend Types)
Define TypeScript types that match the backend payloads.

#### 4.1 Incident
An incident is the unit shown in the feed.

```ts
export type BlastRadius = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type IncidentStatus = "NEW" | "TRIAGED" | "RCA_PENDING" | "RCA_READY" | "ACTIONS_RUNNING" | "RESOLVED" | "SUPPRESSED";

export type Incident = {
  id: string;
  timestamp: string; // ISO
  trace_id: string;
  service?: string;
  endpoint?: string;
  status: IncidentStatus;
  classification?: string;
  blast_radius?: BlastRadius;
  confidence_score?: number;
  summary: string; // short human-readable summary
  tags?: string[];
};
```

#### 4.2 RCA JSON (Strict Contract)
The UI must render this object as the canonical RCA.

```ts
export type RCA = {
  classification: string;
  root_cause: string;
  blast_radius: BlastRadius;
  impact: string;
  trace_id: string;
  timestamp: string;
  log_signals: {
    service: string;
    endpoint: string;
    exception_class: string;
    error_message: string;
  };
  suggested_fix: {
    language: "java";
    target_class: string;
    patch: string; // unified diff or patch-like text
    rationale: string;
    tests: string[];
  };
  github_pr: {
    title: string;
    body: string;
    labels: string[];
  };
  confidence_score: number;
};
```

#### 4.3 Trace Event
A trace has a timeline of log events.

```ts
export type TraceEvent = {
  id: string;
  trace_id: string;
  timestamp: string;
  level: "DEBUG" | "INFO" | "WARN" | "ERROR";
  message: string;
  logger?: string;
  thread?: string;
  span_id?: string;
  fields?: Record<string, unknown>;
  async_orphan?: boolean;
};
```

#### 4.4 Action Execution
Actions are automated workflows executed by Morphic.

```ts
export type ActionType = "EMAIL" | "GITHUB_PR" | "RESTART" | "TICKET";
export type ActionStatus = "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED" | "SKIPPED";

export type ActionExecution = {
  id: string;
  incident_id?: string;
  trace_id?: string;
  action_type: ActionType;
  status: ActionStatus;
  started_at?: string;
  finished_at?: string;
  summary?: string;
  output?: string; // free-form logs or JSON
  link?: string; // e.g., PR URL
};
```

### 5) Backend API Integration (Assume These Endpoints)
Implement a typed API client layer with fetch wrappers.

- Base URL from `VITE_API_BASE_URL`.
- All requests should time out (e.g., 15s) and surface failures via toast.

Assume endpoints:
- `GET /api/incidents?limit=50` → `Incident[]`
- `GET /api/incidents/:incidentId` → `{ incident: Incident; rca?: RCA; actions: ActionExecution[] }`
- `GET /api/traces/:traceId/events?limit=500` → `TraceEvent[]`
- `GET /api/actions?limit=200` → `ActionExecution[]`
- `POST /api/incidents/:incidentId/actions/email` → trigger email
- `POST /api/incidents/:incidentId/actions/github-pr` → trigger PR creation
- `GET /api/health` → `{ ok: boolean; version?: string }`
- `GET /api/settings/status` → configuration readiness (API key present, model configured, GitHub token ready, etc.)

If an endpoint is missing at runtime, the UI must show a helpful error state and keep the rest of the app usable.

### 6) Polling / Live Updates
- Incidents feed must auto-refresh every **10 seconds**.
- Incident detail must auto-refresh every **10 seconds** while status is not RESOLVED.
- Trace timeline should refresh every **15 seconds**.

Implement this with React Query `refetchInterval`.

### 7) Layout & Global UI Components
Build a consistent shell:
- Left sidebar navigation with icons and route labels
- Top bar with:
  - app name “Morphic”
  - environment badge (e.g., DEV)
  - health indicator (green/yellow/red)
  - quick search input (search by `trace_id`)

Global components:
- `AppShell`
- `SidebarNav`
- `TopBar`
- `HealthIndicator`
- `SeverityBadge`
- `StatusChip`
- `EmptyState`
- `ErrorState`
- `SkeletonCard`

### 8) Page Requirements

#### 8.1 Live Incident Feed (`/incidents`)
Page goals: scan quickly, sort by severity, drill in fast.

Must include:
- Header with filters:
  - status filter
  - blast radius filter
  - service filter (derived from data)
  - free-text search (summary, trace_id)
- Sorting:
  - default sort by newest
  - optional sort by blast radius then newest
- Incident list:
  - each row/card shows:
    - `blast_radius` badge
    - `status` chip
    - `summary`
    - `service` + `endpoint`
    - `trace_id` (copy button)
    - timestamp
    - confidence (if present)
- Quick actions per incident:
  - “View details”
  - “View trace”

#### 8.2 Incident Detail (`/incidents/:incidentId`)
Page goals: show everything needed for a decision.

Must include:
- Summary header:
  - incident title/summary
  - severity + status
  - trace_id copy
  - timestamp
- Tabs:
  1. **RCA**
  2. **Actions**
  3. **Related Logs** (preview slice)

RCA tab:
- Render the RCA object into a readable card layout:
  - classification
  - root cause (one sentence)
  - impact (human-readable)
  - confidence score (progress bar)
  - log signals
- Suggested fix section:
  - target class
  - patch in a code block with copy button
  - tests list
  - rationale
- PR suggestion:
  - title
  - labels
  - body preview

Actions tab:
- Table of action executions for this incident
- Buttons to manually trigger:
  - Send email
  - Create GitHub PR
- Manual triggers must:
  - show confirmation modal
  - disable during running
  - display result (toast + refresh)

Related Logs tab:
- Show recent `TraceEvent` snippets (or a compact list) and a link to full trace timeline.

#### 8.3 Trace Timeline (`/traces/:traceId`)
Page goals: investigate timeline, spot ASYNC-ORPHAN.

Must include:
- Timeline list grouped by time
- Controls:
  - filter by level
  - toggle “show only errors/warnings”
  - search within messages
- Each event shows:
  - time
  - level badge
  - message
  - metadata expand/collapse
  - highlight if `async_orphan: true`

Optional:
- mini “sparklines” chart of error count per minute

#### 8.4 Action History (`/actions`)
Page goals: prove automation is working.

Must include:
- Filter by action type and status
- Table:
  - action type
  - status
  - incident/trace link
  - started/finished
  - output preview
  - link (PR URL)

#### 8.5 Settings / Readiness (`/settings`)
Page goals: reduce setup friction.

Must include:
- Show backend health
- Show configuration readiness:
  - `ANTHROPIC_API_KEY` present?
  - `ANTHROPIC_MODEL` configured?
  - GitHub token configured for PR automation?
  - Email provider configured?
- Provide copy-pastable environment variable names and what they do (do not show secrets).

### 9) Visual Design & Component Details
- Use shadcn/ui cards, tables, tabs, badges, dialogs, toasts
- Severity colors:
  - LOW: slate/neutral
  - MEDIUM: amber
  - HIGH: orange
  - CRITICAL: red
- Status chip colors:
  - NEW: blue
  - RCA_PENDING: purple
  - ACTIONS_RUNNING: cyan
  - RESOLVED: green
  - FAILED: red

### 10) Performance & Reliability Requirements
- Avoid re-render storms:
  - memoize list row components
  - use virtualization for large trace event lists (e.g., react-virtual) if > 500 items
- Ensure the app remains usable if some endpoints fail.
- All date/time must be displayed in local time with clear formatting.

### 11) Developer Experience Requirements
- Generate a clean project structure:

```
src/
  api/
  components/
  pages/
  routes/
  hooks/
  types/
  utils/
  App.tsx
  main.tsx
```

- Provide a simple `README` section inside the project output that explains:
  - required env vars (`VITE_API_BASE_URL`)
  - how to run (`npm install`, `npm run dev`)

### 12) Acceptance Criteria (Checklist)
The generated frontend is acceptable only if:
- `/incidents` renders and auto-refreshes
- An incident detail page renders RCA + suggested fix cleanly
- Trace timeline shows ASYNC-ORPHAN highlighting
- Actions page shows executed actions and links to PRs
- Settings page shows readiness and health
- All pages have loading, empty, and error states
- No hardcoded secrets

---

## Output Instructions
Generate the complete React + TypeScript app source.
- Use Vite as the bundler.
- Use Tailwind and shadcn/ui.
- Provide all necessary config files.
- Keep the UI polished and consistent.
