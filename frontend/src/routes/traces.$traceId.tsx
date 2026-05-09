import { createFileRoute, useRouter } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChevronDown, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import { format } from "date-fns";
import { api } from "@/api/client";
import { AppShell } from "@/components/morphic/AppShell";
import { CopyButton } from "@/components/morphic/CopyButton";
import { ErrorState, SkeletonCard } from "@/components/morphic/states";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import type { TraceEvent } from "@/types/morphic";

export const Route = createFileRoute("/traces/$traceId")({
  head: ({ params }) => ({
    meta: [
      { title: `Trace ${params.traceId} — Morphic` },
      { name: "description", content: "Trace timeline with async-orphan detection." },
    ],
  }),
  component: TracePage,
});

const LEVEL_COLOR: Record<TraceEvent["level"], string> = {
  DEBUG: "text-muted-foreground",
  INFO: "text-info",
  WARN: "text-warning",
  ERROR: "text-[oklch(0.82_0.18_25)]",
};

function TracePage() {
  const { traceId } = Route.useParams();
  const router = useRouter();
  const [level, setLevel] = useState("all");
  const [errorsOnly, setErrorsOnly] = useState(false);
  const [search, setSearch] = useState("");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["trace", traceId],
    queryFn: () => api.listTraceEvents(traceId),
    refetchInterval: 15_000,
  });

  const events = useMemo(() => {
    let list = data ?? [];
    if (errorsOnly) list = list.filter((e) => e.level === "ERROR" || e.level === "WARN");
    if (level !== "all") list = list.filter((e) => e.level === level);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((e) => e.message.toLowerCase().includes(q));
    }
    return list;
  }, [data, level, errorsOnly, search]);

  const counts = useMemo(() => {
    const c = { DEBUG: 0, INFO: 0, WARN: 0, ERROR: 0, ORPHAN: 0 };
    (data ?? []).forEach((e) => {
      c[e.level]++;
      if (e.async_orphan) c.ORPHAN++;
    });
    return c;
  }, [data]);

  return (
    <AppShell>
      <button
        onClick={() => router.history.back()}
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Back
      </button>

      <div className="rounded-xl border border-border bg-card p-5">
        <div className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
          Trace
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <span className="font-mono text-lg">{traceId}</span>
          <CopyButton value={traceId} label="copy" />
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Stat label="DEBUG" value={counts.DEBUG} />
          <Stat label="INFO" value={counts.INFO} accent="info" />
          <Stat label="WARN" value={counts.WARN} accent="warn" />
          <Stat label="ERROR" value={counts.ERROR} accent="error" />
          <Stat label="ASYNC-ORPHAN" value={counts.ORPHAN} accent="warn" />
        </div>
      </div>

      <div className="my-4 flex flex-wrap items-center gap-2 rounded-xl border border-border bg-card/40 p-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search messages…"
          className="h-9 min-w-[220px] flex-1 rounded-md border border-border bg-secondary/40 px-3 text-sm focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/30"
        />
        <Select value={level} onValueChange={setLevel}>
          <SelectTrigger className="h-9 w-[150px] bg-secondary/40 text-sm">
            <SelectValue placeholder="Level" />
          </SelectTrigger>
          <SelectContent>
            {["all", "DEBUG", "INFO", "WARN", "ERROR"].map((l) => (
              <SelectItem key={l} value={l}>
                {l === "all" ? "All levels" : l}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <Switch checked={errorsOnly} onCheckedChange={setErrorsOnly} />
          Errors & warnings only
        </label>
      </div>

      {isLoading && <SkeletonCard />}
      {isError && (
        <ErrorState
          title="Failed to load trace"
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

      {!isLoading && !isError && (
        <ol className="overflow-hidden rounded-xl border border-border bg-card">
          {events.map((e) => (
            <EventRow key={e.id} e={e} />
          ))}
          {events.length === 0 && (
            <li className="px-4 py-12 text-center text-sm text-muted-foreground">
              No events match your filters.
            </li>
          )}
        </ol>
      )}
    </AppShell>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: "info" | "warn" | "error";
}) {
  return (
    <div className="rounded-lg border border-border bg-secondary/30 p-3">
      <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div
        className={cn(
          "mt-0.5 font-mono text-xl",
          accent === "warn" && "text-warning",
          accent === "error" && "text-[oklch(0.82_0.18_25)]",
          accent === "info" && "text-info",
        )}
      >
        {value}
      </div>
    </div>
  );
}

function EventRow({ e }: { e: TraceEvent }) {
  const [open, setOpen] = useState(false);
  const hasFields = e.fields && Object.keys(e.fields).length > 0;
  return (
    <li
      className={cn(
        "border-t border-border/60 first:border-t-0 px-3 py-2 font-mono text-xs",
        e.async_orphan && "bg-warning/5 border-l-2 border-l-warning",
      )}
    >
      <div className="flex items-start gap-3">
        <button
          onClick={() => hasFields && setOpen((v) => !v)}
          className={cn(
            "mt-0.5 text-muted-foreground",
            hasFields ? "hover:text-foreground" : "opacity-30 cursor-default",
          )}
        >
          {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        </button>
        <span className="w-[88px] shrink-0 text-muted-foreground">
          {format(new Date(e.timestamp), "HH:mm:ss.SSS")}
        </span>
        <span className={cn("w-12 shrink-0 font-semibold", LEVEL_COLOR[e.level])}>{e.level}</span>
        <span className="flex-1 break-words text-foreground/90">{e.message}</span>
        <div className="flex shrink-0 items-center gap-1.5">
          {e.async_orphan && (
            <span className="rounded border border-warning/40 bg-warning/10 px-1.5 py-0.5 text-[10px] text-warning">
              ASYNC-ORPHAN
            </span>
          )}
          {e.logger && <span className="hidden text-muted-foreground sm:inline">{e.logger}</span>}
        </div>
      </div>
      {open && hasFields && (
        <pre className="mt-2 ml-[112px] max-w-full overflow-x-auto rounded-md border border-border bg-[oklch(0.14_0.018_260)] p-3 text-[11.5px] text-muted-foreground">
          {JSON.stringify(e.fields, null, 2)}
        </pre>
      )}
    </li>
  );
}
