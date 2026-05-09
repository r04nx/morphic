import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { ChevronRight, RefreshCw, Inbox, GitBranch } from "lucide-react";
import { api } from "@/api/client";
import { AppShell } from "@/components/morphic/AppShell";
import { SeverityBadge, StatusChip } from "@/components/morphic/badges";
import { CopyButton } from "@/components/morphic/CopyButton";
import { EmptyState, ErrorState, SkeletonCard } from "@/components/morphic/states";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";
import type { BlastRadius, IncidentStatus } from "@/types/morphic";

export const Route = createFileRoute("/incidents/")({
  head: () => ({
    meta: [
      { title: "Incidents — Morphic" },
      { name: "description", content: "Live incident feed with RCA confidence and severity." },
    ],
  }),
  component: IncidentsPage,
});

const SEV_RANK: Record<BlastRadius, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };

function IncidentsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sevFilter, setSevFilter] = useState<string>("all");
  const [serviceFilter, setServiceFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"newest" | "severity">("newest");
  const [search, setSearch] = useState("");

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["incidents"],
    queryFn: () => api.listIncidents(50),
    refetchInterval: 10_000,
  });

  const incidents = useMemo(() => Array.isArray(data) ? data : [], [data]);

  const services = useMemo(
    () => Array.from(new Set(incidents.map((i) => i.service).filter(Boolean) as string[])),
    [incidents],
  );

  const filtered = useMemo(() => {
    let list = incidents;
    if (statusFilter !== "all") list = list.filter((i) => i.status === statusFilter);
    if (sevFilter !== "all") list = list.filter((i) => i.blast_radius === sevFilter);
    if (serviceFilter !== "all") list = list.filter((i) => i.service === serviceFilter);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (i) =>
          (i.summary || i.impact || '').toLowerCase().includes(q) ||
          i.trace_id.toLowerCase().includes(q) ||
          i.classification?.toLowerCase().includes(q),
      );
    }
    list = [...list].sort((a, b) => {
      if (sortBy === "severity") {
        const d =
          (SEV_RANK[b.blast_radius ?? "LOW"] ?? 0) - (SEV_RANK[a.blast_radius ?? "LOW"] ?? 0);
        if (d !== 0) return d;
      }
      return b.timestamp.localeCompare(a.timestamp);
    });
    return list;
  }, [incidents, statusFilter, sevFilter, serviceFilter, search, sortBy]);

  return (
    <AppShell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Live Incidents</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Auto-refreshing every 10s · {filtered.length} of {incidents.length}
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-1.5 rounded-md border border-border bg-secondary/60 px-3 py-1.5 text-sm transition hover:border-primary/40"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", isFetching && "animate-spin")} />
          Refresh
        </button>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2 rounded-xl border border-border bg-card/40 p-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search summary, classification, trace_id…"
          className="h-9 min-w-[220px] flex-1 rounded-md border border-border bg-secondary/40 px-3 text-sm focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/30"
        />
        <FilterSelect
          value={statusFilter}
          onChange={setStatusFilter}
          placeholder="Status"
          options={[
            "all",
            "NEW",
            "TRIAGED",
            "RCA_PENDING",
            "RCA_READY",
            "ACTIONS_RUNNING",
            "RESOLVED",
            "SUPPRESSED",
          ]}
        />
        <FilterSelect
          value={sevFilter}
          onChange={setSevFilter}
          placeholder="Severity"
          options={["all", "CRITICAL", "HIGH", "MEDIUM", "LOW"]}
        />
        <FilterSelect
          value={serviceFilter}
          onChange={setServiceFilter}
          placeholder="Service"
          options={["all", ...services]}
        />
        <FilterSelect
          value={sortBy}
          onChange={(v) => setSortBy(v as "newest" | "severity")}
          placeholder="Sort"
          options={["newest", "severity"]}
          labelMap={{ newest: "Sort: newest", severity: "Sort: severity" }}
        />
      </div>

      {isLoading && (
        <div className="grid gap-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {isError && (
        <ErrorState
          title="Failed to load incidents"
          description="The backend isn't reachable. Check VITE_API_BASE_URL or try again."
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

      {!isLoading && !isError && filtered.length === 0 && (
        <EmptyState
          icon={<Inbox className="h-6 w-6" />}
          title="No incidents match your filters"
          description="Try clearing filters or wait for the next auto-refresh."
        />
      )}

      <ul className="grid gap-2.5">
        {filtered.map((inc) => (
          <li key={inc.id}>
            <Link
              to="/incidents/$incidentId"
              params={{ incidentId: inc.id }}
              className="group block rounded-xl border border-border bg-card p-4 transition hover:border-primary/40 hover:bg-card/80"
            >
              <div className="flex items-start gap-3">
                <div className="flex flex-1 flex-col gap-2 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <SeverityBadge value={inc.blast_radius} />
                    <StatusChip value={inc.status} />
                    {inc.confidence_score !== undefined && (
                      <span className="font-mono text-[11px] text-muted-foreground">
                        confidence {(parseFloat(String(inc.confidence_score)) * 100).toFixed(0)}%
                      </span>
                    )}
                    <span className="ml-auto font-mono text-[11px] text-muted-foreground">
                      {formatDistanceToNow(new Date(inc.timestamp), { addSuffix: true })}
                    </span>
                  </div>
                  <h3 className="text-base font-medium leading-snug">{inc.summary || inc.impact}</h3>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                    {inc.service && (
                      <span className="inline-flex items-center gap-1 font-mono">
                        <GitBranch className="h-3 w-3" />
                        {inc.service}
                        {inc.endpoint && (
                          <span className="text-muted-foreground/70"> · {inc.endpoint}</span>
                        )}
                      </span>
                    )}
                    <span className="font-mono">{inc.trace_id}</span>
                    <CopyButton value={inc.trace_id} label="trace" />
                  </div>
                </div>
                <ChevronRight className="mt-1 h-4 w-4 text-muted-foreground transition group-hover:translate-x-0.5 group-hover:text-foreground" />
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </AppShell>
  );
}

function FilterSelect({
  value,
  onChange,
  options,
  placeholder,
  labelMap,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  placeholder: string;
  labelMap?: Record<string, string>;
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="h-9 w-[170px] bg-secondary/40 text-sm">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {options.map((o) => (
          <SelectItem key={o} value={o} className="text-sm">
            {labelMap?.[o] ??
              (o === "all" ? `All ${placeholder.toLowerCase()}` : o.replace("_", " "))}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

// satisfy unused-warning
export type _ = IncidentStatus;
