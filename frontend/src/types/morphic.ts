export type BlastRadius = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type IncidentStatus =
  | "NEW"
  | "TRIAGED"
  | "RCA_PENDING"
  | "RCA_READY"
  | "ACTIONS_RUNNING"
  | "RESOLVED"
  | "SUPPRESSED";

export type Incident = {
  id: string;
  timestamp: string;
  trace_id: string;
  service?: string;
  endpoint?: string;
  status: IncidentStatus;
  classification?: string;
  blast_radius?: BlastRadius;
  confidence_score?: number;
  summary?: string;
  impact?: string;
  root_cause?: string;
  tags?: string[];
  created_at?: string;
  updated_at?: string;
};

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
    patch: string;
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
  output?: string;
  link?: string;
};

export type SettingsStatus = {
  anthropic_api_key: boolean;
  anthropic_model?: string;
  github_token: boolean;
  email_provider: boolean;
};

export type MonitorStatus = "UP" | "DOWN" | "DEGRADED";

export type MonitorNotificationType = "NTFY" | "EMAIL" | "TELEGRAM" | "SLACK";

export type MonitorNotification = {
  type: MonitorNotificationType;
  destination: string;
  enabled: boolean;
};

export type MonitorWorkflow = {
  id: string;
  name: string;
  url: string;
  enabled: boolean;
};

export type Monitor = {
  id: string;
  name: string;
  url: string;
  auth_type: "NONE" | "BEARER" | "BASIC";
  auth_config?: string;
  status: MonitorStatus;
  uptime_pct: number;
  latency_ms: number;
  last_check: string;
  notifications: MonitorNotification[];
  workflows: MonitorWorkflow[];
  history: { status: MonitorStatus; timestamp: string }[];
  logs_url?: string;
  // GitHub self-healing integration
  github_owner?: string;       // e.g. "owner" for github.com/owner/repo
  github_repo?: string;        // e.g. "owner/repo" or full HTTPS URL
  github_token?: string;       // personal access token
  github_branch?: string;      // target branch, default "main"
  log_tail_enabled?: boolean;
  enabled?: boolean;          // Whether the monitor is enabled for checking
  agent_run_status?: "IDLE" | "TRIGGERED" | "PR_CREATED" | "ANALYZED" | "FAILED";
  last_anomaly_at?: string;
};

export type AgentRunStatus =
  | "QUEUED"
  | "RUNNING"
  | "ANALYZING"
  | "PR_CREATED"
  | "FAILED"
  | "COMPLETED";

export type AgentRun = {
  id: string;
  monitor_id: string;
  trace_id: string;
  status: AgentRunStatus;
  triggered_at: string;
  completed_at?: string;
  github_repo?: string;
  github_pr_url?: string;
  github_pr_number?: number;
  claude_output?: string;
  anomalies?: {
    score: number;
    error_rate: number;
    error_count: number;
    signals: { timestamp: string; level: string; message: string; service: string }[];
  };
  rca_summary?: string;
  error_message?: string;
};

export type MonitorLogEntry = {
  id: string;
  log_level: string;
  message: string;
  fetched_at: string;
  anomaly_score?: number;
  is_anomaly?: boolean;
};

export type IntegrationSettings = {
  vcs: {
    github_token?: string;
    gitlab_token?: string;
    gitlab_url?: string;
  };
  ai: {
    anthropic_api_key?: string;
    anthropic_model?: string;
  };
  infrastructure: {
    n8n_url?: string;
    n8n_api_key?: string;
    mcp_servers: { name: string; url: string; enabled: boolean }[];
  };
  databases: {
    postgres_url?: string;
    neo4j_url?: string;
    neo4j_user?: string;
    neo4j_password?: string;
  };
  notifications: {
    smtp_host?: string;
    smtp_port?: number;
    smtp_user?: string;
    smtp_password?: string;
    sender_name?: string;
    sender_email?: string;
    ntfy_topic?: string;
    slack_webhook?: string;
    telegram_bot_token?: string;
    telegram_chat_id?: string;
  };
};
