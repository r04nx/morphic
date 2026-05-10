import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Settings,
  Trash2,
  Bell,
  Zap,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ExternalLink,
  Plus,
  Send,
  Mail,
  Slack as SlackIcon,
  MessageSquare,
  ChevronRight,
  Activity,
  Terminal,
  Bot,
  GitPullRequest,
  Search,
  FileText,
  Maximize2,
  Download,
  X,
  Shield,
  Globe,
  PieChart as PieChartIcon,
  ZapOff,
  BarChart3,
  Waves,
  Fingerprint,
} from "lucide-react";
import { api } from "@/api/client";
import { CopyButton } from "@/components/morphic/CopyButton";
import { EmptyState, ErrorState, SkeletonCard } from "@/components/morphic/states";
import { AppShell } from "@/components/morphic/AppShell";
import { TelegramVerification } from "@/components/morphic/TelegramVerification";
import { useState, useMemo, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from "recharts";
import { format } from "date-fns";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useTheme } from "@/components/morphic/theme";

export const Route = createFileRoute("/monitors/$monitorId")({
  head: ({ params }) => ({
    meta: [{ title: `Monitor ${params.monitorId} — Morphic` }],
  }),
  component: MonitorDetailPage,
});

function MonitorDetailPage() {
  const { monitorId } = Route.useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isFullscreenLogs, setIsFullscreenLogs] = useState(false);
  const { resolvedTheme } = useTheme();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["monitor", monitorId],
    queryFn: () => api.getMonitor(monitorId),
    refetchInterval: 10_000,
  });

  const { data: metricsData = [] } = useQuery({
    queryKey: ["monitorMetrics", monitorId],
    queryFn: () => api.getMonitorMetrics(monitorId, 24),
    refetchInterval: 30_000,
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteMonitor(monitorId),
    onSuccess: () => {
      toast.success("Monitor deleted");
      navigate({ to: "/monitors" });
      queryClient.invalidateQueries({ queryKey: ["monitors"] });
    },
    onError: () => toast.error("Failed to delete monitor"),
  });

  const enableMutation = useMutation({
    mutationFn: () => api.enableMonitor(monitorId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["monitors"] });
      queryClient.invalidateQueries({ queryKey: ["monitor", monitorId] });
      toast.success("Monitor enabled");
    },
    onError: () => toast.error("Failed to enable monitor"),
  });

  const disableMutation = useMutation({
    mutationFn: () => api.disableMonitor(monitorId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["monitors"] });
      queryClient.invalidateQueries({ queryKey: ["monitor", monitorId] });
      toast.success("Monitor paused");
    },
    onError: () => toast.error("Failed to pause monitor"),
  });

  const updateMutation = useMutation({
    mutationFn: (updates: any) => api.updateMonitor(monitorId, updates),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["monitor", monitorId] });
      if (variables.notifications) {
        toast.success("Notification settings saved");
      } else {
        toast.success("Monitor updated");
      }
    },
    onError: () => toast.error("Failed to update monitor"),
  });

  if (isLoading)
    return (
      <AppShell>
        <SkeletonCard />
      </AppShell>
    );
  if (isError || !data)
    return (
      <AppShell>
        <ErrorState
          title="Monitor not found"
          description="This monitor may have been deleted or moved."
          action={
            <button onClick={() => navigate({ to: "/monitors" })} className="btn-secondary">
              Go Back
            </button>
          }
        />
      </AppShell>
    );

  const { monitor } = data;

  const StatusIcon = {
    UP: CheckCircle2,
    DOWN: XCircle,
    DEGRADED: AlertCircle,
  }[monitor.status as "UP" | "DOWN" | "DEGRADED"] || AlertCircle;

  return (
    <AppShell>
      <div className="space-y-8">
        {/* Header Section */}
        <div className="relative overflow-hidden rounded-xl bg-card border border-border shadow-sm">
          <div className="p-4 sm:p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
            <div className="flex items-center gap-4">
              <div className={cn(
                "w-10 h-10 rounded-lg flex items-center justify-center shadow-lg",
                monitor.status === "UP" ? "bg-emerald-500/20 text-emerald-500 dark:text-emerald-400" :
                monitor.status === "DOWN" ? "bg-rose-500/20 text-rose-500 dark:text-rose-400" : "bg-amber-500/20 text-amber-500 dark:text-amber-400"
              )}>
                <StatusIcon className="h-6 w-6" />
              </div>
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl font-bold tracking-tight text-foreground dark:text-white">{monitor.name}</h1>
                  <div className={cn(
                    "px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border",
                    monitor.status === "UP" ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20" :
                    monitor.status === "DOWN" ? "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20" :
                    "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20"
                  )}>
                    {monitor.status}
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground dark:text-zinc-400 font-mono">
                  <Globe className="h-3 w-3" />
                  {monitor.url.replace(/^https?:\/\//, '')}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 w-full md:w-auto">
              {[
                { label: "Latency", value: `${monitor.latency_ms}ms`, icon: Activity, color: "text-blue-500 dark:text-blue-400" },
                { label: "Uptime", value: `${monitor.uptime_pct}%`, icon: CheckCircle2, color: "text-emerald-500 dark:text-emerald-400" },
                { label: "Auth", value: monitor.auth_type, icon: Shield, color: "text-purple-500 dark:text-purple-400" },
              ].map((stat, idx) => (
                <div key={idx} className="bg-secondary/40 border border-border rounded-lg p-2.5 min-w-[100px]">
                  <p className="text-[10px] text-muted-foreground dark:text-zinc-400 uppercase tracking-wider font-semibold flex items-center gap-1.5 mb-1">
                    <stat.icon className={cn("h-3 w-3", stat.color)} />
                    {stat.label}
                  </p>
                  <p className="text-sm font-bold truncate text-foreground dark:text-zinc-100">{stat.value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Content (3/4) */}
          <div className="lg:col-span-3 space-y-6">
            <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-blue-500 dark:text-blue-400" />
                  <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground dark:text-zinc-300">Response Latency</h2>
                </div>
                <div className="text-[10px] text-muted-foreground bg-secondary px-2 py-0.5 rounded font-mono">24H RANGE</div>
              </div>
              <div className="h-[240px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={metricsData}>
                    <defs>
                      <linearGradient id="colorLat" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={resolvedTheme === 'dark' ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.03)"} />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={(val) => format(new Date(val), "HH:mm")}
                      fontSize={10}
                      stroke={resolvedTheme === 'dark' ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.3)"}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      fontSize={10}
                      stroke={resolvedTheme === 'dark' ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.3)"}
                      axisLine={false}
                      tickLine={false}
                      unit="ms"
                    />
                    <Tooltip
                      contentStyle={{ 
                        backgroundColor: resolvedTheme === 'dark' ? "#09090b" : "#ffffff", 
                        border: `1px solid ${resolvedTheme === 'dark' ? "#27272a" : "#e4e4e7"}`, 
                        borderRadius: "8px", 
                        fontSize: "11px" 
                      }}
                      itemStyle={{ color: "#3b82f6", fontWeight: "700" }}
                    />
                    <Area type="monotone" dataKey="latency" stroke="#3b82f6" fill="url(#colorLat)" strokeWidth={2} isAnimationActive={false} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <LogAIAnalysisPanel monitorId={monitorId} />
              <AgentRunsSection monitorId={monitorId} />
            </div>
            
            <LiveLogsStream monitorId={monitorId} onFullscreen={() => setIsFullscreenLogs(true)} />
          </div>

          {/* Sidebar (1/4) */}
          <div className="lg:col-span-1 space-y-6">
            <GitHubLinkSection monitor={monitor} />
            <WorkflowSection monitor={monitor} onUpdate={(w) => updateMutation.mutate({ workflows: w })} />
            <AlertChannelsSection monitor={monitor} onUpdate={(n) => updateMutation.mutate({ notifications: n })} />
            <SettingsSection 
              monitor={monitor} 
              onEnable={() => enableMutation.mutate()} 
              onDisable={() => disableMutation.mutate()} 
              onUpdate={(u) => updateMutation.mutate(u)}
              onDelete={() => deleteMutation.mutate()}
            />
          </div>
        </div>
      </div>

      {/* Fullscreen Logs Modal */}
      {isFullscreenLogs && (
        <LiveLogsStreamFullscreen 
          monitorId={monitorId} 
          onClose={() => setIsFullscreenLogs(false)} 
        />
      )}
    </AppShell>
  );
}

function GitHubLinkSection({ monitor }: { monitor: any }) {
  if (!monitor.github_repo) return null;
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center">
          <GitPullRequest className="h-4 w-4 text-indigo-500 dark:text-indigo-400" />
        </div>
        <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground dark:text-zinc-300">GitHub Link</h2>
      </div>
      <div className="flex items-center gap-3 p-2.5 rounded-lg bg-secondary/40 border border-border">
        <div className="w-8 h-8 rounded-md bg-secondary flex items-center justify-center">
          <Globe className="h-4 w-4 text-muted-foreground dark:text-zinc-400" />
        </div>
        <div className="flex-1 overflow-hidden">
          <p className="text-[11px] font-bold truncate tracking-tight text-foreground dark:text-white">{monitor.github_owner}/{monitor.github_repo}</p>
          <p className="text-[9px] text-muted-foreground dark:text-zinc-500 truncate">PR-based Self-healing</p>
        </div>
      </div>
      <a 
        href={`https://github.com/${monitor.github_owner}/${monitor.github_repo}`}
        target="_blank"
        rel="noreferrer"
        className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 py-2 text-[10px] font-bold text-indigo-600 dark:text-indigo-400 transition-all border border-indigo-500/20"
      >
        <ExternalLink className="h-3 w-3" />
        EXPLORE REPO
      </a>
    </div>
  );
}

function WorkflowSection({ monitor, onUpdate }: { monitor: any; onUpdate: (w: any[]) => void }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center">
          <Zap className="h-4 w-4 text-purple-500 dark:text-purple-400" />
        </div>
        <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground dark:text-zinc-300">Automations</h2>
      </div>
      <div className="space-y-2">
        {(monitor.workflows || []).map((wf: any) => (
          <div key={wf.id} className="flex items-center justify-between p-2.5 rounded-lg bg-secondary/30 border border-border">
            <div className="flex items-center gap-3">
              <Bot className="h-3.5 w-3.5 text-purple-500 dark:text-purple-400" />
              <div>
                <p className="text-[11px] font-bold truncate text-foreground dark:text-white">{wf.name}</p>
                <p className="text-[9px] text-muted-foreground font-mono truncate max-w-[100px]">{wf.url}</p>
              </div>
            </div>
            <Switch
              className="scale-75"
              checked={wf.enabled}
              onCheckedChange={(enabled) => {
                const newWfs = monitor.workflows.map((w: any) => w.id === wf.id ? { ...w, enabled } : w);
                onUpdate(newWfs);
              }}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function AlertChannelsSection({ monitor, onUpdate }: { monitor: any; onUpdate: (n: any[]) => void }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
          <Bell className="h-4 w-4 text-blue-500 dark:text-blue-400" />
        </div>
        <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground dark:text-zinc-300">Alert Channels</h2>
      </div>
      <div className="space-y-2">
        <NotificationChannel
          type="NTFY" name="ntfy.sh" domain="ntfy.sh" monitor={monitor}
          onSave={(data) => {
            const others = (monitor.notifications || []).filter((n: any) => n.type !== "NTFY");
            onUpdate([...others, { type: "NTFY", ...data, enabled: true }]);
          }}
        />
        <NotificationChannel
          type="EMAIL" name="Email" domain="gmail.com" monitor={monitor}
          onSave={(data) => {
            const others = (monitor.notifications || []).filter((n: any) => n.type !== "EMAIL");
            onUpdate([...others, { type: "EMAIL", ...data, enabled: true }]);
          }}
        />
        <NotificationChannel
          type="SLACK" name="Slack" domain="slack.com" monitor={monitor}
          onSave={(data) => {
            const others = (monitor.notifications || []).filter((n: any) => n.type !== "SLACK");
            onUpdate([...others, { type: "SLACK", ...data, enabled: true }]);
          }}
        />
      </div>
    </div>
  );
}

function SettingsSection({ monitor, onEnable, onDisable, onUpdate, onDelete }: { monitor: any; onEnable: () => void; onDisable: () => void; onUpdate: (u: any) => void; onDelete: () => void }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center">
          <Settings className="h-4 w-4 text-muted-foreground dark:text-zinc-300" />
        </div>
        <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground dark:text-zinc-300">Monitor Settings</h2>
      </div>
      <div className="space-y-2">
        <div className="flex items-center justify-between p-2.5 rounded-lg bg-secondary/30">
          <div className="text-[11px] font-bold text-foreground dark:text-zinc-100">Monitor Status</div>
          <Switch
            className="scale-75"
            checked={monitor.enabled !== false}
            onCheckedChange={(enabled) => enabled ? onEnable() : onDisable()}
          />
        </div>
        <div className="flex items-center justify-between p-2.5 rounded-lg bg-secondary/30">
          <div className="text-[11px] font-bold text-foreground dark:text-zinc-100">Log Tailing</div>
          <Switch
            className="scale-75"
            checked={monitor.log_tail_enabled}
            onCheckedChange={(enabled) => onUpdate({ log_tail_enabled: enabled })}
          />
        </div>
        <button
          onClick={onDelete}
          className="w-full mt-2 flex items-center justify-center gap-2 rounded-lg border border-rose-500/20 bg-rose-500/5 py-2 text-[10px] font-bold text-rose-500 transition-colors"
        >
          <Trash2 className="h-3 w-3" />
          DELETE MONITOR
        </button>
      </div>
    </div>
  );
}

function LogAIAnalysisPanel({ monitorId }: { monitorId: string }) {
  const { data: analysis, isLoading } = useQuery({
    queryKey: ["monitorAnalysis", monitorId],
    queryFn: () => api.getMonitorAnalysis(monitorId),
    refetchInterval: 10_000,
  });

  const { data: analysisHistory } = useQuery({
    queryKey: ["monitorAnalysisHistory", monitorId],
    queryFn: () => api.getMonitorAnalysisHistory(monitorId, 30),
    refetchInterval: 15_000,
  });

  const { resolvedTheme } = useTheme();

  if (isLoading || !analysis || Object.keys(analysis).length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 shadow-sm h-[400px] flex flex-col items-center justify-center text-center">
        <Shield className="h-8 w-8 text-muted-foreground/30 mb-3" />
        <h3 className="text-sm font-semibold text-muted-foreground">LogAI Calibrating...</h3>
        <p className="text-[10px] text-muted-foreground/60 mt-2">Waiting for first analysis batch</p>
      </div>
    );
  }

  const radarData = [
    { subject: "Semantic", A: (analysis.semantic_score || 0) * 100 },
    { subject: "Stats", A: (analysis.iso_score || 0) * 100 },
    { subject: "Freq", A: (analysis.ts_score || 0) * 100 },
    { subject: "Error", A: (analysis.error_rate || 0) * 100 },
    { subject: "Comp", A: (analysis.composite_score || 0) * 100 },
  ];

  const topPatterns = Array.isArray(analysis.top_patterns) 
    ? analysis.top_patterns 
    : JSON.parse(analysis.top_patterns || "[]");

  const anomalySignals = Array.isArray(analysis.signals)
    ? analysis.signals
    : JSON.parse(analysis.signals || "[]");

  return (
    <div className="rounded-xl bg-card border border-border shadow-sm overflow-hidden flex flex-col h-full">
      <div className="p-4 border-b border-border flex items-center justify-between bg-secondary/20">
        <div className="flex items-center gap-2">
          <Fingerprint className="h-4 w-4 text-emerald-500 dark:text-emerald-400" />
          <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground dark:text-zinc-300">LogAI Intelligence</h2>
        </div>
        <div className={cn(
          "px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-tighter",
          analysis.anomaly_detected ? "bg-rose-500/10 text-rose-600 dark:text-rose-400" : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
        )}>
          {analysis.anomaly_detected ? "Anomaly Detected" : "Nominal State"}
        </div>
      </div>

      <div className="p-4 space-y-6 flex-1 overflow-y-auto scrollbar-thin">
        {/* Radar Map & Trend Area Graph */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
          <div className="h-[220px] w-full flex flex-col">
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest mb-4">Anomaly Score Trend</p>
            <div className="flex-1">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={analysisHistory || []} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={resolvedTheme === 'dark' ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)"} />
                  <XAxis 
                    dataKey="analyzed_at" 
                    hide 
                  />
                  <YAxis 
                    domain={[0, 1]} 
                    tick={{ fontSize: 9, fill: 'var(--muted-foreground)' }} 
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: resolvedTheme === 'dark' ? '#09090b' : '#fff',
                      border: '1px solid var(--border)',
                      fontSize: '10px',
                      borderRadius: '8px'
                    }} 
                  />
                  <Area 
                    type="monotone" 
                    dataKey="composite_score" 
                    stroke="#10b981" 
                    strokeWidth={2}
                    fillOpacity={1} 
                    fill="url(#colorScore)" 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="h-[200px] w-full">
             <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                <PolarGrid stroke={resolvedTheme === 'dark' ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.1)"} />
                <PolarAngleAxis 
                  dataKey="subject" 
                  tick={{ fill: resolvedTheme === 'dark' ? "rgba(255,255,255,0.5)" : "rgba(0,0,0,0.6)", fontSize: 10, fontWeight: 600 }} 
                />
                <Radar name="Score" dataKey="A" stroke="#10b981" fill="#10b981" fillOpacity={0.2} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="w-full space-y-4">
          <div className="bg-secondary/40 p-3 rounded-xl border border-border shadow-sm">
            <div className="flex justify-between items-end mb-1.5">
              <p className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest">Composite Score</p>
              <span className="text-xs font-bold font-mono text-foreground">{(analysis.composite_score || 0).toFixed(2)}</span>
            </div>
            <div className="h-2 bg-zinc-200 dark:bg-zinc-800 rounded-full overflow-hidden">
              <div 
                className={cn(
                  "h-full transition-all duration-1000", 
                  analysis.composite_score > 0.7 ? "bg-rose-500" : analysis.composite_score > 0.4 ? "bg-amber-500" : "bg-emerald-500"
                )} 
                style={{ width: `${(analysis.composite_score || 0) * 100}%` }}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-xl bg-secondary/20 border border-border/50">
              <p className="text-[9px] uppercase font-bold text-muted-foreground mb-1">Error Rate</p>
              <p className="text-sm font-bold font-mono text-foreground">{(analysis.error_rate || 0).toFixed(2)}%</p>
            </div>
            <div className="p-3 rounded-xl bg-secondary/20 border border-border/50">
              <p className="text-[9px] uppercase font-bold text-muted-foreground mb-1">Semantic</p>
              <p className="text-sm font-bold font-mono text-foreground">{(analysis.semantic_score || 0).toFixed(2)}</p>
            </div>
          </div>
        </div>

        {/* Anomaly Signals */}
        {anomalySignals.length > 0 && (
          <div className="space-y-3 pt-2 border-t border-border/50">
            <div className="flex items-center gap-2">
              <Waves className="h-4 w-4 text-rose-500 dark:text-rose-400" />
              <h3 className="text-[10px] font-bold text-foreground/80 uppercase tracking-widest">Diagnostic Signals</h3>
            </div>
            <div className="space-y-2">
              {anomalySignals.slice(0, 3).map((sig: any, i: number) => (
                <div key={i} className="bg-rose-500/5 dark:bg-rose-500/10 border border-rose-500/10 dark:border-rose-500/20 p-3 rounded-xl flex items-start gap-3 group transition-colors hover:bg-rose-500/10 dark:hover:bg-rose-500/15">
                  <AlertCircle className="h-4 w-4 text-rose-600 dark:text-rose-400 mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] text-rose-900 dark:text-rose-100/90 leading-relaxed font-mono break-all line-clamp-2">{sig.message || sig}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-[9px] text-rose-700/70 dark:text-rose-400/50 uppercase font-bold tracking-tighter bg-rose-500/10 px-1.5 py-0.5 rounded">Event Signal</span>
                      <span className="text-[9px] text-muted-foreground dark:text-zinc-500 font-mono">{(sig.timestamp || analysis.analyzed_at).slice(11, 19)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Frequent Patterns */}
        <div className="pb-4">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="h-3.5 w-3.5 text-zinc-500" />
            <h3 className="text-[10px] font-bold text-muted-foreground dark:text-zinc-500 uppercase tracking-widest">Pattern Discovery</h3>
          </div>
          <div className="space-y-1.5 max-h-[140px] overflow-y-auto pr-1 scrollbar-thin">
            {topPatterns.slice(0, 6).map((p: any, i: number) => (
              <div key={i} className="flex items-center justify-between gap-3 text-[10px] font-mono text-foreground/80 dark:text-zinc-300 bg-secondary/30 p-1.5 rounded border border-border/50 group hover:border-emerald-500/30 transition-colors">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <div className="w-1 h-1 rounded-full bg-emerald-500/50 group-hover:scale-150 transition-all" />
                  <span className="truncate">{p.pattern || p.template}</span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                   <span className="text-zinc-500 text-[8px] uppercase">Hits:</span>
                   <span className="text-emerald-600 dark:text-emerald-400/70 font-bold">{p.count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Meta */}
        <div className="py-2 border-t border-border/40 flex items-center justify-between">
           <p className="text-[8px] text-muted-foreground/50 uppercase font-bold tracking-widest">LogAI v1.2 Engine</p>
           <p className="text-[8px] text-muted-foreground/50 font-mono">Last analysis: {format(new Date(analysis.analyzed_at), "HH:mm:ss")}</p>
        </div>
      </div>
    </div>
  );
}

function AgentRunsSection({ monitorId }: { monitorId: string }) {
  const { data: runs, isLoading } = useQuery({
    queryKey: ["agentRuns", monitorId],
    queryFn: () => api.getAgentRuns(monitorId),
    refetchInterval: 5_000,
  });

  const { data: latestAnalysis } = useQuery({
    queryKey: ["monitorAnalysis", monitorId],
    queryFn: () => api.getMonitorAnalysis(monitorId),
  });

  const triggerMutation = useMutation({
    mutationFn: () => api.triggerAgentRun(monitorId, { 
      analysis: latestAnalysis,
      trace_id: `manual-${Date.now()}`
    }),
    onSuccess: () => toast.success("Agent triggered with LogAI context!"),
    onError: () => toast.error("Failed to trigger agent."),
  });

  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-sm flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-blue-500 dark:text-blue-400" />
          <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground dark:text-zinc-300">Agent Activity</h2>
        </div>
        <button 
          onClick={() => triggerMutation.mutate()}
          disabled={triggerMutation.isPending}
          className="text-[9px] font-bold bg-blue-500/10 text-blue-600 dark:text-blue-400 px-2 py-1 rounded hover:bg-blue-500/20 transition-colors border border-blue-500/20"
        >
          {triggerMutation.isPending ? "TRIGGERING..." : "TRIGGER RCA"}
        </button>
      </div>
      <div className="space-y-2 flex-1 overflow-y-auto max-h-[300px] scrollbar-thin">
        {isLoading || !runs || runs.length === 0 ? (
          <div className="text-[10px] text-muted-foreground italic p-4 text-center">No recent activity</div>
        ) : (
          runs.map((run: any) => (
            <div key={run.id} className="p-2.5 rounded-lg bg-secondary/40 border border-border flex items-center justify-between gap-3">
              <div className="flex-1 overflow-hidden">
                <div className="flex items-center gap-2 mb-1">
                  <span className={cn(
                    "w-1.5 h-1.5 rounded-full",
                    run.status === "COMPLETED" ? "bg-emerald-500" : "bg-blue-500 animate-pulse"
                  )}></span>
                  <p className="text-[10px] font-bold truncate text-foreground dark:text-zinc-100">{run.status}</p>
                </div>
                <p className="text-[9px] text-muted-foreground font-mono truncate">{run.trace_id}</p>
              </div>
              <div className="text-[9px] text-muted-foreground font-mono">{format(new Date(run.created_at), "HH:mm")}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function LiveLogsStream({ monitorId, onFullscreen }: { monitorId: string; onFullscreen: () => void }) {
  const { data: logs, isLoading } = useQuery({
    queryKey: ["monitorLogs", monitorId],
    queryFn: () => api.getMonitorLogs(monitorId),
    refetchInterval: 2_000,
  });

  return (
    <div className="rounded-xl border border-border bg-zinc-950 dark:bg-black shadow-lg overflow-hidden flex flex-col h-[400px]">
      <div className="bg-zinc-100 dark:bg-zinc-900 px-4 py-2 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5 mr-2">
            <div className="w-2.5 h-2.5 rounded-full bg-rose-500/20"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-amber-500/20"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/20"></div>
          </div>
          <Terminal className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-[10px] font-bold text-muted-foreground font-mono uppercase tracking-widest">Live Stream</span>
        </div>
        <button onClick={onFullscreen} className="text-muted-foreground hover:text-foreground transition-colors">
          <Maximize2 className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="flex-1 p-4 overflow-y-auto font-mono text-[10px] leading-relaxed space-y-1 bg-zinc-950 dark:bg-[#050505] scrollbar-thin">
        {isLoading ? (
          <div className="text-zinc-700 animate-pulse">Initializing log stream...</div>
        ) : !logs || logs.length === 0 ? (
          <div className="text-zinc-700 italic">Waiting for logs...</div>
        ) : (
          logs.map((log: any, i: number) => (
            <div key={i} className="flex gap-4 group">
              <span className="text-zinc-500 dark:text-zinc-400 shrink-0 select-none w-16 font-mono">{format(new Date(log.timestamp), "HH:mm:ss")}</span>
              <span className={cn(
                "font-bold shrink-0 w-12",
                log.level === "ERROR" ? "text-rose-500" :
                log.level === "WARN" ? "text-amber-500" : "text-zinc-600"
              )}>[{log.level}]</span>
              <span className="text-zinc-100 break-all">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function LiveLogsStreamFullscreen({ monitorId, onClose }: { monitorId: string; onClose: () => void }) {
  const { data: logs, isLoading } = useQuery({
    queryKey: ["monitorLogs", monitorId],
    queryFn: () => api.getMonitorLogs(monitorId, 200),
    refetchInterval: 5_000,
  });

  return (
    <div className="fixed inset-0 bg-zinc-950 dark:bg-black z-50 flex flex-col p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Terminal className="h-6 w-6 text-emerald-500" />
          <h2 className="text-lg font-bold uppercase tracking-widest text-zinc-300 dark:text-zinc-100">Live Log Stream (Fullscreen)</h2>
        </div>
        <button onClick={onClose} className="p-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 transition-colors">
          <X className="h-6 w-6 text-zinc-400" />
        </button>
      </div>
      <div className="flex-1 rounded-xl bg-[#050505] border border-zinc-800 p-6 overflow-y-auto font-mono text-xs leading-relaxed space-y-1 scrollbar-thin">
        {isLoading ? (
          <div className="text-zinc-700 animate-pulse">Initializing log stream...</div>
        ) : !logs || logs.length === 0 ? (
          <div className="text-zinc-700 italic">Waiting for logs...</div>
        ) : (
          logs.map((log: any, i: number) => (
            <div key={i} className="flex gap-6 group">
              <span className="text-zinc-500 dark:text-zinc-400 shrink-0 select-none font-mono">{format(new Date(log.timestamp), "yyyy-MM-dd HH:mm:ss")}</span>
              <span className={cn(
                "font-bold shrink-0",
                log.level === "ERROR" ? "text-rose-500" :
                log.level === "WARN" ? "text-amber-500" : "text-zinc-500"
              )}>[{log.level}]</span>
              <span className="text-zinc-100 break-all">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function NotificationChannel({
  type,
  name,
  domain,
  monitor,
  onSave,
}: {
  type: string;
  name: string;
  domain: string;
  monitor: any;
  onSave: (data: any) => void;
}) {
  const config = (monitor.notifications || []).find((n: any) => n.type === type);
  const enabled = config?.enabled ?? false;
  const logoUrl = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;

  return (
    <Dialog>
      <DialogTrigger asChild>
        <button className="flex w-full items-center justify-between rounded-lg border border-border bg-secondary/20 p-2 hover:bg-secondary/40 transition-colors group">
          <div className="flex items-center gap-3">
            <img src={logoUrl} alt={name} className="h-5 w-5 grayscale group-hover:grayscale-0 transition-all opacity-50 group-hover:opacity-100" />
            <div className="text-left">
              <p className="text-[10px] font-bold text-muted-foreground dark:text-zinc-300">{name}</p>
              <p className="text-[8px] text-muted-foreground/60 truncate max-w-[80px]">{config?.destination || "DISCONNECTED"}</p>
            </div>
          </div>
          {enabled && <div className="h-1 w-1 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />}
        </button>
      </DialogTrigger>
      <DialogContent className="glass border-primary/20 sm:max-w-[400px]">
        <ChannelConfigModal type={type} name={name} initialData={config} onSave={onSave} />
      </DialogContent>
    </Dialog>
  );
}

function ChannelConfigModal({
  type,
  name,
  initialData,
  onSave,
}: {
  type: string;
  name: string;
  initialData: any;
  onSave: (data: any) => void;
}) {
  const [dest, setDest] = useState(initialData?.destination || "");
  const [secret, setSecret] = useState(initialData?.bot_token || "");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  return (
    <div className="space-y-6 pt-4">
      <DialogHeader>
        <DialogTitle className="text-foreground dark:text-zinc-100">Configure {name}</DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        <div className="space-y-2">
          <Label className="text-xs uppercase tracking-widest text-muted-foreground">Destination / ID</Label>
          <Input
            className="bg-secondary border-border text-foreground"
            value={dest}
            onChange={(e) => setDest(e.target.value)}
            placeholder={type === "EMAIL" ? "alerts@company.com" : "Topic / Webhook / Channel"}
          />
        </div>
        {type === "SLACK" && (
          <div className="space-y-2">
            <Label className="text-xs uppercase tracking-widest text-muted-foreground">Bot Token</Label>
            <Input
              type="password"
              className="bg-secondary border-border text-foreground"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder="xoxb-..."
            />
          </div>
        )}
      </div>
      {testResult && (
        <div className={cn(
          "p-3 rounded-lg text-[10px] font-mono",
          testResult.success ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20" : "bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20"
        )}>
          {testResult.message}
        </div>
      )}
      <DialogFooter className="flex-col sm:flex-row gap-2">
        <button
          onClick={async () => {
            setTesting(true);
            try {
              const res = await api.testNotification(type, { destination: dest, bot_token: secret });
              setTestResult(res);
            } catch (e) {
              setTestResult({ success: false, message: "Connection failed" });
            } finally {
              setTesting(false);
            }
          }}
          disabled={!dest || testing}
          className="flex-1 rounded-lg border border-border bg-secondary py-2.5 text-xs font-bold text-muted-foreground hover:bg-secondary/60 disabled:opacity-50"
        >
          {testing ? "TESTING..." : "TEST CONNECTION"}
        </button>
        <button
          onClick={() => onSave({ destination: dest, bot_token: secret })}
          className="flex-1 rounded-lg bg-indigo-500 py-2.5 text-xs font-bold text-white hover:bg-indigo-600 shadow-lg shadow-indigo-500/20"
        >
          SAVE CONFIG
        </button>
      </DialogFooter>
    </div>
  );
}
