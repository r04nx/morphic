import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  X,
  Shield,
  Globe,
  Zap,
  Database,
  Bell,
  Cpu,
  ExternalLink,
  RefreshCw,
  Save,
  Eye,
  EyeOff,
} from "lucide-react";
import { api, isMockMode } from "@/api/client";
import { AppShell, HealthIndicator } from "@/components/morphic/AppShell";
import { SkeletonCard } from "@/components/morphic/states";
import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — Morphic" },
      { name: "description", content: "Integrations and system configuration." },
    ],
  }),
  component: SettingsPage,
});

function SettingsPage() {
  const queryClient = useQueryClient();
  const [showSmtpPass, setShowSmtpPass] = useState(false);
  const [showNeoPass, setShowNeoPass] = useState(false);

  const { data: integrations, isLoading } = useQuery({
    queryKey: ["integrations"],
    queryFn: api.getIntegrations,
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) => api.updateIntegrations(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      toast.success("Settings saved successfully");
    },
  });

  if (isLoading || !integrations) {
    return (
      <AppShell>
        <SkeletonCard />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">System Configuration</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage external services, databases, and notification channels.
        </p>
      </div>

      <Tabs defaultValue="vcs" className="space-y-6">
        <TabsList className="glass border-primary/10">
          <TabsTrigger value="vcs" className="gap-2">
            <Shield className="h-4 w-4" /> VCS
          </TabsTrigger>
          <TabsTrigger value="ai" className="gap-2">
            <Cpu className="h-4 w-4" /> AI & MCP
          </TabsTrigger>
          <TabsTrigger value="infra" className="gap-2">
            <Zap className="h-4 w-4" /> Infrastructure
          </TabsTrigger>
          <TabsTrigger value="db" className="gap-2">
            <Database className="h-4 w-4" /> Databases
          </TabsTrigger>
          <TabsTrigger value="alerts" className="gap-2">
            <Bell className="h-4 w-4" /> Alerts
          </TabsTrigger>
        </TabsList>

        <TabsContent value="vcs" className="space-y-6">
          <IntegrationCard
            title="GitHub"
            domain="github.com"
            description="Manage repositories and open PRs with suggested fixes."
            onSave={(val) =>
              updateMutation.mutate({ vcs: { ...integrations.vcs, github_token: val } })
            }
            initialValue={integrations.vcs.github_token}
            placeholder="ghp_********************"
            type="password"
          />
          <IntegrationCard
            title="GitLab"
            domain="gitlab.com"
            description="Enterprise VCS integration for MRs and CI status."
            onSave={(val) =>
              updateMutation.mutate({ vcs: { ...integrations.vcs, gitlab_token: val } })
            }
            initialValue={integrations.vcs.gitlab_token}
            placeholder="glpat-********************"
            type="password"
          />
        </TabsContent>

        <TabsContent value="ai" className="space-y-6">
          <IntegrationCard
            title="Claude API"
            domain="anthropic.com"
            description="Anthropic's LLM used for Root Cause Analysis (RCA)."
            onSave={(val) =>
              updateMutation.mutate({ ai: { ...integrations.ai, anthropic_api_key: val } })
            }
            initialValue={integrations.ai.anthropic_api_key}
            placeholder="sk-ant-********************"
            type="password"
          />
          <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-lg bg-primary/10">
                  <Cpu className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg">MCP Servers</h3>
                  <p className="text-sm text-muted-foreground">
                    Model Context Protocol endpoints for extending Morphic capabilities.
                  </p>
                </div>
              </div>
            </div>
            <div className="space-y-3">
              {integrations.infrastructure.mcp_servers.map((s, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-lg border border-border bg-secondary/10 p-3"
                >
                  <div className="flex items-center gap-2">
                    <div
                      className={cn(
                        "h-1.5 w-1.5 rounded-full",
                        s.enabled ? "bg-success shadow-[0_0_8px_var(--success)]" : "bg-muted",
                      )}
                    />
                    <span className="text-sm font-medium">{s.name}</span>
                    <span className="text-[10px] text-muted-foreground font-mono">{s.url}</span>
                  </div>
                  <button className="text-[10px] font-bold uppercase tracking-wider text-primary hover:underline">
                    Configure
                  </button>
                </div>
              ))}
              <button className="w-full flex items-center justify-center gap-2 rounded-lg border border-dashed border-border py-2 text-sm text-muted-foreground hover:bg-secondary/20 transition">
                <Plus className="h-4 w-4" /> Add MCP Server
              </button>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="infra" className="space-y-6">
          <IntegrationCard
            title="n8n"
            domain="n8n.io"
            description="Workflow automation for self-healing and remediation."
            onSave={(val) =>
              updateMutation.mutate({
                infrastructure: { ...integrations.infrastructure, n8n_url: val },
              })
            }
            initialValue={integrations.infrastructure.n8n_url}
            placeholder="https://n8n.example.com"
          />
          <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
            <div className="mb-6 flex items-center gap-3">
              <img
                src="https://www.google.com/s2/favicons?domain=gmail.com&sz=64"
                className="h-10 w-10"
              />
              <div>
                <h3 className="font-semibold text-lg">SMTP Server</h3>
                <p className="text-sm text-muted-foreground">
                  Outbound email configuration for alerts.
                </p>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Host</Label>
                <Input
                  defaultValue={integrations.notifications.smtp_host}
                  placeholder="smtp.gmail.com"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Port</Label>
                <Input
                  type="number"
                  defaultValue={integrations.notifications.smtp_port}
                  placeholder="587"
                />
              </div>
              <div className="space-y-1.5">
                <Label>User</Label>
                <Input defaultValue={integrations.notifications.smtp_user} />
              </div>
              <div className="space-y-1.5">
                <Label>Password</Label>
                <Input type="password" placeholder="••••••••••••" />
              </div>
              <div className="space-y-1.5">
                <Label>Sender Name</Label>
                <Input defaultValue={integrations.notifications.sender_name} />
              </div>
              <div className="space-y-1.5">
                <Label>Sender Email</Label>
                <Input defaultValue={integrations.notifications.sender_email} />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <TestButton type="smtp" config={{}} />
              <button className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90">
                <Save className="h-4 w-4" /> Save SMTP
              </button>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="db" className="space-y-6">
          <IntegrationCard
            title="PostgreSQL"
            domain="postgresql.org"
            description="Primary data store for traces, monitors, and incidents."
            onSave={(val) =>
              updateMutation.mutate({ databases: { ...integrations.databases, postgres_url: val } })
            }
            initialValue={integrations.databases.postgres_url}
            placeholder="postgresql://user:pass@host:5432/db"
          />
          <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
            <div className="mb-6 flex items-center gap-3">
              <img
                src="https://www.google.com/s2/favicons?domain=neo4j.com&sz=64"
                className="h-10 w-10"
              />
              <div>
                <h3 className="font-semibold text-lg">Neo4j</h3>
                <p className="text-sm text-muted-foreground">
                  Graph database for dependency mapping and blast radius analysis.
                </p>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5 sm:col-span-2">
                <Label>Bolt URL</Label>
                <Input
                  defaultValue={integrations.databases.neo4j_url}
                  placeholder="bolt://localhost:7687"
                />
              </div>
              <div className="space-y-1.5">
                <Label>User</Label>
                <Input defaultValue={integrations.databases.neo4j_user} />
              </div>
              <div className="space-y-1.5">
                <Label>Password</Label>
                <Input type="password" placeholder="••••••••••••" />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <TestButton type="neo4j" config={{}} />
              <button className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90">
                <Save className="h-4 w-4" /> Save Neo4j
              </button>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="alerts" className="space-y-6">
          <IntegrationCard
            title="Slack"
            domain="slack.com"
            description="Incoming Webhooks for team alerts."
            onSave={(val) =>
              updateMutation.mutate({
                notifications: { ...integrations.notifications, slack_webhook: val },
              })
            }
            initialValue={integrations.notifications.slack_webhook}
            placeholder="https://hooks.slack.com/services/..."
            type="password"
          />
          <IntegrationCard
            title="Telegram"
            domain="telegram.org"
            description="Direct messages and group notifications via Bot API."
            onSave={(val) =>
              updateMutation.mutate({
                notifications: { ...integrations.notifications, telegram_bot_token: val },
              })
            }
            initialValue={integrations.notifications.telegram_bot_token}
            placeholder="123456:ABC-DEF..."
            type="password"
          />
          <IntegrationCard
            title="ntfy.sh"
            domain="ntfy.sh"
            description="Simple HTTP-based pub-sub for push notifications."
            onSave={(val) =>
              updateMutation.mutate({
                notifications: { ...integrations.notifications, ntfy_topic: val },
              })
            }
            initialValue={integrations.notifications.ntfy_topic}
            placeholder="topic_name"
          />
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}

function IntegrationCard({
  title,
  domain,
  description,
  onSave,
  initialValue,
  placeholder,
  type = "text",
}: {
  title: string;
  domain: string;
  description: string;
  onSave: (val: string) => void;
  initialValue?: string;
  placeholder?: string;
  type?: string;
}) {
  const [val, setVal] = useState(initialValue || "");
  const [isChanged, setIsChanged] = useState(false);
  const [showPass, setShowPass] = useState(false);

  useEffect(() => {
    setIsChanged(val !== initialValue);
  }, [val, initialValue]);

  const inputType = type === "password" ? (showPass ? "text" : "password") : type;

  return (
    <div className="rounded-xl border border-border bg-card p-6 shadow-sm transition-all hover:border-primary/20">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 overflow-hidden rounded-lg">
            <img
              src={`https://www.google.com/s2/favicons?domain=${domain}&sz=64`}
              alt={title}
              className="h-full w-full object-contain"
            />
          </div>
          <div>
            <h3 className="text-lg font-semibold">{title}</h3>
            <p className="text-sm text-muted-foreground max-w-md">{description}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <TestButton type={title.toLowerCase()} config={{ value: val }} />
          <button
            disabled={!isChanged}
            onClick={() => onSave(val)}
            className="inline-flex h-9 items-center gap-1.5 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            Save
          </button>
        </div>
      </div>
      <div className="mt-4 relative">
        <Input
          type={inputType}
          value={val}
          onChange={(e) => setVal(e.target.value)}
          placeholder={placeholder}
          className={cn("font-mono text-sm", type === "password" && "pr-10")}
        />
        {type === "password" && (
          <button
            type="button"
            onClick={() => setShowPass(!showPass)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-primary"
          >
            {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        )}
      </div>
    </div>
  );
}

function TestButton({ type, config }: { type: string; config: any }) {
  const [isTesting, setIsTesting] = useState(false);

  const handleTest = async () => {
    setIsTesting(true);
    try {
      const res = await api.testIntegration(type, config);
      if (res.success) toast.success(res.message);
      else toast.error(res.message);
    } catch (err) {
      toast.error(`Failed to test ${type} connection`);
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <button
      onClick={handleTest}
      disabled={isTesting}
      className="inline-flex h-9 items-center gap-1.5 rounded-md border border-border bg-secondary/40 px-3 text-sm font-medium transition hover:bg-secondary/80 disabled:opacity-50"
    >
      <RefreshCw className={cn("h-3.5 w-3.5", isTesting && "animate-spin")} />
      Test Connection
    </button>
  );
}

function Plus({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M5 12h14" />
      <path d="M12 5v14" />
    </svg>
  );
}
