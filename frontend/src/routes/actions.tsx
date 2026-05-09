import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { useMemo, useState } from "react";
import { format } from "date-fns";
import { api } from "@/api/client";
import { AppShell } from "@/components/morphic/AppShell";
import { ActionStatusChip, ActionTypeBadge } from "@/components/morphic/badges";
import { EmptyState, ErrorState, SkeletonCard } from "@/components/morphic/states";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export const Route = createFileRoute("/actions")({
  head: () => ({
    meta: [
      { title: "Actions — Morphic" },
      { name: "description", content: "Automated action execution history." },
    ],
  }),
  component: ActionsPage,
});

function ActionsPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["actions"],
    queryFn: () => api.listActions(200),
    refetchInterval: 15_000,
  });
  const [type, setType] = useState("all");
  const [status, setStatus] = useState("all");

  const filtered = useMemo(() => {
    let list = data ?? [];
    if (type !== "all") list = list.filter((a) => a.action_type === type);
    if (status !== "all") list = list.filter((a) => a.status === status);
    return list;
  }, [data, type, status]);

  return (
    <AppShell>
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Action history</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Automated and manually triggered remediations · {filtered.length} of {data?.length ?? 0}
          </p>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2 rounded-xl border border-border bg-card/40 p-3">
        <Select value={type} onValueChange={setType}>
          <SelectTrigger className="h-9 w-[170px] bg-secondary/40 text-sm">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            {["all", "EMAIL", "GITHUB_PR", "RESTART", "TICKET"].map((o) => (
              <SelectItem key={o} value={o}>
                {o === "all" ? "All types" : o}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="h-9 w-[170px] bg-secondary/40 text-sm">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            {["all", "QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "SKIPPED"].map((o) => (
              <SelectItem key={o} value={o}>
                {o === "all" ? "All status" : o}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading && <SkeletonCard />}
      {isError && (
        <ErrorState
          title="Failed to load actions"
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
          title="No actions"
          description="Trigger an action from an incident detail page."
        />
      )}

      {filtered.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-border bg-card">
          <table className="w-full text-sm">
            <thead className="bg-secondary/40 text-left text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Incident</th>
                <th className="px-3 py-2">Started</th>
                <th className="px-3 py-2">Finished</th>
                <th className="px-3 py-2">Output</th>
                <th className="px-3 py-2">Link</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((a) => (
                <tr key={a.id} className="border-t border-border/60 hover:bg-secondary/20">
                  <td className="px-3 py-2">
                    <ActionTypeBadge value={a.action_type} />
                  </td>
                  <td className="px-3 py-2">
                    <ActionStatusChip value={a.status} />
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px]">
                    {a.incident_id ? (
                      <Link
                        to="/incidents/$incidentId"
                        params={{ incidentId: a.incident_id }}
                        className="text-primary hover:underline"
                      >
                        {a.incident_id}
                      </Link>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px] text-muted-foreground">
                    {a.started_at ? format(new Date(a.started_at), "HH:mm:ss") : "—"}
                  </td>
                  <td className="px-3 py-2 font-mono text-[11px] text-muted-foreground">
                    {a.finished_at ? format(new Date(a.finished_at), "HH:mm:ss") : "—"}
                  </td>
                  <td className="px-3 py-2 max-w-[280px] truncate text-foreground/90">
                    {a.output ?? a.summary ?? "—"}
                  </td>
                  <td className="px-3 py-2">
                    {a.link ? (
                      <a
                        href={a.link}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-primary hover:underline"
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
    </AppShell>
  );
}
