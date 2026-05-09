import type {
  ActionExecution,
  Incident,
  Monitor,
  RCA,
  SettingsStatus,
  TraceEvent,
} from "@/types/morphic";

const SERVICES = ["payments-svc", "checkout-svc", "auth-svc", "ledger-svc", "notify-svc"];
const ENDPOINTS = [
  "/api/charge",
  "/api/refund",
  "/api/login",
  "/api/ledger/post",
  "/api/notify/send",
];

const now = Date.now();

function randomTrace() {
  return "trc_" + Math.random().toString(36).slice(2, 10) + Math.random().toString(36).slice(2, 6);
}

export const mockIncidents: Incident[] = [
  {
    id: "inc_001",
    timestamp: new Date(now - 1000 * 60 * 2).toISOString(),
    trace_id: "trc_a91f0c2b88e4",
    service: "payments-svc",
    endpoint: "/api/charge",
    status: "RCA_READY",
    classification: "NullPointerException in async retry path",
    blast_radius: "CRITICAL",
    confidence_score: 0.92,
    summary: "Charge requests failing with NPE after Stripe webhook retry",
    tags: ["payments", "async-orphan", "regression"],
  },
  {
    id: "inc_002",
    timestamp: new Date(now - 1000 * 60 * 9).toISOString(),
    trace_id: "trc_77bd5c12a4e0",
    service: "checkout-svc",
    endpoint: "/api/cart/checkout",
    status: "ACTIONS_RUNNING",
    classification: "Database connection pool exhausted",
    blast_radius: "HIGH",
    confidence_score: 0.81,
    summary: "Checkout latency p99 > 8s, HikariCP saturation detected",
    tags: ["db", "saturation"],
  },
  {
    id: "inc_003",
    timestamp: new Date(now - 1000 * 60 * 22).toISOString(),
    trace_id: "trc_31ef0099aa12",
    service: "auth-svc",
    endpoint: "/api/login",
    status: "RCA_PENDING",
    classification: "Elevated 401 rate from EU region",
    blast_radius: "MEDIUM",
    confidence_score: 0.66,
    summary: "Spike in 401 responses from eu-west-1 since 14:02 UTC",
    tags: ["auth", "regional"],
  },
  {
    id: "inc_004",
    timestamp: new Date(now - 1000 * 60 * 41).toISOString(),
    trace_id: "trc_55a3b201ffe9",
    service: "ledger-svc",
    endpoint: "/api/ledger/post",
    status: "NEW",
    classification: "Schema drift",
    blast_radius: "LOW",
    confidence_score: 0.42,
    summary: "Unknown column 'tx_idempotency_v2' on ledger writes",
    tags: ["schema", "drift"],
  },
  {
    id: "inc_005",
    timestamp: new Date(now - 1000 * 60 * 65).toISOString(),
    trace_id: "trc_bb09d7a13c40",
    service: "notify-svc",
    endpoint: "/api/notify/send",
    status: "RESOLVED",
    classification: "SMTP timeout",
    blast_radius: "MEDIUM",
    confidence_score: 0.88,
    summary: "Outbound SMTP retried 3x and recovered after provider restored",
    tags: ["smtp", "recovered"],
  },
  ...Array.from({ length: 6 }).map((_, i) => ({
    id: `inc_10${i}`,
    timestamp: new Date(now - 1000 * 60 * (90 + i * 17)).toISOString(),
    trace_id: randomTrace(),
    service: SERVICES[i % SERVICES.length],
    endpoint: ENDPOINTS[i % ENDPOINTS.length],
    status: (["TRIAGED", "RESOLVED", "RCA_READY", "NEW"] as const)[i % 4],
    classification: ["Timeout", "5xx burst", "Regression", "Cache miss storm"][i % 4],
    blast_radius: (["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const)[i % 4],
    confidence_score: 0.5 + ((i * 7) % 40) / 100,
    summary: `Auto-detected anomaly on ${SERVICES[i % SERVICES.length]}`,
    tags: ["auto"],
  })),
];

const RCA_001: RCA = {
  classification: "NullPointerException in async retry path",
  root_cause:
    "RetryableChargeProcessor schedules a retry on a CompletableFuture without propagating the SecurityContext, so when the retry callback dereferences `principal.getTenantId()` the principal is null.",
  blast_radius: "CRITICAL",
  impact: "All Stripe webhook-triggered retries fail. ~38% of charges in last 5 minutes affected.",
  trace_id: "trc_a91f0c2b88e4",
  timestamp: new Date(now - 1000 * 60 * 2).toISOString(),
  log_signals: {
    service: "payments-svc",
    endpoint: "/api/charge",
    exception_class: "java.lang.NullPointerException",
    error_message: 'Cannot invoke "TenantPrincipal.getTenantId()" because "principal" is null',
  },
  suggested_fix: {
    language: "java",
    target_class: "com.morphic.payments.RetryableChargeProcessor",
    patch: `--- a/src/main/java/com/morphic/payments/RetryableChargeProcessor.java
+++ b/src/main/java/com/morphic/payments/RetryableChargeProcessor.java
@@ -42,8 +42,12 @@ public class RetryableChargeProcessor {
   public CompletableFuture<ChargeResult> retry(ChargeRequest req) {
-    return CompletableFuture.supplyAsync(() -> {
-      TenantPrincipal principal = SecurityContextHolder.getPrincipal();
-      return doCharge(principal.getTenantId(), req);
-    }, retryExecutor);
+    final TenantPrincipal captured = SecurityContextHolder.getPrincipal();
+    return CompletableFuture.supplyAsync(() -> {
+      if (captured == null) {
+        throw new IllegalStateException("Missing principal at retry dispatch");
+      }
+      return doCharge(captured.getTenantId(), req);
+    }, retryExecutor);
   }
 }`,
    rationale:
      "Capture the principal on the calling thread before dispatching to the executor so the async task does not depend on thread-local state.",
    tests: [
      "RetryableChargeProcessorTest#retry_capturesPrincipalAtDispatch",
      "RetryableChargeProcessorTest#retry_failsFastWhenNoPrincipal",
    ],
  },
  github_pr: {
    title: "fix(payments): capture principal before async retry to prevent NPE",
    body: "Morphic detected that retried charges fail with NPE because SecurityContext is not propagated to the executor. This patch captures the principal on the calling thread.\n\nTrace: trc_a91f0c2b88e4",
    labels: ["bug", "auto-rca", "payments", "critical"],
  },
  confidence_score: 0.92,
};

export const mockRcaByIncident: Record<string, RCA | undefined> = {
  inc_001: RCA_001,
  inc_002: {
    ...RCA_001,
    classification: "DB pool exhaustion",
    root_cause: "HikariCP maxPoolSize=10 too low for current QPS.",
    blast_radius: "HIGH",
    confidence_score: 0.81,
    suggested_fix: {
      ...RCA_001.suggested_fix,
      target_class: "com.morphic.checkout.DataSourceConfig",
      rationale: "Raise pool size and add leak detection.",
      patch:
        "--- a/DataSourceConfig.java\n+++ b/DataSourceConfig.java\n-  config.setMaximumPoolSize(10);\n+  config.setMaximumPoolSize(40);\n+  config.setLeakDetectionThreshold(5000);",
      tests: ["DataSourceConfigTest#poolSized"],
    },
    github_pr: {
      ...RCA_001.github_pr,
      title: "fix(checkout): raise HikariCP pool size & enable leak detection",
    },
  },
};

export const mockActions: ActionExecution[] = [
  {
    id: "act_001",
    incident_id: "inc_001",
    trace_id: "trc_a91f0c2b88e4",
    action_type: "GITHUB_PR",
    status: "SUCCEEDED",
    started_at: new Date(now - 1000 * 60).toISOString(),
    finished_at: new Date(now - 1000 * 30).toISOString(),
    summary: "Opened PR #482 with Morphic's suggested fix",
    output: "PR #482 opened, 2 reviewers auto-assigned",
    link: "https://github.com/morphic/payments-svc/pull/482",
  },
  {
    id: "act_002",
    incident_id: "inc_001",
    action_type: "EMAIL",
    status: "SUCCEEDED",
    started_at: new Date(now - 1000 * 90).toISOString(),
    finished_at: new Date(now - 1000 * 89).toISOString(),
    summary: "Notified payments on-call",
    output: "Sent to oncall-payments@morphic.dev",
  },
  {
    id: "act_003",
    incident_id: "inc_002",
    action_type: "RESTART",
    status: "RUNNING",
    started_at: new Date(now - 1000 * 20).toISOString(),
    summary: "Rolling restart of checkout-svc to clear leaked connections",
  },
  {
    id: "act_004",
    incident_id: "inc_005",
    action_type: "TICKET",
    status: "SKIPPED",
    summary: "Ticket suppressed — incident auto-resolved before threshold",
  },
  {
    id: "act_005",
    incident_id: "inc_003",
    action_type: "EMAIL",
    status: "FAILED",
    started_at: new Date(now - 1000 * 60 * 18).toISOString(),
    finished_at: new Date(now - 1000 * 60 * 18 + 800).toISOString(),
    summary: "SMTP relay refused connection",
    output: "smtp.morphic.dev:587 — connection refused",
  },
];

export function mockTraceEvents(traceId: string): TraceEvent[] {
  const base = Date.now() - 1000 * 60 * 3;
  const evts: TraceEvent[] = [
    {
      id: "e1",
      trace_id: traceId,
      timestamp: new Date(base).toISOString(),
      level: "INFO",
      message: "POST /api/charge received",
      logger: "http.access",
      thread: "http-nio-8080-exec-12",
      span_id: "sp_a1",
    },
    {
      id: "e2",
      trace_id: traceId,
      timestamp: new Date(base + 120).toISOString(),
      level: "DEBUG",
      message: "Resolved tenant=acme via JWT",
      logger: "auth.SecurityFilter",
      thread: "http-nio-8080-exec-12",
      span_id: "sp_a2",
    },
    {
      id: "e3",
      trace_id: traceId,
      timestamp: new Date(base + 340).toISOString(),
      level: "INFO",
      message: "Calling Stripe charges.create",
      logger: "payments.Gateway",
      thread: "http-nio-8080-exec-12",
      span_id: "sp_a3",
    },
    {
      id: "e4",
      trace_id: traceId,
      timestamp: new Date(base + 1800).toISOString(),
      level: "WARN",
      message: "Stripe webhook retry scheduled in 200ms",
      logger: "payments.RetryableChargeProcessor",
      thread: "http-nio-8080-exec-12",
      span_id: "sp_a4",
    },
    {
      id: "e5",
      trace_id: traceId,
      timestamp: new Date(base + 2050).toISOString(),
      level: "ERROR",
      message:
        'NullPointerException: Cannot invoke "TenantPrincipal.getTenantId()" because "principal" is null',
      logger: "payments.RetryableChargeProcessor",
      thread: "retry-exec-3",
      span_id: "sp_a5",
      async_orphan: true,
      fields: {
        exception: "java.lang.NullPointerException",
        at: "RetryableChargeProcessor.lambda$retry$0(RetryableChargeProcessor.java:45)",
      },
    },
    {
      id: "e6",
      trace_id: traceId,
      timestamp: new Date(base + 2090).toISOString(),
      level: "ERROR",
      message: "Charge retry failed, marking transaction as PENDING_REVIEW",
      logger: "payments.ChargeService",
      thread: "retry-exec-3",
      span_id: "sp_a6",
      async_orphan: true,
    },
    {
      id: "e7",
      trace_id: traceId,
      timestamp: new Date(base + 2400).toISOString(),
      level: "INFO",
      message: "Response 502 sent to client",
      logger: "http.access",
      thread: "http-nio-8080-exec-12",
      span_id: "sp_a7",
    },
  ];
  // Add some noise
  for (let i = 0; i < 12; i++) {
    evts.push({
      id: `n${i}`,
      trace_id: traceId,
      timestamp: new Date(base + 200 + i * 90).toISOString(),
      level: i % 5 === 0 ? "WARN" : "DEBUG",
      message: `metrics.report counter=charge.attempt n=${i + 1}`,
      logger: "metrics.Reporter",
      thread: "metrics-1",
    });
  }
  return evts.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

export const mockSettingsStatus: SettingsStatus = {
  anthropic_api_key: true,
  anthropic_model: "claude-sonnet-4-5",
  github_token: true,
  email_provider: false,
};

function generateHistory(baseStatus: MonitorStatus, points = 60) {
  const history = [];
  for (let i = 0; i < points; i++) {
    let status: MonitorStatus = baseStatus;
    const rand = Math.random();
    // Simulate some downtime/degradation regardless of baseStatus
    if (rand > 0.97) status = "DOWN";
    else if (rand > 0.92) status = "DEGRADED";
    else if (baseStatus === "DEGRADED" && rand > 0.4) status = "DEGRADED";
    else status = "UP";

    history.push({
      status,
      timestamp: new Date(now - (points - i) * 300000).toISOString(),
    });
  }
  return history;
}

export const mockMonitors: Monitor[] = [
  {
    id: "mon_001",
    name: "Production Checkout",
    url: "https://api.morphic.dev/checkout",
    auth_type: "BEARER",
    status: "UP",
    uptime_pct: 99.98,
    latency_ms: 142,
    last_check: new Date(now - 1000 * 30).toISOString(),
    notifications: [
      { type: "SLACK", destination: "#alerts-prod", enabled: true },
      { type: "EMAIL", destination: "sre@morphic.dev", enabled: true },
    ],
    workflows: [
      {
        id: "wf_001",
        name: "Restart Checkout Svc",
        url: "https://n8n.morphic.dev/wf/1",
        enabled: true,
      },
    ],
    history: generateHistory("UP"),
    logs_url: "https://logs.morphic.dev/checkout",
  },
  {
    id: "mon_002",
    name: "Auth Service",
    url: "https://auth.morphic.dev/health",
    auth_type: "NONE",
    status: "DEGRADED",
    uptime_pct: 98.5,
    latency_ms: 850,
    last_check: new Date(now - 1000 * 45).toISOString(),
    notifications: [
      { type: "TELEGRAM", destination: "@morphic_ops", enabled: true },
      { type: "NTFY", destination: "https://ntfy.sh/morphic_critical", enabled: true },
    ],
    workflows: [],
    history: generateHistory("DEGRADED"),
    logs_url: "https://logs.morphic.dev/auth",
  },
];


export const mockIntegrations: IntegrationSettings = {
  vcs: {
    github_token: "ghp_********************",
    gitlab_token: "glpat-********************",
    gitlab_url: "https://gitlab.com",
  },
  ai: {
    anthropic_api_key: "sk-ant-********************",
    anthropic_model: "claude-3-5-sonnet",
  },
  infrastructure: {
    n8n_url: "https://n8n.morphic.dev",
    n8n_api_key: "n8n_api_********************",
    mcp_servers: [
      { name: "Postgres MCP", url: "http://localhost:8001", enabled: true },
      { name: "Neo4j MCP", url: "http://localhost:8002", enabled: false },
    ],
  },
  databases: {
    postgres_url: "postgresql://user:pass@localhost:5432/morphic",
    neo4j_url: "bolt://localhost:7687",
    neo4j_user: "neo4j",
    neo4j_password: "password123",
  },
  notifications: {
    smtp_host: "smtp.morphic.dev",
    smtp_port: 587,
    smtp_user: "alert@morphic.dev",
    smtp_password: "password****************",
    sender_name: "Morphic Alerts",
    sender_email: "noreply@morphic.dev",
    ntfy_topic: "morphic_ops",
    slack_webhook: "https://hooks.slack.com/services/...",
    telegram_bot_token: "123456:ABC-DEF...",
    telegram_chat_id: "-100123456789",
  },
};

export function generateMonitorMetrics(monitorId: string, points = 20) {
  const data = [];
  const baseLatency = monitorId === "mon_002" ? 800 : 100;
  for (let i = 0; i < points; i++) {
    data.push({
      timestamp: new Date(now - (points - i) * 60000).toISOString(),
      latency:
        baseLatency +
        Math.random() * 50 -
        25 +
        (i > points - 5 && monitorId === "mon_002" ? 200 : 0),
      status: Math.random() > 0.05 ? 1 : 0,
    });
  }
  return data;
}
