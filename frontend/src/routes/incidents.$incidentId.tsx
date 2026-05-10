import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ExternalLink, GitPullRequestArrow, Mail, Loader2, Bot, CheckCircle, XCircle, Clock } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { api } from "@/api/client";
import { AppShell } from "@/components/morphic/AppShell";
import {
  ActionStatusChip,
  ActionTypeBadge,
  SeverityBadge,
  StatusChip,
} from "@/components/morphic/badges";
import { CopyButton } from "@/components/morphic/CopyButton";
import { EmptyState, ErrorState, SkeletonCard } from "@/components/morphic/states";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { format } from "date-fns";
import type { RCA } from "@/types/morphic";

export const Route = createFileRoute("/incidents/$incidentId")({
  head: ({ params }) => ({
    meta: [
      { title: `Incident ${params.incidentId} — Morphic` },
      { name: "description", content: "RCA, suggested fix, and automated actions." },
    ],
  }),
  component: IncidentDetailPage,
});

function IncidentDetailPage() {
  const { incidentId } = Route.useParams();
  const router = useRouter();
  const qc = useQueryClient();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["incident", incidentId],
    queryFn: () => api.getIncident(incidentId),
    refetchInterval: (q) => (q.state.data?.incident.status === "RESOLVED" ? false : 10_000),
  });

  // Fetch agent runs for this incident
  const { data: agentRuns, isLoading: isLoadingAgentRuns } = useQuery({
    queryKey: ["agent-runs", "incident", incidentId],
    queryFn: () => api.getAgentRunsByIncident(incidentId),
    refetchInterval: 5_000, // Refresh every 5 seconds for real-time updates
  });

  const emailMut = useMutation({
    mutationFn: () => api.triggerEmail(incidentId),
    onSuccess: () => {
      toast.success("Email action dispatched");
      qc.invalidateQueries({ queryKey: ["incident", incidentId] });
      qc.invalidateQueries({ queryKey: ["actions"] });
    },
    onError: () => toast.error("Failed to dispatch email"),
  });
  const prMut = useMutation({
    mutationFn: () => api.triggerPR(incidentId),
    onSuccess: (a) => {
      toast.success("Pull request opened", { description: a.link });
      qc.invalidateQueries({ queryKey: ["incident", incidentId] });
      qc.invalidateQueries({ queryKey: ["actions"] });
    },
    onError: () => toast.error("Failed to open PR"),
  });

  return (
    <AppShell>
      <button
        onClick={() => router.history.back()}
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back
      </button>

      {isLoading && (
        <div className="space-y-4">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}
      {isError && (
        <ErrorState
          title="Could not load incident"
          action={
            <button
              onClick={() => refetch()}
              className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground"
            >
              Retry
            </button>
          }
        />
      )}
      {data && (
        <>
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="flex flex-wrap items-center gap-2">
              <SeverityBadge value={data.incident.blast_radius} />
              <StatusChip value={data.incident.status} />
              {data.incident.confidence_score !== undefined && (
                <span className="font-mono text-[11px] text-muted-foreground">
                  confidence {(data.incident.confidence_score * 100).toFixed(0)}%
                </span>
              )}
              <span className="ml-auto font-mono text-[11px] text-muted-foreground">
                {format(new Date(data.incident.timestamp), "PPpp")}
              </span>
            </div>
            <h1 className="mt-3 text-2xl font-semibold leading-tight">{data.incident.summary}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              {data.incident.service && (
                <span className="font-mono">
                  {data.incident.service}
                  {data.incident.endpoint ? ` · ${data.incident.endpoint}` : ""}
                </span>
              )}
              <span className="font-mono">{data.incident.trace_id}</span>
              <CopyButton value={data.incident.trace_id} label="copy trace" />
              <Link
                to="/traces/$traceId"
                params={{ traceId: data.incident.trace_id }}
                className="inline-flex items-center gap-1 text-primary hover:underline"
              >
                View trace timeline <ExternalLink className="h-3 w-3" />
              </Link>
            </div>
          </div>

          <Tabs defaultValue="rca" className="mt-6">
            <TabsList>
              <TabsTrigger value="rca">RCA</TabsTrigger>
              <TabsTrigger value="agent">Claude Agent</TabsTrigger>
              <TabsTrigger value="actions">Actions</TabsTrigger>
              <TabsTrigger value="logs">Related Logs</TabsTrigger>
            </TabsList>

            <TabsContent value="rca" className="mt-4">
              {data.rca ? (
                <RcaCard rca={data.rca} />
              ) : (
                <EmptyState
                  title="RCA not ready yet"
                  description="Morphic is still analyzing this incident. The page will refresh automatically."
                />
              )}
            </TabsContent>

            <TabsContent value="agent" className="mt-4">
              {isLoadingAgentRuns ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading agent status...
                </div>
              ) : agentRuns && agentRuns.length > 0 ? (
                <div className="space-y-4">
                  {agentRuns.map((run) => (
                    <div key={run.id} className="rounded-xl border border-border bg-card p-5">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Bot className="h-4 w-4 text-primary" />
                          <span className="font-medium">Claude Agent Run</span>
                        </div>
                        <AgentStatusChip status={run.status} />
                      </div>
                      
                      <div className="grid gap-4 md:grid-cols-2">
                        <div>
                          <div className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                            Triggered
                          </div>
                          <div className="mt-1 font-mono text-sm">
                            {format(new Date(run.triggered_at), "PPpp")}
                          </div>
                        </div>
                        {run.completed_at && (
                          <div>
                            <div className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                              Duration
                            </div>
                            <div className="mt-1 font-mono text-sm">
                              {formatDuration(run.triggered_at, run.completed_at)}
                            </div>
                          </div>
                        )}
                      </div>
                      
                      {run.github_pr_url && (
                        <div className="mt-4">
                          <div className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                            Pull Request
                          </div>
                          <a
                            href={run.github_pr_url}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-2 inline-flex items-center gap-2 text-sm text-primary hover:underline"
                          >
                            <GitPullRequestArrow className="h-4 w-4" />
                            View PR on GitHub
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        </div>
                      )}
                      
                      {run.claude_output && (
                        <div className="mt-4">
                          <div className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                            Claude Analysis
                          </div>
                          <div className="mt-2 rounded-lg border border-border bg-secondary/20 p-3">
                            <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-foreground/90">
                              {run.claude_output.slice(0, 500)}
                              {run.claude_output.length > 500 && "..."}
                            </pre>
                          </div>
                        </div>
                      )}
                      
                      {run.error_message && (
                        <div className="mt-4">
                          <div className="text-[11px] font-mono uppercase tracking-wider text-destructive">
                            Error
                          </div>
                          <div className="mt-1 rounded-lg border border-destructive/30 bg-destructive/5 p-3">
                            <p className="text-sm text-destructive">{run.error_message}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="No agent runs yet"
                  description="Claude agent has not been triggered for this incident."
                />
              )}
            </TabsContent>

            <TabsContent value="actions" className="mt-4 space-y-4">
              <div className="flex flex-wrap gap-2">
                <ConfirmAction
                  title="Send email to on-call?"
                  description="This will notify the configured on-call alias for this service."
                  onConfirm={() => emailMut.mutate()}
                  disabled={emailMut.isPending}
                  icon={<Mail className="h-3.5 w-3.5" />}
                  label={emailMut.isPending ? "Sending…" : "Send email"}
                  loading={emailMut.isPending}
                />
                <ConfirmAction
                  title="Create GitHub PR with suggested fix?"
                  description="A draft PR will be opened against the default branch using the patch in the RCA."
                  onConfirm={() => prMut.mutate()}
                  disabled={prMut.isPending}
                  icon={<GitPullRequestArrow className="h-3.5 w-3.5" />}
                  label={prMut.isPending ? "Opening PR…" : "Create PR"}
                  loading={prMut.isPending}
                />
              </div>

              {data.actions.length === 0 ? (
                <EmptyState
                  title="No actions yet"
                  description="Trigger an action above or wait for Morphic to act."
                />
              ) : (
                <div className="overflow-hidden rounded-xl border border-border bg-card">
                  <table className="w-full text-sm">
                    <thead className="bg-secondary/40 text-left text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2">Type</th>
                        <th className="px-3 py-2">Status</th>
                        <th className="px-3 py-2">Summary</th>
                        <th className="px-3 py-2">Started</th>
                        <th className="px-3 py-2">Link</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.actions.map((a) => (
                        <tr key={a.id} className="border-t border-border/60">
                          <td className="px-3 py-2">
                            <ActionTypeBadge value={a.action_type} />
                          </td>
                          <td className="px-3 py-2">
                            <ActionStatusChip value={a.status} />
                          </td>
                          <td className="px-3 py-2 text-foreground/90">{a.summary ?? "—"}</td>
                          <td className="px-3 py-2 font-mono text-[11px] text-muted-foreground">
                            {a.started_at ? format(new Date(a.started_at), "HH:mm:ss") : "—"}
                          </td>
                          <td className="px-3 py-2">
                            {a.link ? (
                              <a
                                className="inline-flex items-center gap-1 text-primary hover:underline"
                                href={a.link}
                                target="_blank"
                                rel="noreferrer"
                              >
                                Open <ExternalLink className="h-3 w-3" />
                              </a>
                            ) : (
                              "—"
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </TabsContent>

            <TabsContent value="logs" className="mt-4">
              <RelatedLogsPreview traceId={data.incident.trace_id} />
            </TabsContent>
          </Tabs>
        </>
      )}
    </AppShell>
  );
}

function RcaCard({ rca }: { rca: RCA }) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="space-y-4 lg:col-span-2">
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
            Classification
          </div>
          <div className="mt-1 text-base font-medium">{rca.classification}</div>

          <div className="mt-4 text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
            Root cause
          </div>
          <p className="mt-1 leading-relaxed">{rca.root_cause}</p>

          <div className="mt-4 text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
            Impact
          </div>
          <p className="mt-1 leading-relaxed">{rca.impact}</p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold">Suggested fix</h3>
            <span className="font-mono text-[11px] text-muted-foreground">
              {rca.suggested_fix.target_class}
            </span>
          </div>
          <div className="relative overflow-hidden rounded-lg border border-border bg-[oklch(0.14_0.018_260)]">
            <div className="absolute right-2 top-2">
              <CopyButton value={rca.suggested_fix.patch} label="copy patch" />
            </div>
            <pre className="overflow-x-auto p-4 font-mono text-[12.5px] leading-relaxed text-foreground/90">
              {rca.suggested_fix.patch.split("\n").map((line, i) => (
                <div
                  key={i}
                  className={
                    line.startsWith("+") && !line.startsWith("+++")
                      ? "text-success"
                      : line.startsWith("-") && !line.startsWith("---")
                        ? "text-[oklch(0.78_0.18_25)]"
                        : line.startsWith("@@")
                          ? "text-info"
                          : "text-muted-foreground"
                  }
                >
                  {line || " "}
                </div>
              ))}
            </pre>
          </div>
          <div className="mt-3 text-sm">
            <span className="text-muted-foreground">Rationale: </span>
            {rca.suggested_fix.rationale}
          </div>
          {rca.suggested_fix.tests.length > 0 && (
            <div className="mt-3">
              <div className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                Tests
              </div>
              <ul className="mt-1 space-y-1 font-mono text-xs">
                {rca.suggested_fix.tests.map((t) => (
                  <li key={t} className="text-foreground/80">
                    · {t}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <h3 className="text-sm font-semibold">Suggested PR</h3>
          <div className="mt-2 font-mono text-sm">{rca.github_pr.title}</div>
          <div className="mt-2 flex flex-wrap gap-1">
            {rca.github_pr.labels.map((l) => (
              <span
                key={l}
                className="rounded border border-border bg-secondary/60 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
              >
                {l}
              </span>
            ))}
          </div>
          <p className="mt-3 whitespace-pre-line text-sm text-muted-foreground">
            {rca.github_pr.body}
          </p>
        </div>
      </div>

      <div className="space-y-4">
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
            Confidence
          </div>
          <div className="mt-2 flex items-center gap-3">
            <Progress value={rca.confidence_score * 100} className="h-2" />
            <span className="font-mono text-sm">{(rca.confidence_score * 100).toFixed(0)}%</span>
          </div>
          <div className="mt-4 text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
            Severity
          </div>
          <div className="mt-2">
            <SeverityBadge value={rca.blast_radius} />
          </div>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
            Log signals
          </div>
          <dl className="mt-2 space-y-1.5 font-mono text-xs">
            <Row label="service" value={rca.log_signals.service} />
            <Row label="endpoint" value={rca.log_signals.endpoint} />
            <Row label="exception" value={rca.log_signals.exception_class} />
            <div className="rounded-md border border-destructive/30 bg-destructive/5 p-2 text-[oklch(0.82_0.18_25)]">
              {rca.log_signals.error_message}
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <span className="w-20 text-muted-foreground">{label}</span>
      <span className="text-foreground/90">{value}</span>
    </div>
  );
}

function AgentStatusChip({ status }: { status: string }) {
  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'QUEUED':
        return { icon: <Clock className="h-3 w-3" />, color: 'text-muted-foreground', bg: 'bg-secondary/20', label: 'Queued' };
      case 'RUNNING':
        return { icon: <Loader2 className="h-3 w-3 animate-spin" />, color: 'text-blue-600', bg: 'bg-blue-50', label: 'Running' };
      case 'ANALYZING':
        return { icon: <Bot className="h-3 w-3" />, color: 'text-purple-600', bg: 'bg-purple-50', label: 'Analyzing' };
      case 'PR_CREATED':
        return { icon: <CheckCircle className="h-3 w-3" />, color: 'text-green-600', bg: 'bg-green-50', label: 'PR Created' };
      case 'COMPLETED':
        return { icon: <CheckCircle className="h-3 w-3" />, color: 'text-green-600', bg: 'bg-green-50', label: 'Completed' };
      case 'FAILED':
        return { icon: <XCircle className="h-3 w-3" />, color: 'text-red-600', bg: 'bg-red-50', label: 'Failed' };
      default:
        return { icon: <Clock className="h-3 w-3" />, color: 'text-muted-foreground', bg: 'bg-secondary/20', label: status };
    }
  };

  const config = getStatusConfig(status);
  
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 font-mono text-[10px] font-medium ${config.bg} ${config.color}`}>
      {config.icon}
      {config.label}
    </span>
  );
}

function formatDuration(started: string, completed: string): string {
  const start = new Date(started);
  const end = new Date(completed);
  const diffMs = end.getTime() - start.getTime();
  
  if (diffMs < 1000) {
    return `${diffMs}ms`;
  } else if (diffMs < 60000) {
    return `${Math.round(diffMs / 1000)}s`;
  } else if (diffMs < 3600000) {
    return `${Math.round(diffMs / 60000)}m ${Math.round((diffMs % 60000) / 1000)}s`;
  } else {
    const hours = Math.floor(diffMs / 3600000);
    const minutes = Math.round((diffMs % 3600000) / 60000);
    return `${hours}h ${minutes}m`;
  }
}

function ConfirmAction({
  title,
  description,
  onConfirm,
  disabled,
  icon,
  label,
  loading,
}: {
  title: string;
  description: string;
  onConfirm: () => void;
  disabled?: boolean;
  icon: React.ReactNode;
  label: string;
  loading?: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>
        <button
          disabled={disabled}
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-secondary/60 px-3 py-1.5 text-sm transition hover:border-primary/40 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : icon}
          {label}
        </button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>Run</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

function RelatedLogsPreview({ traceId }: { traceId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["trace", traceId, "preview"],
    queryFn: () => api.listTraceEvents(traceId, 50),
    refetchInterval: 15_000,
  });
  if (isLoading) return <SkeletonCard />;
  const errs = (data ?? []).filter((e) => e.level === "ERROR" || e.level === "WARN").slice(0, 8);
  return (
    <div className="space-y-3">
      <div className="overflow-hidden rounded-xl border border-border bg-card">
        <ul className="divide-y divide-border/60">
          {(errs.length > 0 ? errs : (data ?? []).slice(0, 8)).map((e) => (
            <li key={e.id} className="flex items-start gap-3 px-4 py-2 font-mono text-xs">
              <span className="text-muted-foreground">
                {format(new Date(e.timestamp), "HH:mm:ss.SSS")}
              </span>
              <span
                className={
                  e.level === "ERROR"
                    ? "text-[oklch(0.82_0.18_25)]"
                    : e.level === "WARN"
                      ? "text-warning"
                      : "text-info"
                }
              >
                {e.level}
              </span>
              <span className="flex-1 text-foreground/90">{e.message}</span>
              {e.async_orphan && (
                <span className="rounded border border-warning/40 bg-warning/10 px-1.5 py-0.5 text-[10px] text-warning">
                  ASYNC-ORPHAN
                </span>
              )}
            </li>
          ))}
        </ul>
      </div>
      <Link
        to="/traces/$traceId"
        params={{ traceId }}
        className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
      >
        Open full trace timeline <ExternalLink className="h-3 w-3" />
      </Link>
    </div>
  );
}
