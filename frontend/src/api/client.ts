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

// Always use relative URLs so requests go through the Vite dev proxy (/api → localhost:5000).
// Do NOT set VITE_API_BASE_URL — that causes absolute URLs which bypass the proxy and
// can fail silently (CORS, wrong IP, etc.).
const BASE_URL = "";

const TIMEOUT_MS = 15_000;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function tryFetch<T>(path: string, init?: RequestInit): Promise<T> {
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
    // Use console.error so failures appear as red errors in DevTools, not hidden warnings.
    console.error(`[morphic.api] ${path} failed — falling back to mock:`, err);
    return null as any;
  } finally {
    clearTimeout(t);
  }
}

export const api = {
  async health(): Promise<{ ok: boolean; version?: string; mock: boolean }> {
    const real = await tryFetch<{ ok: boolean; version?: string }>("/api/health");
    return { ...real, mock: false };
  },

  async listIncidents(limit = 50): Promise<Incident[]> {
    const real = await tryFetch<{ incidents: Incident[]; total?: number } | Incident[]>(
      `/api/incidents?limit=${limit}`,
    );
    if (real) {
      if (Array.isArray(real)) return real;
      if (real.incidents) return real.incidents;
    }
    // Fallback to mock if API fails or returns unexpected shape
    const { mockIncidents } = await import("./mock");
    return mockIncidents.slice(0, limit);
  },

  async getIncident(id: string): Promise<{
    incident: Incident;
    rca?: RCA;
    actions: ActionExecution[];
  }> {
    const res = await tryFetch<{ incident: Incident; rca?: RCA; actions: ActionExecution[] }>(
      `/api/incidents/${id}`,
    );
    if (res) return res;
    
    // Fallback to mock
    const { mockIncidents, mockRCA, mockActions } = await import("./mock");
    const inc = mockIncidents.find(i => i.id === id || i.trace_id === id) || mockIncidents[0];
    return {
      incident: inc,
      rca: mockRCA,
      actions: mockActions.slice(0, 3)
    };
  },

  async listTraceEvents(traceId: string, limit = 500): Promise<TraceEvent[]> {
    return await tryFetch<TraceEvent[]>(`/api/traces/${traceId}/events?limit=${limit}`) || [];
  },

  async listActions(limit = 200): Promise<ActionExecution[]> {
    return await tryFetch<ActionExecution[]>(`/api/actions?limit=${limit}`) || [];
  },

  async triggerEmail(incidentId: string): Promise<ActionExecution> {
    return await tryFetch<ActionExecution>(`/api/incidents/${incidentId}/actions/email`, {
      method: "POST",
    });
  },

  async triggerPR(incidentId: string): Promise<ActionExecution> {
    return await tryFetch<ActionExecution>(`/api/incidents/${incidentId}/actions/github-pr`, {
      method: "POST",
    });
  },

  async settingsStatus(): Promise<SettingsStatus> {
    return await tryFetch<SettingsStatus>("/api/settings/status");
  },

  async listMonitors(): Promise<Monitor[]> {
    return await tryFetch<Monitor[]>("/api/monitors") || [];
  },

  async getMonitor(id: string): Promise<{ monitor: Monitor; metrics: any[] }> {
    return await tryFetch<{ monitor: Monitor; metrics: any[] }>(`/api/monitors/${id}`);
  },

  async createMonitor(data: Partial<Monitor>): Promise<Monitor> {
    return await tryFetch<Monitor>("/api/monitors", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateMonitor(id: string, data: Partial<Monitor>): Promise<Monitor> {
    return await tryFetch<Monitor>(`/api/monitors/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async deleteMonitor(id: string): Promise<void> {
    await tryFetch<void>(`/api/monitors/${id}`, { method: "DELETE" });
  },

  async enableMonitor(id: string): Promise<Monitor> {
    return await tryFetch<Monitor>(`/api/monitors/${id}/enable`, {
      method: "POST",
    });
  },

  async disableMonitor(id: string): Promise<Monitor> {
    return await tryFetch<Monitor>(`/api/monitors/${id}/disable`, {
      method: "POST",
    });
  },

  async listAgentRuns(monitorId: string, limit = 10): Promise<AgentRun[]> {
    return await tryFetch<AgentRun[]>(`/api/monitors/${monitorId}/agent-runs?limit=${limit}`) || [];
  },

  async getAgentRun(runId: string): Promise<AgentRun | null> {
    return await tryFetch<AgentRun>(`/api/agent-runs/${runId}`);
  },

  async getAgentRuns(monitorId?: string): Promise<AgentRun[]> {
    const query = monitorId ? `?monitor_id=${monitorId}` : '';
    return await tryFetch<AgentRun[]>(`/api/agent-runs${query}`) || [];
  },

  async getAgentRunsByIncident(incidentId: string): Promise<AgentRun[]> {
    return await tryFetch<AgentRun[]>(`/api/agent-runs/incident/${incidentId}`) || [];
  },

  async triggerAgentRun(monitorId: string, opts?: any): Promise<{ run_id: string; trace_id: string; status: string }> {
    return await tryFetch<{ run_id: string; trace_id: string; status: string }>(
      `/api/monitors/${monitorId}/trigger-agent`,
      { method: "POST", body: JSON.stringify(opts ?? {}) }
    );
  },

  async triggerAgent(
    monitorId: string,
    opts?: { trace_id?: string; score?: number; signals?: any[] }
  ): Promise<{ run_id: string; trace_id: string; status: string }> {
    return await tryFetch<{ run_id: string; trace_id: string; status: string }>(
      `/api/monitors/${monitorId}/trigger-agent`,
      { method: "POST", body: JSON.stringify(opts ?? {}) }
    );
  },

  async testNotification(type: string, config: any): Promise<{ success: boolean; message: string }> {
    return await tryFetch<{ success: boolean; message: string }>(
      "/api/notifications/test",
      { method: "POST", body: JSON.stringify({ type, config }) }
    );
  },

  async sendNotification(monitorId: string, status: string, message?: string): Promise<{ success: boolean; results: Record<string, boolean> }> {
    return await tryFetch<{ success: boolean; results: Record<string, boolean> }>(
      "/api/notifications/send",
      { method: "POST", body: JSON.stringify({ monitor_id: monitorId, status, message }) }
    );
  },

  async getMonitorLogs(monitorId: string, limit = 100): Promise<MonitorLogEntry[]> {
    return await tryFetch<MonitorLogEntry[]>(`/api/monitors/${monitorId}/logs?limit=${limit}`) || [];
  },

  async getMonitorMetrics(monitorId: string, hours = 24): Promise<any[]> {
    return await tryFetch<any[]>(`/api/monitors/${monitorId}/metrics?hours=${hours}`) || [];
  },

  async getMonitorAnalysis(monitorId: string): Promise<any> {
    return await tryFetch<any>(`/api/monitors/${monitorId}/analysis`);
  },

  async getMonitorAnalysisHistory(monitorId: string, limit = 20): Promise<any[]> {
    return await tryFetch<any[]>(`/api/monitors/${monitorId}/analysis/history?limit=${limit}`) || [];
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
    return await tryFetch<{
      success: boolean;
      status?: number;
      tail?: any;
      message?: string;
    }>(`/api/monitors/test`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async getIntegrations(): Promise<IntegrationSettings> {
    return await tryFetch<IntegrationSettings>("/api/settings/integrations");
  },

  async updateIntegrations(data: Partial<IntegrationSettings>): Promise<IntegrationSettings> {
    return await tryFetch<IntegrationSettings>("/api/settings/integrations", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async sendTelegramVerificationCode(username: string): Promise<{ success: boolean; bot_username?: string; verification_code?: string; message?: string; error?: string }> {
    return await tryFetch<{ success: boolean; bot_username?: string; verification_code?: string; message?: string; error?: string }>(
      "/api/notifications/telegram/send-code",
      {
        method: "POST",
        body: JSON.stringify({ username }),
      },
    );
  },

  async verifyTelegramChatId(username: string, code: string): Promise<{ success: boolean; message?: string; error?: string; chat_id?: string }> {
    return await tryFetch<{ success: boolean; message?: string; error?: string; chat_id?: string }>(
      "/api/notifications/telegram/verify",
      {
        method: "POST",
        body: JSON.stringify({ username, code }),
      },
    );
  },

  async testIntegration(type: string, config: any): Promise<{ success: boolean; message: string }> {
    return await tryFetch<{ success: boolean; message: string }>(
      `/api/settings/integrations/test/${type}`,
      {
        method: "POST",
        body: JSON.stringify(config),
      },
    );
  },

  async getGitHubRepos(token: string): Promise<{ repos: any[] }> {
    return await tryFetch<{ repos: any[] }>("/api/github/repos", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
  },

  async getGitHubBranches(token: string, repo: string): Promise<{ branches: any[] }> {
    return await tryFetch<{ branches: any[] }>("/api/github/branches", {
      method: "POST",
      body: JSON.stringify({ token, repo }),
    });
  },
};

export const isMockMode = false;
