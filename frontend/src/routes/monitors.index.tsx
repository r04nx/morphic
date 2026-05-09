import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, RefreshCw, Activity, Search, Terminal, Globe, Info } from "lucide-react";
import { api } from "@/api/client";
import { AppShell } from "@/components/morphic/AppShell";
import { MonitorCard } from "@/components/morphic/MonitorCard";
import { EmptyState, ErrorState, SkeletonCard } from "@/components/morphic/states";
import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

export const Route = createFileRoute("/monitors/")({
  head: () => ({
    meta: [
      { title: "Monitors — Morphic" },
      { name: "description", content: "Live application health and SLA monitoring." },
    ],
  }),
  component: MonitorsPage,
});

function MonitorsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["monitors"],
    queryFn: () => api.listMonitors(),
    refetchInterval: 30_000,
  });

  const filtered = useMemo(() => {
    let list = data ?? [];
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (m) => m.name.toLowerCase().includes(q) || m.url.toLowerCase().includes(q),
      );
    }
    return list;
  }, [data, search]);

  const stats = useMemo(() => {
    if (!data) return { up: 0, total: 0, avgLatency: 0 };
    const up = data.filter((m) => m.status === "UP").length;
    const avgLatency =
      data.length > 0
        ? Math.round(data.reduce((acc, m) => acc + m.latency_ms, 0) / data.length)
        : 0;
    return { up, total: data.length, avgLatency };
  }, [data]);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteMonitor(id),
    onSuccess: () => {
      toast.success("Monitor deleted");
      queryClient.invalidateQueries({ queryKey: ["monitors"] });
    },
    onError: () => toast.error("Failed to delete monitor"),
  });

  return (
    <AppShell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-gradient">System Monitors</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {stats.up} of {stats.total} services are healthy · Avg latency {stats.avgLatency}ms
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-secondary/60 px-3 py-1.5 text-sm transition hover:border-primary/40"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", isFetching && "animate-spin")} />
            Refresh
          </button>

          <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
            <DialogTrigger asChild>
              <button className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition hover:opacity-90">
                <Plus className="h-3.5 w-3.5" />
                Add Monitor
              </button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px] glass border-primary/20">
              <DialogDescription className="sr-only">
                Configure a new application health and logs monitor.
              </DialogDescription>
              <CreateMonitorForm
                onSuccess={() => {
                  setIsCreateOpen(false);
                  queryClient.invalidateQueries({ queryKey: ["monitors"] });
                }}
              />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="mb-6 flex items-center gap-2 rounded-xl border border-border bg-card/40 p-3">
        <Search className="h-4 w-4 text-muted-foreground ml-1" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter monitors by name or URL..."
          className="h-9 flex-1 bg-transparent px-2 text-sm focus:outline-none"
        />
      </div>

      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {isError && (
        <ErrorState
          title="Failed to load monitors"
          description="Unable to fetch monitoring data. Please check your connection."
          action={
            <button onClick={() => refetch()} className="btn-primary">
              Retry
            </button>
          }
        />
      )}

      {!isLoading && !isError && filtered.length === 0 && (
        <EmptyState
          icon={<Activity className="h-8 w-8 text-muted-foreground/50" />}
          title="No monitors found"
          description={
            search
              ? "No monitors match your search query."
              : "Start by adding your first application monitor."
          }
        />
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((monitor) => (
          <MonitorCard 
            key={monitor.id} 
            monitor={monitor} 
            onDelete={() => deleteMutation.mutate(monitor.id)}
          />
        ))}
      </div>
    </AppShell>
  );
}

function CreateMonitorForm({ onSuccess }: { onSuccess: () => void }) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [logsSource, setLogsSource] = useState<"HTTP" | "DATADOG" | "GRAFANA" | "HONEYCOMB" | "CORALOGIX">("HTTP");
  const [logsUrl, setLogsUrl] = useState("");
  const [authType, setAuthType] = useState<"NONE" | "BEARER" | "BASIC">("NONE");
  const [bearerToken, setBearerToken] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  // GitHub self-healing
  const [githubRepo, setGithubRepo] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [githubBranch, setGithubBranch] = useState("main");
  const [isLoading, setIsLoading] = useState(false);

  const [healthTest, setHealthTest] = useState<{
    status?: number;
    success?: boolean;
    testing?: boolean;
  }>({});
  const [logsTest, setLogsTest] = useState<{
    status?: number;
    success?: boolean;
    testing?: boolean;
    tail?: string;
  }>({});

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !url) return;

    setIsLoading(true);
    try {
      await api.createMonitor({
        name,
        url,
        logs_url: logsUrl,
        auth_type: authType,
        github_repo: githubRepo || undefined,
        github_token: githubToken || undefined,
        github_branch: githubBranch || "main",
        log_tail_enabled: !!logsUrl,
      } as any);
      toast.success("Monitor created successfully");
      onSuccess();
    } catch (err) {
      toast.error("Failed to create monitor");
    } finally {
      setIsLoading(false);
    }
  };

  const handleTest = async (type: "health" | "logs") => {
    const setter = type === "health" ? setHealthTest : setLogsTest;
    const urlValue = type === "health" ? url : logsUrl;

    if (!urlValue) {
      toast.error(`Please enter a ${type === "health" ? "healthcheck" : "logs"} URL first`);
      return;
    }

    setter({ testing: true });
    try {
      const startTime = performance.now();
      
      const res = await api.testMonitorConnection({
        url: urlValue,
        type,
        auth_type: authType,
        bearer_token: bearerToken,
        username,
        password,
      });
      
      const endTime = performance.now();
      
      if (!res.success) {
        throw new Error(res.message || `Connection failed (HTTP ${res.status || 'Error'})`);
      }

      let tailContent = "";
      if (type === "logs" && res.tail) {
        const data = res.tail;
        
        if (Array.isArray(data)) {
          tailContent = data.slice(-10).map(l => {
            const levelColor = l.level === "ERROR" ? "\x1b[31m" : l.level === "WARN" ? "\x1b[33m" : "\x1b[32m";
            return `[${l.timestamp}] ${levelColor}${l.level}\x1b[0m: ${l.message}`;
          }).join("\n");
        } else if (typeof data === "string") {
          tailContent = data;
        } else {
          tailContent = JSON.stringify(data, null, 2);
        }
      }

      setter({
        testing: false,
        success: true,
        status: res.status || 200,
        tail: tailContent
      });
      
      toast.success(`${type === "health" ? "Healthcheck" : "Logs"} verified in ${Math.round(endTime - startTime)}ms`);
    } catch (err: any) {
      console.error(err);
      setter({ testing: false, success: false, status: 0 });
      toast.error(`Failed to verify ${type}: ${err.message}`);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5 pt-2 max-h-[80vh] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-white/10">
      <DialogHeader>
        <DialogTitle className="text-xl font-bold tracking-tight">Add New Monitor</DialogTitle>
      </DialogHeader>
      
      <div className="space-y-4">
        {/* Basic Info */}
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="name" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">Display Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Production Checkout"
              className="bg-secondary/20 border-border/50 focus:border-primary/50 h-10 transition-all"
              required
            />
          </div>
          
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor="url" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">Healthcheck URL</Label>
              {healthTest.status && (
                <span className={cn(
                  "text-[10px] font-bold px-1.5 py-0.5 rounded-full border",
                  healthTest.success ? "bg-success/10 text-success border-success/20" : "bg-destructive/10 text-destructive border-destructive/20"
                )}>
                  HTTP {healthTest.status}
                </span>
              )}
            </div>
            <div className="flex gap-2">
              <Input
                id="url"
                type="url"
                value={url}
                onChange={(e) => { setUrl(e.target.value); setHealthTest({}); }}
                placeholder="https://api.example.com/health"
                className={cn(
                  "flex-1 bg-secondary/20 border-border/50 focus:border-primary/50 h-10 transition-all",
                  healthTest.success && "border-success/50 ring-1 ring-success/20"
                )}
                required
              />
              <button
                type="button"
                onClick={() => handleTest("health")}
                disabled={healthTest.testing}
                className="flex items-center gap-2 rounded-md border border-border bg-secondary/40 px-4 h-10 text-xs font-semibold transition hover:bg-secondary/60 hover:border-primary/30"
              >
                <RefreshCw className={cn("h-3.5 w-3.5", healthTest.testing && "animate-spin")} />
                Test
              </button>
            </div>
          </div>
        </div>

        <div className="h-px bg-border/40" />

        {/* Logs Source */}
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">Logs Source</Label>
            <Select value={logsSource} onValueChange={(v: any) => setLogsSource(v)}>
              <SelectTrigger className="bg-secondary/20 border-border/50 h-10">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="glass">
                <SelectItem value="HTTP">
                  <div className="flex items-center gap-2">
                    <Globe className="h-3.5 w-3.5 opacity-70" />
                    <span>HTTP (Active)</span>
                  </div>
                </SelectItem>
                <SelectItem value="DATADOG">
                  <div className="flex items-center gap-2">
                    <img src="https://www.google.com/s2/favicons?domain=datadoghq.com&sz=32" className="h-3.5 w-3.5 rounded-sm" alt="" />
                    <span>Datadog <span className="text-[10px] opacity-60 ml-1">(coming soon)</span></span>
                  </div>
                </SelectItem>
                <SelectItem value="GRAFANA">
                  <div className="flex items-center gap-2">
                    <img src="https://www.google.com/s2/favicons?domain=grafana.com&sz=32" className="h-3.5 w-3.5 rounded-sm" alt="" />
                    <span>Grafana <span className="text-[10px] opacity-60 ml-1">(coming soon)</span></span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {logsSource === "HTTP" && (
            <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="logs-url" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">Source URL</Label>
                  {logsTest.status && (
                    <span className={cn(
                      "text-[10px] font-bold px-1.5 py-0.5 rounded-full border",
                      logsTest.success ? "bg-success/10 text-success border-success/20" : "bg-destructive/10 text-destructive border-destructive/20"
                    )}>
                      HTTP {logsTest.status}
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  <Input
                    id="logs-url"
                    type="url"
                    value={logsUrl}
                    onChange={(e) => { setLogsUrl(e.target.value); setLogsTest({}); }}
                    placeholder="https://logs.example.com/stream"
                    className={cn(
                      "flex-1 bg-secondary/20 border-border/50 focus:border-primary/50 h-10 transition-all",
                      logsTest.success && "border-success/50 ring-1 ring-success/20"
                    )}
                  />
                  <button
                    type="button"
                    onClick={() => handleTest("logs")}
                    disabled={logsTest.testing}
                    className="flex items-center gap-2 rounded-md border border-border bg-secondary/40 px-4 h-10 text-xs font-semibold transition hover:bg-secondary/60 hover:border-primary/30"
                  >
                    <RefreshCw className={cn("h-3.5 w-3.5", logsTest.testing && "animate-spin")} />
                    Test
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">Authentication</Label>
                  <Select value={authType} onValueChange={(v: any) => setAuthType(v)}>
                    <SelectTrigger className="bg-secondary/20 border-border/50 h-9 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="glass">
                      <SelectItem value="NONE">None</SelectItem>
                      <SelectItem value="BEARER">Bearer Token</SelectItem>
                      <SelectItem value="BASIC">Basic Auth</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {authType === "BEARER" && (
                  <div className="space-y-1.5 animate-in fade-in zoom-in-95 duration-200">
                    <Label htmlFor="token" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">Token</Label>
                    <Input
                      id="token"
                      type="password"
                      value={bearerToken}
                      onChange={(e) => setBearerToken(e.target.value)}
                      placeholder="sk-..."
                      className="bg-secondary/20 border-border/50 h-9 text-xs"
                    />
                  </div>
                )}

                {authType === "BASIC" && (
                  <div className="space-y-1.5 animate-in fade-in zoom-in-95 duration-200 flex gap-2 col-span-2">
                    <div className="flex-1 space-y-1.5">
                      <Label htmlFor="user" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">Username</Label>
                      <Input id="user" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="admin" className="bg-secondary/20 border-border/50 h-9 text-xs" />
                    </div>
                    <div className="flex-1 space-y-1.5">
                      <Label htmlFor="pass" className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">Password</Label>
                      <Input id="pass" type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="bg-secondary/20 border-border/50 h-9 text-xs" />
                    </div>
                  </div>
                )}
              </div>

              {logsTest.tail && (
                <div className="mt-2 rounded-xl bg-black/95 p-4 font-mono text-[11px] text-zinc-300 shadow-2xl border border-white/10 max-h-[200px] overflow-y-auto leading-relaxed whitespace-pre-wrap animate-in zoom-in-95 duration-300 scrollbar-thin scrollbar-thumb-white/10">
                  <div className="flex items-center justify-between mb-2 border-b border-white/10 pb-2">
                    <div className="flex items-center gap-2 text-[10px] text-muted-foreground uppercase tracking-widest font-bold">
                      <Terminal className="h-3.5 w-3.5 text-primary" />
                      Live Log Stream Preview
                    </div>
                    <div className="flex gap-1">
                      <div className="h-2 w-2 rounded-full bg-red-500/50" />
                      <div className="h-2 w-2 rounded-full bg-yellow-500/50" />
                      <div className="h-2 w-2 rounded-full bg-green-500/50" />
                    </div>
                  </div>
                  <AnsiText text={logsTest.tail} />
                </div>
              )}
            </div>
          )}
        </div>

        <div className="h-px bg-border/40" />

        {/* GitHub Self-Healing */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="h-5 w-5 rounded bg-foreground/10 flex items-center justify-center">
              <svg viewBox="0 0 16 16" className="h-3.5 w-3.5 fill-current"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
            </div>
            <div className="flex items-center gap-2">
              <Label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/80">GitHub Self-Healing</Label>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button className="h-4 w-4 rounded-full flex items-center justify-center text-muted-foreground/60 hover:text-muted-foreground transition-colors">
                      <Info className="h-3 w-3" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top" className="max-w-xs">
                    <p className="text-xs leading-relaxed">
                      On anomaly detection, Claude Code will clone this repo, perform RCA, and open a PR with an automated fix.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <span className="ml-auto text-[10px] text-primary/70 font-medium bg-primary/10 px-2 py-0.5 rounded-full">AI Agent</span>
          </div>
          <p className="text-[11px] text-muted-foreground leading-relaxed">
            On anomaly detection, Claude Code will clone this repo, perform RCA, and open a PR with an automated fix.
          </p>
          <div className="space-y-2">
            <div className="space-y-1.5">
              <Label htmlFor="github-repo" className="text-xs text-muted-foreground">Repository (owner/repo)</Label>
              <Input
                id="github-repo"
                value={githubRepo}
                onChange={(e) => setGithubRepo(e.target.value)}
                placeholder="acme-corp/payment-service"
                className="bg-secondary/20 border-border/50 focus:border-primary/50 h-9 text-xs font-mono"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5">
                <Label htmlFor="github-branch" className="text-xs text-muted-foreground">Target Branch</Label>
                <Input
                  id="github-branch"
                  value={githubBranch}
                  onChange={(e) => setGithubBranch(e.target.value)}
                  placeholder="main"
                  className="bg-secondary/20 border-border/50 h-9 text-xs font-mono"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="github-token" className="text-xs text-muted-foreground">PAT Token (optional)</Label>
                <Input
                  id="github-token"
                  type="password"
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  placeholder="ghp_..."
                  className="bg-secondary/20 border-border/50 h-9 text-xs font-mono"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <DialogFooter className="pt-2">
        <button
          type="submit"
          disabled={isLoading || !name || !url}
          className="w-full rounded-xl bg-primary py-3 text-sm font-bold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:scale-[1.01] hover:shadow-primary/30 active:scale-[0.99] disabled:opacity-50 disabled:scale-100 disabled:hover:scale-100"
        >
          {isLoading ? (
            <div className="flex items-center justify-center gap-2">
              <RefreshCw className="h-4 w-4 animate-spin" />
              Creating...
            </div>
          ) : "Create Monitor"}
        </button>
      </DialogFooter>
    </form>
  );
}
function AnsiText({ text }: { text: string }) {
  // Simple ANSI to styled spans parser
  const parts = text.split(/(\x1b\[[0-9;]*m)/);
  let currentColor = "";

  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("\x1b[")) {
          if (part.includes("32m")) currentColor = "text-success";
          else if (part.includes("33m")) currentColor = "text-warning";
          else if (part.includes("31m")) currentColor = "text-destructive";
          else if (part.includes("0m")) currentColor = "";
          return null;
        }
        return (
          <span key={i} className={currentColor}>
            {part}
          </span>
        );
      })}
    </>
  );
}
