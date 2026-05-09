import { cn } from "@/lib/utils";
import type { ActionStatus, ActionType, BlastRadius, IncidentStatus } from "@/types/morphic";

const sevMap: Record<BlastRadius, string> = {
  LOW: "bg-muted text-muted-foreground border-border",
  MEDIUM: "bg-warning/15 text-warning border-warning/30",
  HIGH: "bg-[oklch(0.32_0.12_50)] text-[oklch(0.85_0.18_55)] border-[oklch(0.55_0.15_50)]/40",
  CRITICAL: "bg-destructive/20 text-[oklch(0.82_0.18_25)] border-destructive/40",
};

export function SeverityBadge({ value }: { value?: BlastRadius }) {
  if (!value) return null;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-mono font-medium uppercase tracking-wider",
        sevMap[value],
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {value}
    </span>
  );
}

const statusMap: Record<IncidentStatus, string> = {
  NEW: "bg-info/15 text-info border-info/30",
  TRIAGED: "bg-muted text-muted-foreground border-border",
  RCA_PENDING:
    "bg-[oklch(0.28_0.12_295)] text-[oklch(0.82_0.18_295)] border-[oklch(0.55_0.18_295)]/40",
  RCA_READY: "bg-primary/15 text-primary border-primary/30",
  ACTIONS_RUNNING: "bg-info/15 text-info border-info/40",
  RESOLVED: "bg-success/15 text-success border-success/30",
  SUPPRESSED: "bg-muted text-muted-foreground border-border",
};

export function StatusChip({ value }: { value: IncidentStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-mono font-medium uppercase tracking-wider",
        statusMap[value],
      )}
    >
      {value.replace("_", " ")}
    </span>
  );
}

const actionStatusMap: Record<ActionStatus, string> = {
  QUEUED: "bg-muted text-muted-foreground",
  RUNNING: "bg-info/15 text-info animate-pulse",
  SUCCEEDED: "bg-success/15 text-success",
  FAILED: "bg-destructive/20 text-[oklch(0.82_0.18_25)]",
  SKIPPED: "bg-muted text-muted-foreground",
};

export function ActionStatusChip({ value }: { value: ActionStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-2 py-0.5 text-[11px] font-mono font-medium uppercase tracking-wider",
        actionStatusMap[value],
      )}
    >
      {value}
    </span>
  );
}

const actionTypeLabel: Record<ActionType, string> = {
  EMAIL: "Email",
  GITHUB_PR: "GitHub PR",
  RESTART: "Restart",
  TICKET: "Ticket",
};

export function ActionTypeBadge({ value }: { value: ActionType }) {
  return (
    <span className="inline-flex items-center rounded-md border border-border bg-secondary/60 px-2 py-0.5 text-xs font-mono">
      {actionTypeLabel[value]}
    </span>
  );
}
