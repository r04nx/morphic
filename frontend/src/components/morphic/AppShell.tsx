import { Link, useRouterState } from "@tanstack/react-router";
import { Activity, LineChart, Search, Settings, Workflow } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "@tanstack/react-router";
import { isMockMode } from "@/api/client";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "./ThemeToggle";
import { useTheme } from "./theme";
import { Breadcrumbs } from "./Breadcrumbs";

const NAV = [
  { to: "/incidents", label: "Incidents", icon: Activity },
  { to: "/monitors", label: "Monitors", icon: LineChart },
  { to: "/actions", label: "Actions", icon: Workflow },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <div className="flex min-h-screen w-full bg-background text-foreground">
      <Sidebar pathname={pathname} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex-1 overflow-x-hidden">
          <div className="mx-auto w-full max-w-[1400px] px-6 pt-6">
            <div className="mb-4">
              <Breadcrumbs />
            </div>
            <div className="pb-6">
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

function Sidebar({ pathname }: { pathname: string }) {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);
  }, []);

  const logoSrc =
    !mounted || resolvedTheme === "dark" ? "/logo-blackbg-square.png" : "/logo-whitebg-square.png";

  return (
    <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-nav-border bg-nav md:flex">
      <div className="flex h-14 items-center gap-2 border-b border-nav-border px-4">
        <div className="grid h-8 w-8 place-items-center overflow-hidden rounded-md border border-nav-border bg-background">
          <img
            src={logoSrc}
            alt="Morphic"
            className="h-8 w-8 object-contain"
            loading="eager"
            decoding="async"
          />
        </div>
        <div>
          <div className="font-semibold leading-none">Morphic</div>
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
            Self-healing console
          </div>
        </div>
      </div>
      <nav className="flex-1 space-y-0.5 p-2">
        {NAV.map((item) => {
          const active = pathname === item.to || pathname.startsWith(item.to + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition",
                active
                  ? "bg-nav-active text-foreground shadow-[inset_0_0_0_1px_var(--nav-border)]"
                  : "text-muted-foreground hover:bg-nav-hover hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-nav-border p-3 text-[11px] text-muted-foreground">
        <div className="flex items-center gap-1.5 font-mono">
          <span className="h-1.5 w-1.5 rounded-full bg-success" />
          {isMockMode ? "demo data" : "live"}
        </div>
      </div>
    </aside>
  );
}

function TopBar() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const v = q.trim();
    if (!v) return;
    navigate({ to: "/traces/$traceId", params: { traceId: v } });
  };

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-background/80 px-6 backdrop-blur">
      <form onSubmit={onSubmit} className="relative flex-1 max-w-md">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search trace_id…"
          className="h-9 w-full rounded-md border border-border bg-secondary/40 pl-8 pr-3 font-mono text-xs text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/30"
        />
      </form>
      <ThemeToggle />
    </header>
  );
}
