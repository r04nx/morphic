import type {
  ActionExecution,
  AgentRun,
  Incident,
  Monitor,
  MonitorLogEntry,
  RCA,
  SettingsStatus,
  TraceEvent,
  IntegrationSettings,
} from "@/types/morphic";
import {
  mockActions,
  mockIncidents,
  mockMonitors,
  mockRcaByIncident,
  mockSettingsStatus,
  mockTraceEvents,
  generateMonitorMetrics,
  mockIntegrations,
} from "./mock";

const BASE_URL =
  (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_BASE_URL) || "";

const TIMEOUT_MS = 15_000;

async function tryFetch<T>(path: string, init?: RequestInit): Promise<T | null> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...init,
      signal: ctrl.signal,
      headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    if (res.status === 204) return true as any;
    const text = await res.text();
    if (!text) return true as any;
    return JSON.parse(text) as T;
  } catch (err) {
    console.warn(`[morphic.api] ${path} unavailable, falling back to mock:`, err);
    return null;
  } finally {
    clearTimeout(t);
  }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export const api = {
  async health(): Promise<{ ok: boolean; version?: string; mock: boolean }> {
    const real = await tryFetch<{ ok: boolean; version?: string }>("/api/health");
    if (real) return { ...real, mock: false };
    return { ok: true, version: "0.1.0-mock", mock: true };
  },

  async listIncidents(limit = 50): Promise<Incident[]> {
    const real = await tryFetch<{ incidents: Incident[]; limit: number; offset: number; total: number }>(`/api/incidents?limit=${limit}`);
    if (real && real.incidents) return real.incidents;
    await sleep(120);
    return mockIncidents.slice(0, limit);
  },

  async getIncident(id: string): Promise<{
    incident: Incident;
    rca?: RCA;
    actions: ActionExecution[];
  }> {
    const real = await tryFetch<{ incident: Incident; rca?: RCA; actions: ActionExecution[] }>(
      `/api/incidents/${id}`,
    );
    if (real) return real;
    await sleep(140);
    const incident = mockIncidents.find((i) => i.id === id);
    if (!incident) throw new Error("Incident not found");
    return {
      incident,
      rca: mockRcaByIncident[id],
      actions: mockActions.filter((a) => a.incident_id === id),
    };
  },

  async listTraceEvents(traceId: string, limit = 500): Promise<TraceEvent[]> {
    const real = await tryFetch<TraceEvent[]>(`/api/traces/${traceId}/events?limit=${limit}`);
    if (real) return real;
    await sleep(160);
    return mockTraceEvents(traceId);
  },

  async listActions(limit = 200): Promise<ActionExecution[]> {
    const real = await tryFetch<ActionExecution[]>(`/api/actions?limit=${limit}`);
    if (real) return real;
    await sleep(120);
    return mockActions.slice(0, limit);
  },

  async triggerEmail(incidentId: string): Promise<ActionExecution> {
    const real = await tryFetch<ActionExecution>(`/api/incidents/${incidentId}/actions/email`, {
      method: "POST",
    });
    if (real) return real;
    await sleep(800);
    return {
      id: "act_" + Math.random().toString(36).slice(2, 8),
      incident_id: incidentId,
      action_type: "EMAIL",
      status: "SUCCEEDED",
      started_at: new Date().toISOString(),
      finished_at: new Date().toISOString(),
      summary: "Notified on-call (mock)",
      output: "Delivered to oncall@morphic.dev",
    };
  },

  async triggerPR(incidentId: string): Promise<ActionExecution> {
    const real = await tryFetch<ActionExecution>(`/api/incidents/${incidentId}/actions/github-pr`, {
      method: "POST",
    });
    if (real) return real;
    await sleep(1200);
    return {
      id: "act_" + Math.random().toString(36).slice(2, 8),
      incident_id: incidentId,
      action_type: "GITHUB_PR",
      status: "SUCCEEDED",
      started_at: new Date().toISOString(),
      finished_at: new Date().toISOString(),
      summary: "Opened PR with Morphic's suggested fix (mock)",
      output: "PR #999 opened",
      link: "https://github.com/morphic/example/pull/999",
    };
  },

  async settingsStatus(): Promise<SettingsStatus> {
    const real = await tryFetch<SettingsStatus>("/api/settings/status");
    if (real) return real;
    await sleep(80);
    return mockSettingsStatus;
  },

  async listMonitors(): Promise<Monitor[]> {
    const real = (await tryFetch<Monitor[]>("/api/monitors")) || [];
    // Combine real monitors with the first two mock ones as requested
    return [...real, ...mockMonitors.slice(0, 2)];
  },

  async getMonitor(id: string): Promise<{ monitor: Monitor; metrics: any[] }> {
    const real = await tryFetch<{ monitor: Monitor; metrics: any[] }>(`/api/monitors/${id}`);
    if (real) return real;
    
    // Fallback to mock data if not in backend
    const monitor = mockMonitors.find((m) => m.id === id);
    if (!monitor) throw new Error("Monitor not found");
    return {
      monitor,
      metrics: generateMonitorMetrics(id),
    };
  },

  async createMonitor(data: Partial<Monitor>): Promise<Monitor> {
    const real = await tryFetch<Monitor>("/api/monitors", {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (real) return real;
    await sleep(400);
    const newMonitor: Monitor = {
      id: "mon_" + Math.random().toString(36).slice(2, 8),
      name: data.name || "New Monitor",
      url: data.url || "",
      auth_type: data.auth_type || "NONE",
      status: "UP",
      uptime_pct: 100,
      latency_ms: 0,
      last_check: new Date().toISOString(),
      notifications: data.notifications || [],
      workflows: data.workflows || [],
      history: [],
    };
    mockMonitors.unshift(newMonitor);
    return newMonitor;
  },

  async updateMonitor(id: string, data: Partial<Monitor>): Promise<Monitor> {
    const real = await tryFetch<Monitor>(`/api/monitors/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
    if (real) return real;
    await sleep(300);
    const idx = mockMonitors.findIndex((m) => m.id === id);
    if (idx === -1) throw new Error("Monitor not found");
    mockMonitors[idx] = { ...mockMonitors[idx], ...data };
    return mockMonitors[idx];
  },

  async deleteMonitor(id: string): Promise<void> {
    await tryFetch<void>(`/api/monitors/${id}`, { method: "DELETE" });
    const idx = mockMonitors.findIndex((m) => m.id === id);
    if (idx !== -1) mockMonitors.splice(idx, 1);
  },

  async listAgentRuns(monitorId: string, limit = 10): Promise<AgentRun[]> {
    const real = await tryFetch<AgentRun[]>(`/api/monitors/${monitorId}/agent-runs?limit=${limit}`);
    return real ?? [];
  },

  async getAgentRun(runId: string): Promise<AgentRun | null> {
    return await tryFetch<AgentRun>(`/api/agent-runs/${runId}`);
  },

  async getAgentRuns(monitorId?: string): Promise<AgentRun[]> {
    const query = monitorId ? `?monitor_id=${monitorId}` : '';
    const real = await tryFetch<AgentRun[]>(`/api/agent-runs${query}`);
    return real ?? [];
  },

  async triggerAgentRun(monitorId: string, opts?: any): Promise<{ run_id: string; trace_id: string; status: string }> {
    const real = await tryFetch<{ run_id: string; trace_id: string; status: string }>(
      `/api/monitors/${monitorId}/trigger-agent`,
      { method: "POST", body: JSON.stringify(opts ?? {}) }
    );
    if (real) return real;
    return { run_id: "mock-run", trace_id: "mock-trace", status: "QUEUED" };
  },

  async triggerAgent(
    monitorId: string,
    opts?: { trace_id?: string; score?: number; signals?: any[] }
  ): Promise<{ run_id: string; trace_id: string; status: string }> {
    const real = await tryFetch<{ run_id: string; trace_id: string; status: string }>(
      `/api/monitors/${monitorId}/trigger-agent`,
      { method: "POST", body: JSON.stringify(opts ?? {}) }
    );
    if (real) return real;
    return { run_id: "mock-run", trace_id: "mock-trace", status: "QUEUED" };
  },

  async testNotification(type: string, config: any): Promise<{ success: boolean; message: string }> {
    const real = await tryFetch<{ success: boolean; message: string }>(
      "/api/notifications/test",
      { method: "POST", body: JSON.stringify({ type, config }) }
    );
    if (real) return real;
    return { success: true, message: "Test notification sent (mock)" };
  },

  async sendNotification(monitorId: string, status: string, message?: string): Promise<{ success: boolean; results: Record<string, boolean> }> {
    const real = await tryFetch<{ success: boolean; results: Record<string, boolean> }>(
      "/api/notifications/send",
      { method: "POST", body: JSON.stringify({ monitor_id: monitorId, status, message }) }
    );
    if (real) return real;
    return { success: true, results: {} };
  },

  
  async getMonitorLogs(monitorId: string, limit = 100): Promise<MonitorLogEntry[]> {
    const real = await tryFetch<MonitorLogEntry[]>(
      `/api/monitors/${monitorId}/logs?limit=${limit}`
    );
    return real ?? [];
  },

  async getMonitorMetrics(monitorId: string, hours = 24): Promise<any[]> {
    const real = await tryFetch<any[]>(
      `/api/monitors/${monitorId}/metrics?hours=${hours}`
    );
    return real ?? [];
  },

  async testMonitorConnection(
    data: {
      url: string;
      type: "health" | "logs";
      auth_type: string;
      bearer_token?: string;
      username?: string;
      password?: string;
    }
  ): Promise<{ success: boolean; status?: number; tail?: any; message?: string }> {
    const real = await tryFetch<{
      success: boolean;
      status?: number;
      tail?: any;
      message?: string;
    }>(`/api/monitors/test`, {
      method: "POST",
      body: JSON.stringify(data),
    });
    if (real) return real;
    await sleep(800);
    return { success: false, status: 0 };
  },

  async getIntegrations(): Promise<IntegrationSettings> {
    const real = await tryFetch<IntegrationSettings>("/api/settings/integrations");
    if (real) return real;
    await sleep(150);
    return mockIntegrations;
  },

  async updateIntegrations(data: Partial<IntegrationSettings>): Promise<IntegrationSettings> {
    const real = await tryFetch<IntegrationSettings>("/api/settings/integrations", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
    if (real) return real;
    await sleep(300);
    // Deep merge mock integrations
    Object.assign(mockIntegrations, { ...mockIntegrations, ...data });
    return mockIntegrations;
  },

  async testIntegration(type: string, config: any): Promise<{ success: boolean; message: string }> {
    const real = await tryFetch<{ success: boolean; message: string }>(
      `/api/settings/integrations/test/${type}`,
      {
        method: "POST",
        body: JSON.stringify(config),
      },
    );
    if (real) return real;
    await sleep(1200);
    return { success: true, message: `${type} connection verified!` };
  },
};

export const isMockMode = false;
