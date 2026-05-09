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
} from "lucide-react";
import { api } from "@/api/client";
import { CopyButton } from "@/components/morphic/CopyButton";
import { EmptyState, ErrorState, SkeletonCard } from "@/components/morphic/states";
import { AppShell } from "@/components/morphic/AppShell";
import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
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

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["monitor", monitorId],
    queryFn: () => api.getMonitor(monitorId),
    refetchInterval: 10_000,
  });

  const { data: metricsData = [], isLoading: metricsLoading } = useQuery({
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

  const updateMutation = useMutation({
    mutationFn: (updates: any) => api.updateMonitor(monitorId, updates),
    onSuccess: (_, variables) => {
      console.log("Update successful, variables:", variables);
      queryClient.invalidateQueries({ queryKey: ["monitor", monitorId] });
      if (variables.notifications) {
        console.log("Showing notification success toast");
        toast.success("Notification settings saved");
      } else {
        toast.success("Monitor updated");
      }
    },
    onError: (error) => {
      console.error("Update failed:", error);
      toast.error("Failed to update monitor");
    },
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
  }[monitor.status];

  const statusColor = {
    UP: "text-success",
    DOWN: "text-destructive",
    DEGRADED: "text-warning",
  }[monitor.status];

  return (
    <AppShell>
      <div className="space-y-8">
        {/* Header Section */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-primary/10 via-primary/5 to-transparent border border-primary/20">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/5 via-purple-500/5 to-pink-500/5"></div>
          <div className="relative p-8">
            <div className="flex items-start justify-between">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "w-3 h-3 rounded-full animate-pulse",
                    monitor.status === "UP" ? "bg-emerald-500" :
                    monitor.status === "DOWN" ? "bg-rose-500" : "bg-amber-500"
                  )}></div>
                  <h1 className="text-4xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                    {monitor.name}
                  </h1>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-background/50 border border-border/50 font-mono">
                    <Globe className="h-3 w-3" />
                    {monitor.url}
                    <ExternalLink className="h-3 w-3 opacity-50" />
                  </div>
                  <div className={cn(
                    "flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-semibold border",
                    monitor.status === "UP" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                    monitor.status === "DOWN" ? "bg-rose-500/10 text-rose-400 border-rose-500/20" :
                    "bg-amber-500/10 text-amber-400 border-amber-500/20"
                  )}>
                    <StatusIcon className="h-4 w-4" />
                    {monitor.status}
                  </div>
                </div>
              </div>
              
              {/* Stats Cards */}
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-background/50 backdrop-blur-sm rounded-2xl p-4 border border-border/50">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                    <Activity className="h-3 w-3" />
                    Latency
                  </div>
                  <p className="text-2xl font-bold">{monitor.latency_ms}<span className="text-sm text-muted-foreground ml-1">ms</span></p>
                </div>
                <div className="bg-background/50 backdrop-blur-sm rounded-2xl p-4 border border-border/50">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Uptime
                  </div>
                  <p className="text-2xl font-bold">{monitor.uptime_pct}<span className="text-sm text-muted-foreground ml-1">%</span></p>
                </div>
                <div className="bg-background/50 backdrop-blur-sm rounded-2xl p-4 border border-border/50">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                    <Shield className="h-3 w-3" />
                    Auth
                  </div>
                  <p className="text-2xl font-bold uppercase">{monitor.auth_type}</p>
                </div>
              </div>
            </div>
            
            {monitor.logs_url && (
              <div className="mt-6 flex items-center justify-between rounded-2xl bg-background/30 backdrop-blur-sm border border-primary/20 p-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Terminal className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold">Log Source</h4>
                    <p className="text-xs text-muted-foreground font-mono">{monitor.logs_url}</p>
                  </div>
                </div>
                <a
                  href={monitor.logs_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 rounded-lg bg-primary/10 hover:bg-primary/20 px-4 py-2 text-sm font-medium text-primary transition-colors"
                >
                  <ExternalLink className="h-4 w-4" />
                  View
                </a>
              </div>
            )}
          </div>
        </div>

        {/* Main Grid Layout */}
        <div className="grid gap-8 lg:grid-cols-3">
          {/* Left Column - Main Content */}
          <div className="lg:col-span-2 space-y-8">
            {/* Performance Chart */}
            <div className="group relative overflow-hidden rounded-3xl bg-card border border-border/50 shadow-lg hover:shadow-xl transition-all duration-300">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <div className="relative p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-xl font-semibold">Performance Metrics</h2>
                    <p className="text-sm text-muted-foreground">Real-time latency and uptime tracking</p>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-medium">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                    Live
                  </div>
                </div>
                
                <div className="h-[320px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={metricsData}>
                      <defs>
                        <linearGradient id="colorLat" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.03)" />
                      <XAxis
                        dataKey="timestamp"
                        tickFormatter={(val) => format(new Date(val), "HH:mm")}
                        fontSize={11}
                        stroke="hsl(var(--muted-foreground))"
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        fontSize={11}
                        stroke="hsl(var(--muted-foreground))"
                        axisLine={false}
                        tickLine={false}
                        unit="ms"
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "rgba(0,0,0,0.9)",
                          border: "1px solid hsl(var(--border))",
                          borderRadius: "12px",
                        }}
                        labelStyle={{ color: "hsl(var(--muted-foreground))", fontSize: "11px" }}
                        itemStyle={{ color: "hsl(var(--primary))", fontSize: "12px", fontWeight: "600" }}
                        labelFormatter={(val) => format(new Date(val), "MMM d, HH:mm:ss")}
                      />
                      <Area
                        type="monotone"
                        dataKey="latency"
                        stroke="hsl(var(--primary))"
                        fillOpacity={1}
                        fill="url(#colorLat)"
                        strokeWidth={2}
                        isAnimationActive={false}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Live Logs */}
            <LiveLogsStream monitorId={monitorId} onFullscreen={() => setIsFullscreenLogs(true)} />
            
            {/* Agent Runs */}
            <AgentRunsSection monitorId={monitorId} />

            {/* Workflows */}
            <div className="group relative overflow-hidden rounded-3xl bg-card border border-border/50 shadow-lg hover:shadow-xl transition-all duration-300">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <div className="relative p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center">
                    <Zap className="h-5 w-5 text-purple-400" />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold">Self-Healing Workflows</h2>
                    <p className="text-sm text-muted-foreground">Automated remediation with n8n</p>
                  </div>
                </div>
                
                <div className="space-y-3">
                  {monitor.workflows.map((wf) => (
                    <div
                      key={wf.id}
                      className="flex items-center justify-between rounded-2xl bg-secondary/30 border border-border/50 p-4 hover:bg-secondary/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center">
                          <Bot className="h-4 w-4 text-purple-400" />
                        </div>
                        <div>
                          <p className="font-medium">{wf.name}</p>
                          <p className="text-xs text-muted-foreground font-mono">{wf.url}</p>
                        </div>
                      </div>
                      <Switch
                        checked={wf.enabled}
                        onCheckedChange={(enabled) => {
                          const newWfs = monitor.workflows.map((w) =>
                            w.id === wf.id ? { ...w, enabled } : w,
                          );
                          updateMutation.mutate({ workflows: newWfs });
                        }}
                      />
                    </div>
                  ))}
                  <ConnectN8nModal
                    onConnect={(data) => {
                      toast.success(`Connected to n8n at ${data.url}`);
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Sidebar */}
          <div className="space-y-8">
            {/* Alert Channels */}
            <div className="group relative overflow-hidden rounded-3xl bg-card border border-border/50 shadow-lg hover:shadow-xl transition-all duration-300">
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <div className="relative p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
                    <Bell className="h-5 w-5 text-blue-400" />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold">Alert Channels</h2>
                    <p className="text-sm text-muted-foreground">Real-time notifications</p>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <NotificationChannel
                    type="NTFY"
                    name="ntfy.sh"
                    domain="ntfy.sh"
                    monitor={monitor}
                    onSave={(data) => {
                      const existingNotifications = monitor.notifications || [];
                      const otherNotifications = existingNotifications.filter((n: any) => n.type !== "NTFY");
                      const ntfyNotification = { type: "NTFY", ...data, enabled: true };
                      const news = [...otherNotifications, ntfyNotification];
                      updateMutation.mutate({ notifications: news });
                    }}
                  />
                  <NotificationChannel
                    type="EMAIL"
                    name="Email"
                    domain="gmail.com"
                    monitor={monitor}
                    onSave={(data) => {
                      const existingNotifications = monitor.notifications || [];
                      const otherNotifications = existingNotifications.filter((n: any) => n.type !== "EMAIL");
                      const emailNotification = { type: "EMAIL", ...data, enabled: true };
                      const news = [...otherNotifications, emailNotification];
                      updateMutation.mutate({ notifications: news });
                    }}
                  />
                  <NotificationChannel
                    type="TELEGRAM"
                    name="Telegram"
                    domain="t.me"
                    monitor={monitor}
                    onSave={(data) => {
                      const existingNotifications = monitor.notifications || [];
                      const otherNotifications = existingNotifications.filter((n: any) => n.type !== "TELEGRAM");
                      const telegramNotification = { type: "TELEGRAM", ...data, enabled: true };
                      const news = [...otherNotifications, telegramNotification];
                      updateMutation.mutate({ notifications: news });
                    }}
                  />
                  <NotificationChannel
                    type="SLACK"
                    name="Slack"
                    domain="slack.com"
                    monitor={monitor}
                    onSave={(data) => {
                      const existingNotifications = monitor.notifications || [];
                      const otherNotifications = existingNotifications.filter((n: any) => n.type !== "SLACK");
                      const slackNotification = { type: "SLACK", ...data, enabled: true };
                      const news = [...otherNotifications, slackNotification];
                      updateMutation.mutate({ notifications: news });
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Settings */}
            <div className="group relative overflow-hidden rounded-3xl bg-card border border-border/50 shadow-lg hover:shadow-xl transition-all duration-300">
              <div className="absolute inset-0 bg-gradient-to-br from-amber-500/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <div className="relative p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center">
                    <Settings className="h-5 w-5 text-amber-400" />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold">Settings</h2>
                    <p className="text-sm text-muted-foreground">Monitor configuration</p>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 rounded-xl bg-secondary/30">
                    <div>
                      <p className="font-medium">Log Tail</p>
                      <p className="text-xs text-muted-foreground">
                        {monitor.log_tail_enabled ? "Enabled" : "Disabled"}
                      </p>
                    </div>
                    <Switch
                      checked={monitor.log_tail_enabled}
                      onCheckedChange={(enabled) => {
                        updateMutation.mutate({ log_tail_enabled: enabled });
                      }}
                    />
                  </div>
                  
                  <div className="flex items-center justify-between p-3 rounded-xl bg-secondary/30">
                    <div>
                      <p className="font-medium">Agent Status</p>
                      <p className="text-xs text-muted-foreground">
                        {monitor.agent_run_status || "IDLE"}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {monitor.agent_run_status === "TRIGGERED" && (
                        <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
                      )}
                      {monitor.agent_run_status === "PR_CREATED" && (
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      )}
                      <span className="text-xs font-mono">{monitor.agent_run_status || "IDLE"}</span>
                    </div>
                  </div>
                  
                  <button
                    onClick={() => deleteMutation.mutate()}
                    className="w-full mt-4 flex items-center justify-center gap-2 rounded-2xl border border-destructive/20 bg-destructive/5 hover:bg-destructive/10 px-4 py-3 text-sm font-medium text-destructive transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete Monitor
                  </button>
                </div>
              </div>
            </div>
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
  const config = monitor.notifications.find((n: any) => n.type === type);
  const enabled = config?.enabled ?? false;
  const logoUrl = `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;

  return (
    <Dialog>
      <DialogTrigger asChild>
        <button className="flex w-full items-center justify-between rounded-xl border border-border bg-secondary/10 p-3 transition hover:bg-secondary/20 group">
          <div className="flex items-center gap-3 text-left">
            <div className="h-10 w-10 overflow-hidden">
              <img
                src={logoUrl}
                alt={name}
                className="h-full w-full object-contain transition-transform group-hover:scale-110"
              />
            </div>
            <div>
              <p className="text-sm font-medium group-hover:text-primary transition-colors">
                {name}
              </p>
              <p className="text-[10px] text-muted-foreground truncate max-w-[120px]">
                {config?.destination || "Not configured"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {enabled && (
              <div className="h-1.5 w-1.5 rounded-full bg-success shadow-[0_0_8px_var(--success)]" />
            )}
            <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </button>
      </DialogTrigger>
      <DialogContent className="glass border-primary/20 sm:max-w-[425px]">
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
  const [secret, setSecret] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  return (
    <div className="space-y-4 pt-4">
      <DialogHeader>
        <DialogTitle>Configure {name}</DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        <div className="space-y-1.5">
          <Label>
            {type === "EMAIL"
              ? "Email Address"
              : type === "NTFY"
                ? "Topic Name"
                : "Webhook URL / ID"}
          </Label>
          <Input
            value={dest}
            onChange={(e) => {
              const value = e.target.value;
              if (type === "NTFY") {
                // Remove spaces and convert to lowercase for NTFY topics
                setDest(value.replace(/\s+/g, '').toLowerCase());
              } else {
                setDest(value);
              }
            }}
            placeholder={
              type === "EMAIL" ? "alerts@company.com" :
              type === "NTFY" ? "morphic-alerts" :
              type === "TELEGRAM" ? "123456789 or @channel" :
              type === "SLACK" ? "#alerts" :
              "https://..."
            }
          />
          {type === "NTFY" && (
            <p className="text-xs text-muted-foreground">
              Enter an NTFY topic name. Create one at <a href="https://ntfy.sh" target="_blank" className="text-primary hover:underline">ntfy.sh</a>
            </p>
          )}
          {type === "EMAIL" && (
            <p className="text-xs text-muted-foreground">
              Email address to receive alert notifications
            </p>
          )}
          {type === "TELEGRAM" && (
            <p className="text-xs text-muted-foreground">
              Chat ID or username. Create a bot with <a href="https://t.me/BotFather" target="_blank" className="text-primary hover:underline">@BotFather</a>
            </p>
          )}
          {type === "SLACK" && (
            <p className="text-xs text-muted-foreground">
              Channel name (e.g., #alerts). Create a webhook in Slack settings
            </p>
          )}
        </div>
        {(type === "SLACK" || type === "TELEGRAM") && (
          <div className="space-y-1.5">
            <Label>{type === "SLACK" ? "Bot Token (Optional)" : "Bot API Token"}</Label>
            <Input
              type="password"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder="xoxb-..."
            />
          </div>
        )}
      </div>
      {testResult && (
        <div className={cn(
          "p-3 rounded-lg text-sm",
          testResult.success ? "bg-success/10 text-success border border-success/20" : "bg-destructive/10 text-destructive border border-destructive/20"
        )}>
          {testResult.message}
        </div>
      )}
      <DialogFooter className="gap-2">
        <button
          onClick={async () => {
            if (!dest) return;
            setTesting(true);
            setTestResult(null);
            
            try {
              const config: any = { destination: dest, enabled: true };
              if (secret) config.bot_token = secret;
              
              const result = await api.testNotification(type, config);
              setTestResult(result);
            } catch (error) {
              let message = "Test failed";
              if (type === "TELEGRAM" && !secret) {
                message = "Bot token required for Telegram";
              } else if (type === "NTFY" && dest.includes(' ')) {
                message = "Topic name cannot contain spaces";
              } else if (type === "EMAIL" && !dest.includes('@')) {
                message = "Invalid email address";
              }
              setTestResult({ success: false, message });
            } finally {
              setTesting(false);
            }
          }}
          disabled={!dest || testing}
          className="flex-1 rounded-md border border-border bg-secondary/60 py-2 text-sm font-medium transition hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {testing ? "Testing..." : "Test Notification"}
        </button>
        <button
          onClick={() => {
              const data: any = { destination: dest };
              if (secret) data.bot_token = secret;
              onSave(data);
            }}
          className="flex-1 rounded-md bg-primary py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          Save Configuration
        </button>
      </DialogFooter>
    </div>
  );
}

function ConnectN8nModal({ onConnect }: { onConnect: (data: any) => void }) {
  const [url, setUrl] = useState("https://n8n.company.com");
  const [apiKey, setApiKey] = useState("");

  return (
    <Dialog>
      <DialogTrigger asChild>
        <button className="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-border p-3 text-sm text-muted-foreground transition hover:border-primary/50 hover:bg-primary/5">
          <Plus className="h-4 w-4" />
          Connect n8n Instance
        </button>
      </DialogTrigger>
      <DialogContent className="glass border-primary/20">
        <div className="space-y-4 pt-4">
          <DialogHeader>
            <DialogTitle>Connect n8n Instance</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>n8n Host URL</Label>
              <Input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://n8n.morphic.dev"
              />
            </div>
            <div className="space-y-1.5">
              <Label>API Key</Label>
              <Input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="n8n_api_..."
              />
            </div>
          </div>
          <DialogFooter>
            <button
              onClick={() => onConnect({ url, apiKey })}
              className="w-full rounded-md bg-primary py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
            >
              Verify & Connect
            </button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function EditMonitorForm({ monitor, onSuccess }: { monitor: any; onSuccess: () => void }) {
  const [name, setName] = useState(monitor.name);
  const [url, setUrl] = useState(monitor.url);
  const [logsUrl, setLogsUrl] = useState(monitor.logs_url || "");
  const [authType, setAuthType] = useState(monitor.auth_type);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await api.updateMonitor(monitor.id, { name, url, logs_url: logsUrl, auth_type: authType });
      onSuccess();
    } catch (err) {
      toast.error("Failed to update monitor");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 pt-4">
      <DialogHeader>
        <DialogTitle>Edit Monitor Settings</DialogTitle>
      </DialogHeader>
      <div className="space-y-3">
        <div className="space-y-1.5">
          <Label htmlFor="edit-name">Display Name</Label>
          <Input id="edit-name" value={name} onChange={(e) => setName(e.target.value)} required />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="edit-url">Application URL</Label>
          <Input
            id="edit-url"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="edit-logs-url">Logs Source URL (Optional)</Label>
          <Input
            id="edit-logs-url"
            type="url"
            value={logsUrl}
            onChange={(e) => setLogsUrl(e.target.value)}
            placeholder="https://..."
          />
        </div>
        <div className="space-y-1.5">
          <Label>Authentication</Label>
          <Select value={authType} onValueChange={(v: any) => setAuthType(v)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="NONE">None</SelectItem>
              <SelectItem value="BEARER">Bearer Token</SelectItem>
              <SelectItem value="BASIC">Basic Auth</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <DialogFooter className="pt-2">
        <button
          type="submit"
          disabled={isLoading}
          className="w-full rounded-md bg-primary py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-50"
        >
          {isLoading ? "Saving..." : "Save Changes"}
        </button>
      </DialogFooter>
    </form>
  );
}

function LiveLogsStream({ monitorId, onFullscreen }: { monitorId: string; onFullscreen: () => void }) {
  const { data: logs, isLoading } = useQuery({
    queryKey: ["monitorLogs", monitorId],
    queryFn: () => api.getMonitorLogs(monitorId, 50),
    refetchInterval: 5_000,
  });

  const exportLogs = () => {
    if (!logs || logs.length === 0) return;
    
    const logText = logs.map((log: any) => {
      const timestamp = new Date(log.timestamp || log.fetched_at).toISOString();
      const level = log.level || 'INFO';
      const service = log.service || '';
      const traceId = log.trace_id || '';
      const errorType = log.error_type && log.error_type !== "NONE" ? `[${log.error_type}]` : '';
      const message = log.message || '';
      
      return `[${timestamp}] ${level} ${service ? `[${service}]` : ''} ${traceId ? `#${traceId}` : ''} ${errorType} ${message}`.trim();
    }).join('\n');
    
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `monitor-${monitorId}-logs-${new Date().toISOString().slice(0, 19)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-border bg-card p-6 shadow-sm h-[300px] flex items-center justify-center">
        <div className="animate-pulse text-sm text-muted-foreground">Loading log stream...</div>
      </div>
    );
  }

  return (
    <>
      <div className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden flex flex-col">
        <div className="p-4 border-b border-border bg-secondary/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Terminal className="h-4 w-4 text-primary" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Live Log Stream</h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onFullscreen}
              className="p-1.5 rounded-md hover:bg-secondary/60 transition-colors"
              title="Fullscreen logs"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={exportLogs}
              disabled={!logs || logs.length === 0}
              className="p-1.5 rounded-md hover:bg-secondary/60 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="Export logs"
            >
              <Download className="h-3.5 w-3.5" />
            </button>
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
            </span>
            <span className="text-[10px] text-success font-bold uppercase tracking-widest">Tailing</span>
          </div>
        </div>
        
        <div className="p-4 bg-black/95 font-mono text-[11px] text-zinc-300 h-[300px] overflow-y-auto leading-relaxed scrollbar-thin scrollbar-thumb-white/10 flex flex-col-reverse">
          {!logs || logs.length === 0 ? (
            <div className="text-zinc-500 italic py-4">No logs available. Waiting for stream...</div>
          ) : (
            <div className="space-y-1">
              {logs.map((log: any, idx: number) => {
                const levelColor = 
                  log.level === "ERROR" ? "text-red-400" : 
                  log.level === "WARN" ? "text-yellow-400" : 
                  log.level === "INFO" ? "text-emerald-400" :
                  "text-zinc-400";
                  
                return (
                  <div key={log.id || idx} className="hover:bg-white/5 px-2 py-0.5 rounded break-all">
                    <span className="text-zinc-400 mr-2">[{new Date(log.timestamp || log.fetched_at).toLocaleTimeString()}]</span>
                    <span className={`font-bold mr-2 ${levelColor}`}>{log.level}</span>
                    {log.service && <span className="text-cyan-400 mr-2">[{log.service}]</span>}
                    {log.trace_id && <span className="text-violet-400 mr-2">#{log.trace_id.slice(0, 8)}</span>}
                    {log.error_type && log.error_type !== "NONE" && (
                      <span className="text-amber-400 mr-2">[{log.error_type}]</span>
                    )}
                    <span className="text-zinc-100">{log.message}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function LiveLogsStreamFullscreen({ monitorId, onClose }: { monitorId: string; onClose: () => void }) {
  const { data: logs, isLoading } = useQuery({
    queryKey: ["monitorLogs", monitorId],
    queryFn: () => api.getMonitorLogs(monitorId, 200), // More logs in fullscreen
    refetchInterval: 5_000,
  });

  const exportLogs = () => {
    if (!logs || logs.length === 0) return;
    
    const logText = logs.map((log: any) => {
      const timestamp = new Date(log.timestamp || log.fetched_at).toISOString();
      const level = log.level || 'INFO';
      const service = log.service || '';
      const traceId = log.trace_id || '';
      const errorType = log.error_type && log.error_type !== "NONE" ? `[${log.error_type}]` : '';
      const message = log.message || '';
      
      return `[${timestamp}] ${level} ${service ? `[${service}]` : ''} ${traceId ? `#${traceId}` : ''} ${errorType} ${message}`.trim();
    }).join('\n');
    
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `monitor-${monitorId}-logs-${new Date().toISOString().slice(0, 19)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black/95 z-50 flex items-center justify-center">
        <div className="animate-pulse text-sm text-muted-foreground">Loading log stream...</div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/95 z-50 flex flex-col">
      <div className="p-4 border-b border-border/20 bg-black/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Terminal className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold">Live Log Stream - Fullscreen</h2>
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
          </span>
          <span className="text-xs text-success font-bold uppercase tracking-widest">Tailing</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={exportLogs}
            disabled={!logs || logs.length === 0}
            className="px-3 py-1.5 rounded-md bg-secondary/80 hover:bg-secondary text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            Export
          </button>
          <button
            onClick={onClose}
            className="p-2 rounded-md hover:bg-secondary/80 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>
      
      <div className="flex-1 p-4 bg-black font-mono text-[12px] text-zinc-300 overflow-y-auto leading-relaxed scrollbar-thin scrollbar-thumb-white/10">
        {!logs || logs.length === 0 ? (
          <div className="text-zinc-500 italic py-8">No logs available. Waiting for stream...</div>
        ) : (
          <div className="space-y-1">
            {logs.map((log: any, idx: number) => {
              const levelColor = 
                log.level === "ERROR" ? "text-red-400" : 
                log.level === "WARN" ? "text-yellow-400" : 
                log.level === "INFO" ? "text-emerald-400" :
                "text-zinc-400";
                
              return (
                <div key={log.id || idx} className="hover:bg-white/5 px-2 py-1 rounded break-all">
                  <span className="text-zinc-400 mr-3">[{new Date(log.timestamp || log.fetched_at).toLocaleTimeString()}]</span>
                  <span className={`font-bold mr-3 ${levelColor}`}>{log.level}</span>
                  {log.service && <span className="text-cyan-400 mr-3">[{log.service}]</span>}
                  {log.trace_id && <span className="text-violet-400 mr-3">#{log.trace_id.slice(0, 8)}</span>}
                  {log.error_type && log.error_type !== "NONE" && (
                    <span className="text-amber-400 mr-3">[{log.error_type}]</span>
                  )}
                  <span className="text-zinc-100">{log.message}</span>
                </div>
              );
            })}
          </div>
        )}
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

  const triggerMutation = useMutation({
    mutationFn: () => api.triggerAgentRun(monitorId),
    onSuccess: () => toast.success("SRE Agent triggered manually!"),
    onError: () => toast.error("Failed to trigger agent."),
  });

  if (isLoading) return null;

  return (
    <div className="rounded-2xl border border-border bg-card shadow-sm">
      <div className="p-5 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-indigo-400" />
          <h2 className="text-lg font-semibold">Automated RCA & Remediation</h2>
        </div>
        <button
          onClick={() => triggerMutation.mutate()}
          disabled={triggerMutation.isPending}
          className="px-3 py-1.5 text-xs font-semibold bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 rounded-md border border-indigo-500/20 transition-all flex items-center gap-1.5"
        >
          <Zap className="h-3.5 w-3.5" />
          Trigger Agent
        </button>
      </div>
      
      <div className="p-5 space-y-4 max-h-[400px] overflow-y-auto">
        {!runs || runs.length === 0 ? (
          <div className="text-center py-8 text-sm text-muted-foreground border border-dashed rounded-xl">
            No agent runs triggered yet.
          </div>
        ) : (
          runs.map((run: any) => (
            <div key={run.id} className="border border-border bg-secondary/10 rounded-xl p-4 transition-all hover:border-primary/30">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className={cn(
                    "px-2 py-0.5 rounded-full text-[10px] font-bold tracking-widest uppercase border",
                    run.status === "COMPLETED" ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" :
                    run.status === "PR_CREATED" ? "bg-blue-500/10 text-blue-500 border-blue-500/20" :
                    run.status === "FAILED" ? "bg-red-500/10 text-red-500 border-red-500/20" :
                    "bg-amber-500/10 text-amber-500 border-amber-500/20 animate-pulse"
                  )}>
                    {run.status.replace("_", " ")}
                  </div>
                  <span className="text-xs text-muted-foreground font-mono">
                    {new Date(run.triggered_at).toLocaleString()}
                  </span>
                </div>
                {run.github_pr_url && (
                  <a href={run.github_pr_url} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 text-xs font-semibold text-blue-400 hover:text-blue-300 bg-blue-400/10 px-2.5 py-1 rounded-md transition-colors">
                    <GitPullRequest className="h-3.5 w-3.5" />
                    View PR #{run.github_pr_number}
                  </a>
                )}
              </div>
              
              <div className="space-y-3">
                {run.rca_summary && (
                  <div className="text-sm bg-black/20 p-3 rounded-lg border border-white/5 flex items-start gap-3">
                    <Search className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                    <p className="text-zinc-300 leading-relaxed font-mono text-xs">{run.rca_summary}</p>
                  </div>
                )}
                
                {run.rca_md && (
                  <Dialog>
                    <DialogTrigger asChild>
                      <button className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground hover:text-primary transition-colors">
                        <FileText className="h-3.5 w-3.5" />
                        View Full RCA Report
                      </button>
                    </DialogTrigger>
                    <DialogContent className="max-w-3xl glass max-h-[85vh] overflow-y-auto">
                      <DialogHeader>
                        <DialogTitle>Root Cause Analysis</DialogTitle>
                      </DialogHeader>
                      <div className="prose prose-invert prose-sm max-w-none mt-4 font-mono">
                        <pre className="whitespace-pre-wrap bg-black/50 p-4 rounded-xl border border-white/10 text-zinc-300 text-[11px] leading-relaxed">
                          {run.rca_md}
                        </pre>
                      </div>
                    </DialogContent>
                  </Dialog>
                )}
                
                {run.error_message && (
                  <div className="text-xs text-red-400 bg-red-400/10 p-2.5 rounded-lg border border-red-400/20 font-mono">
                    {run.error_message}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
