import { Link } from "@tanstack/react-router";
import { Globe, Pause, Play, Trash2 } from "lucide-react";
import type { Monitor } from "@/types/morphic";
import { cn } from "@/lib/utils";
import { format, formatDistanceToNow } from "date-fns";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { toast } from "sonner";

// Safe date parser with fallback
const safeDate = (dateStr: string | undefined | null): Date => {
  if (!dateStr) return new Date();
  const date = new Date(dateStr);
  return isNaN(date.getTime()) ? new Date() : date;
};

export function MonitorCard({ monitor, onDelete }: { monitor: Monitor; onDelete?: () => void }) {
  const queryClient = useQueryClient();
  
  const enableMutation = useMutation({
    mutationFn: () => api.enableMonitor(monitor.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["monitors"] });
      queryClient.invalidateQueries({ queryKey: ["monitor", monitor.id] });
      toast.success(`Monitor "${monitor.name}" enabled`);
    },
    onError: () => toast.error("Failed to enable monitor"),
  });

  const disableMutation = useMutation({
    mutationFn: () => api.disableMonitor(monitor.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["monitors"] });
      queryClient.invalidateQueries({ queryKey: ["monitor", monitor.id] });
      toast.success(`Monitor "${monitor.name}" paused`);
    },
    onError: () => toast.error("Failed to pause monitor"),
  });

  const isPaused = monitor.enabled === false;
  const statusColor = {
    UP: "bg-success",
    DOWN: "bg-destructive",
    DEGRADED: "bg-warning",
  }[monitor.status];

  const statusText = {
    UP: "Operational",
    DOWN: "Outage",
    DEGRADED: "Degraded",
  }[monitor.status];

  return (
    <div className="relative group">
      <div className="absolute -top-1.5 -right-1.5 z-10 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            if (isPaused) {
              enableMutation.mutate();
            } else {
              disableMutation.mutate();
            }
          }}
          disabled={enableMutation.isPending || disableMutation.isPending}
          className={cn(
            "h-6 w-6 items-center justify-center rounded-full border transition-all flex",
            isPaused 
              ? "border-emerald-500 bg-emerald-500 text-white hover:bg-emerald-600 hover:scale-110" 
              : "border-amber-500 bg-amber-500 text-white hover:bg-amber-600 hover:scale-110"
          )}
          title={isPaused ? "Enable monitor" : "Pause monitor"}
        >
          {enableMutation.isPending || disableMutation.isPending ? (
            <div className="h-2.5 w-2.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
          ) : isPaused ? (
            <Play className="h-3 w-3" strokeWidth={3} />
          ) : (
            <Pause className="h-3 w-3" strokeWidth={3} />
          )}
        </button>
        {onDelete && (
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              if (confirm(`Delete monitor "${monitor.name}"?`)) {
                onDelete();
              }
            }}
            className="h-6 w-6 items-center justify-center rounded-full border border-red-500 bg-red-500 text-white hover:bg-red-600 hover:scale-110 transition-all flex"
            title="Delete monitor"
          >
            <Trash2 className="h-3 w-3" strokeWidth={2.5} />
          </button>
        )}
      </div>
      <Link
        to="/monitors/$monitorId"
        params={{ monitorId: monitor.id }}
        className={cn(
          "block rounded-xl border p-4 transition",
          isPaused 
            ? "border-border/50 bg-card/50 opacity-60" 
            : "border-border bg-card hover:border-primary/40 hover:bg-card/80"
        )}
      >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={cn("h-2 w-2 rounded-full", statusColor)} />
          <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            {statusText}
          </span>
          {isPaused && (
            <span className="text-[9px] font-medium uppercase tracking-wider text-warning bg-warning/10 px-2 py-0.5 rounded">
              Paused
            </span>
          )}
        </div>
        <span className="font-mono text-[10px] text-muted-foreground">
          {formatDistanceToNow(safeDate(monitor.last_check), { addSuffix: true })}
        </span>
      </div>

      <div className="mb-4">
        <h3 className="text-base font-medium leading-snug truncate group-hover:text-primary transition-colors text-foreground dark:text-zinc-100">
          {monitor.name}
        </h3>
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground font-mono truncate opacity-70">
          <Globe className="h-3 w-3 shrink-0" />
          {monitor.url}
        </div>
      </div>

      <div className="mb-4 flex items-center justify-between gap-4">
        <div className="flex flex-col gap-0.5">
          <span className="text-[9px] uppercase tracking-wider text-muted-foreground font-bold">
            Uptime
          </span>
          <span className="text-sm font-semibold">{monitor.uptime_pct}%</span>
        </div>
        <div className="flex flex-col gap-0.5 text-right">
          <span className="text-[9px] uppercase tracking-wider text-muted-foreground font-bold">
            Latency
          </span>
          <span className="text-sm font-semibold">{monitor.latency_ms}ms</span>
        </div>
      </div>

      <TooltipProvider>
        <div className="flex h-6 w-full items-center gap-[1px]">
          {monitor.history.map((h, i) => (
            <Tooltip key={i}>
              <TooltipTrigger asChild>
                <div
                  className={cn(
                    "h-5 w-[4px] rounded-[1px] transition-all hover:scale-y-125",
                    h.status === "UP" && "bg-success/80 hover:bg-success",
                    h.status === "DEGRADED" && "bg-warning/80 hover:bg-warning",
                    h.status === "DOWN" && "bg-destructive/80 hover:bg-destructive",
                  )}
                />
              </TooltipTrigger>
              <TooltipContent side="top" className="text-[10px] py-1 px-2 font-mono">
                {h.status} · {format(safeDate(h.timestamp), "HH:mm")}
              </TooltipContent>
            </Tooltip>
          ))}
        </div>
      </TooltipProvider>
    </Link>
    </div>
  );
}
