import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import cytoscape from "cytoscape";
// @ts-ignore
import coseBilkent from "cytoscape-cose-bilkent";
import {
  Activity,
  RefreshCw,
  X,
  ExternalLink,
  Share2,
  GitBranch,
  Server,
  User,
  ShoppingCart,
  Code2,
} from "lucide-react";
import { api } from "@/api/client";
import { AppShell } from "@/components/morphic/AppShell";
import { SeverityBadge, StatusChip } from "@/components/morphic/badges";

// Register layout once
try { cytoscape.use(coseBilkent); } catch (_) {}

// ─── Route ──────────────────────────────────────────────────────────────────

export const Route = createFileRoute("/graph")({
  head: () => ({
    meta: [
      { title: "Knowledge Graph — Morphic" },
      { name: "description", content: "Neo4j incident knowledge graph — service topology and blast radius." },
    ],
  }),
  component: GraphPage,
});

// ─── Constants ──────────────────────────────────────────────────────────────

const NODE_COLORS: Record<string, string> = {
  CRITICAL: "#EF4444",
  HIGH: "#F59E0B",
  MEDIUM: "#8B5CF6",
  LOW: "#3B82F6",
  service: "#10B981",
  javaclass: "#06B6D4",
  user: "#06B6D4",
  order: "#F59E0B",
  unknown: "#6B7280",
};

const NODE_SIZES: Record<string, number> = {
  CRITICAL: 110,
  HIGH: 90,
  MEDIUM: 75,
  LOW: 60,
};

const TYPE_ICONS: Record<string, React.ElementType> = {
  incident: Activity,
  service: Server,
  user: User,
  order: ShoppingCart,
  javaclass: Code2,
};

// ─── Cytoscape stylesheet ────────────────────────────────────────────────────

const CY_STYLE: cytoscape.StylesheetCSS[] = [
  {
    selector: "node",
    style: {
      "background-color": "data(color)",
      "border-width": 2,
      "border-color": "data(borderColor)",
      "border-opacity": 0.7,
      label: "data(label)",
      color: "#F1F5F9",
      "font-size": 13,
      "font-family": "'Inter', 'Segoe UI', sans-serif",
      "font-weight": "600",
      "text-valign": "bottom",
      "text-halign": "center",
      "text-margin-y": 6,
      "text-wrap": "wrap",
      "text-max-width": 120,
      width: "data(size)",
      height: "data(size)",
      "overlay-opacity": 0,
      "transition-property": "border-width, border-opacity, background-opacity",
      "transition-duration": "0.15s" as any,
    },
  },
  {
    selector: "node[type='incident']",
    style: {
      shape: "ellipse",
    },
  },
  {
    selector: "node[type='service']",
    style: {
      shape: "round-rectangle",
    },
  },
  {
    selector: "node[type='javaclass']",
    style: {
      shape: "diamond",
    },
  },
  {
    selector: "node[type='user']",
    style: {
      shape: "round-triangle",
    },
  },
  {
    selector: "node[type='order']",
    style: {
      shape: "hexagon",
    },
  },
  {
    selector: "node:selected",
    style: {
      "border-width": 3,
      "border-color": "#FFFFFF",
      "border-opacity": 1,
    },
  },
  {
    selector: "node.dimmed",
    style: {
      opacity: 0.25,
    },
  },
  {
    selector: "node.highlighted",
    style: {
      "border-width": 3,
      "border-color": "#FFFFFF",
      "border-opacity": 1,
    },
  },
  {
    selector: "edge",
    style: {
      width: 1.5,
      "line-color": "#334155",
      "target-arrow-color": "#334155",
      "target-arrow-shape": "vee",
      "curve-style": "bezier",
      label: "data(label)",
      "font-size": 8,
      color: "#64748B",
      "font-family": "monospace",
      "text-rotation": "autorotate",
      "text-background-color": "#0D1117",
      "text-background-opacity": 0.8,
      "text-background-padding": "2px" as any,
      "overlay-opacity": 0,
      "transition-property": "opacity",
      "transition-duration": "0.15s" as any,
    },
  },
  {
    selector: "edge[label='ORIGINATED_IN']",
    style: { "line-color": "#10B981", "target-arrow-color": "#10B981", width: 2 },
  },
  {
    selector: "edge[label='AFFECTED']",
    style: { "line-color": "#F59E0B", "target-arrow-color": "#F59E0B" },
  },
  {
    selector: "edge[label='TRIGGERED']",
    style: { "line-color": "#EF4444", "target-arrow-color": "#EF4444", width: 2 },
  },
  {
    selector: "edge[label='CORRELATES_WITH']",
    style: {
      "line-color": "#8B5CF6",
      "target-arrow-color": "#8B5CF6",
      "line-style": "dashed",
    },
  },
  {
    selector: "edge[label='HEALED']",
    style: { "line-color": "#10B981", "target-arrow-color": "#10B981", "line-style": "dotted" },
  },
  {
    selector: "edge.dimmed",
    style: { opacity: 0.1 },
  },
  {
    selector: "edge.highlighted",
    style: { width: 2.5, "line-color": "#FFFFFF", "target-arrow-color": "#FFFFFF" },
  },
];

// Build a short human-readable label:
// - incidents → "Race Condition · 95%"  (classification truncated to 20 chars)
// - services  → "payment-service"
// - others    → raw label (20 chars max)
function makeLabel(d: any): { label: string; fullLabel: string } {
  const fullLabel = d.classification || d.label || "";
  if (d.type === "incident") {
    const cls = (d.classification || d.label || "Incident")
      // Strip generic prefixes like "Auto-detected anomaly:"
      .replace(/^auto[-\s]?detected[\s\w]*[:–-]\s*/i, "")
      .replace(/^incident[:–-]\s*/i, "")
      .trim();
    const short = cls.length > 22 ? cls.slice(0, 21) + "…" : cls;
    const pct = d.confidence !== undefined ? ` · ${Math.round(d.confidence * 100)}%` : "";
    return { label: short + pct, fullLabel: cls };
  }
  const short = (d.label ?? "").length > 24 ? (d.label ?? "").slice(0, 23) + "…" : (d.label ?? "");
  return { label: short, fullLabel: d.label ?? "" };
}

function enrichElements(nodes: any[], edges: any[]) {
  return [
    ...nodes.map((n) => {
      const d = n.data;
      const isIncident = d.type === "incident";
      const severity = d.severity ?? "MEDIUM";
      const color = isIncident
        ? (NODE_COLORS[severity] ?? NODE_COLORS.MEDIUM)
        : (NODE_COLORS[d.type] ?? NODE_COLORS.unknown);
      const size = isIncident ? (NODE_SIZES[severity] ?? 60) : 55;
      const { label, fullLabel } = makeLabel(d);
      return {
        data: {
          ...d,
          color,
          borderColor: color,
          size,
          label,
          fullLabel,
        },
      };
    }),
    ...edges,
  ];
}

// ─── Main Page ───────────────────────────────────────────────────────────────

function GraphPage() {
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [selected, setSelected] = useState<any | null>(null);
  const [filter, setFilter] = useState<string>("ALL");

  const { data, isLoading, isError, refetch, dataUpdatedAt } = useQuery({
    queryKey: ["graph-incidents"],
    queryFn: () => api.getGraphIncidents(),
    refetchInterval: 30_000,
    staleTime: 25_000,
  });

  const nodeCount = data?.nodes.length ?? 0;
  const edgeCount = data?.edges.length ?? 0;

  // Filter nodes by severity
  const filteredData = (() => {
    if (!data) return { nodes: [], edges: [] };
    if (filter === "ALL") return data;
    const allowedIds = new Set(
      data.nodes
        .filter((n) => n.data.type !== "incident" || n.data.severity === filter)
        .map((n) => n.data.id),
    );
    const filteredNodes = data.nodes.filter((n) => allowedIds.has(n.data.id));
    const filteredEdges = data.edges.filter(
      (e) => allowedIds.has(e.data.source) && allowedIds.has(e.data.target),
    );
    return { nodes: filteredNodes, edges: filteredEdges };
  })();

  const elements = enrichElements(filteredData.nodes, filteredData.edges);

  // Click + hover handler
  const handleCyReady = useCallback((cy: cytoscape.Core) => {
    cyRef.current = cy;

    // ── Click: highlight neighbourhood ──
    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      const d = node.data();
      if (d.type === "incident") setSelected(d);
      else setSelected(null);
      cy.elements().addClass("dimmed").removeClass("highlighted");
      node.removeClass("dimmed").addClass("highlighted");
      node.neighborhood().removeClass("dimmed").addClass("highlighted");
    });

    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        setSelected(null);
        cy.elements().removeClass("dimmed highlighted");
      }
    });

    // ── Hover tooltip ──
    cy.on("mouseover", "node", (evt) => {
      const d = evt.target.data();
      const tip = document.getElementById("cy-tooltip");
      if (!tip) return;
      const rp = evt.renderedPosition;
      const container = (cy as any).container() as HTMLElement;
      const rect = container.getBoundingClientRect();
      tip.innerText = d.fullLabel || d.label || d.id;
      tip.style.left = `${rect.left + rp.x + 14}px`;
      tip.style.top  = `${rect.top  + rp.y - 10}px`;
      tip.style.display = "block";
      container.style.cursor = "pointer";
    });

    cy.on("mouseout", "node", () => {
      const tip = document.getElementById("cy-tooltip");
      if (tip) tip.style.display = "none";
      const container = (cy as any).container() as HTMLElement;
      if (container) container.style.cursor = "default";
    });

    cy.on("drag", "node", () => {
      const tip = document.getElementById("cy-tooltip");
      if (tip) tip.style.display = "none";
    });
  }, []);

  const fitGraph = () => cyRef.current?.fit(undefined, 40);

  const lastUpdated = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString()
    : null;

  return (
    <>
      {/* Fixed hover tooltip — controlled by cytoscape mouseover handlers */}
      <div
        id="cy-tooltip"
        style={{
          display: "none",
          position: "fixed",
          zIndex: 9999,
          pointerEvents: "none",
          background: "rgba(15,23,42,0.95)",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: "8px",
          padding: "6px 10px",
          fontSize: "12px",
          fontFamily: "'Inter','Segoe UI',sans-serif",
          fontWeight: 500,
          color: "#F1F5F9",
          maxWidth: "260px",
          wordBreak: "break-word",
          backdropFilter: "blur(8px)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
        }}
      />
      <AppShell>
      {/* ── Top bar ── */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div>
          <h1 className="text-xl font-semibold">Knowledge Graph</h1>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Neo4j incident topology — blast radius &amp; service relationships
          </p>
        </div>

        <div className="ml-auto flex items-center gap-2">
          {/* Stats chips */}
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-secondary/60 px-3 py-1 font-mono text-xs text-muted-foreground">
            <Share2 className="h-3 w-3" />
            {nodeCount} nodes
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-secondary/60 px-3 py-1 font-mono text-xs text-muted-foreground">
            <GitBranch className="h-3 w-3" />
            {edgeCount} edges
          </span>
          {lastUpdated && (
            <span className="font-mono text-[11px] text-muted-foreground">
              updated {lastUpdated}
            </span>
          )}
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-secondary/60 px-3 py-1.5 text-xs transition hover:border-primary/40 hover:bg-secondary"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
          <button
            onClick={fitGraph}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-secondary/60 px-3 py-1.5 text-xs transition hover:border-primary/40"
          >
            Fit
          </button>
        </div>
      </div>

      {/* ── Severity filter ── */}
      <div className="mb-3 flex flex-wrap gap-1.5">
        {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
          <button
            key={sev}
            onClick={() => setFilter(sev)}
            className={[
              "rounded-full border px-3 py-0.5 font-mono text-[11px] transition",
              filter === sev
                ? "border-primary/50 bg-primary/10 text-primary"
                : "border-border bg-secondary/40 text-muted-foreground hover:border-primary/30",
            ].join(" ")}
          >
            {sev === "ALL" ? "All nodes" : sev}
          </button>
        ))}
      </div>

      {/* ── Legend ── */}
      <div className="mb-3 flex flex-wrap items-center gap-3 rounded-xl border border-border bg-card px-4 py-2">
        <span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">Legend</span>
        {[
          { label: "CRITICAL", color: "#EF4444" },
          { label: "HIGH", color: "#F59E0B" },
          { label: "MEDIUM", color: "#8B5CF6" },
          { label: "LOW", color: "#3B82F6" },
          { label: "Service", color: "#10B981" },
          { label: "User/Class", color: "#06B6D4" },
        ].map(({ label, color }) => (
          <span key={label} className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />
            {label}
          </span>
        ))}
        <span className="ml-auto text-[10px] text-muted-foreground">Click a node to inspect • Scroll to zoom</span>
      </div>

      {/* ── Graph canvas ── */}
      <div className="relative overflow-hidden rounded-xl border border-border" style={{ height: "60vh", background: "#0D1117" }}>
        {isLoading && <GraphSkeleton />}
        {isError && (
          <div className="flex h-full flex-col items-center justify-center gap-3">
            <p className="text-sm text-muted-foreground">Failed to load graph</p>
            <button
              onClick={() => refetch()}
              className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground"
            >
              Retry
            </button>
          </div>
        )}
        {!isLoading && !isError && elements.length === 0 && (
          <EmptyGraph />
        )}
        {!isLoading && !isError && elements.length > 0 && (
          <CytoscapeComponent
            elements={elements}
            stylesheet={CY_STYLE}
            layout={{
              name: "cose-bilkent",
              animate: true,
              animationDuration: 600,
              randomize: false,
              nodeRepulsion: 8500,
              idealEdgeLength: 120,
              edgeElasticity: 0.45,
              gravity: 0.25,
              numIter: 2500,
              tile: true,
              tilingPaddingVertical: 10,
              tilingPaddingHorizontal: 10,
            } as any}
            cy={handleCyReady}
            style={{ width: "100%", height: "100%", background: "transparent" }}
            minZoom={0.2}
            maxZoom={3}
          />
        )}

        {/* ── Selected node popup ── */}
        {selected && <IncidentPopup data={selected} onClose={() => setSelected(null)} />}

        {/* Zoom hint */}
        <div className="pointer-events-none absolute bottom-3 right-3 font-mono text-[10px] text-muted-foreground/50">
          scroll to zoom • drag to pan
        </div>
      </div>

      {/* ── Node table ── */}
      {data && data.nodes.filter((n) => n.data.type === "incident").length > 0 && (
        <IncidentTable nodes={data.nodes} onSelect={setSelected} />
      )}
    </AppShell>
    </>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function IncidentPopup({ data, onClose }: { data: any; onClose: () => void }) {
  const TypeIcon = TYPE_ICONS[data.type] ?? Activity;
  const color = data.type === "incident"
    ? (NODE_COLORS[data.severity] ?? NODE_COLORS.MEDIUM)
    : (NODE_COLORS[data.type] ?? NODE_COLORS.unknown);

  return (
    <div
      className="absolute right-4 top-4 z-20 w-72 overflow-hidden rounded-xl border border-white/10 shadow-2xl"
      style={{ background: "rgba(15,23,42,0.97)", backdropFilter: "blur(12px)" }}
    >
      {/* Header */}
      <div
        className="flex items-center gap-2 px-4 py-3"
        style={{ borderBottom: `1px solid ${color}30`, background: `${color}10` }}
      >
        <span
          className="grid h-7 w-7 shrink-0 place-items-center rounded-lg"
          style={{ background: `${color}20`, border: `1px solid ${color}50` }}
        >
          <TypeIcon className="h-4 w-4" style={{ color }} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-white">{data.label}</div>
          <div className="font-mono text-[10px]" style={{ color }}>{data.severity}</div>
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-white transition">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Body */}
      <div className="space-y-2 p-4">
        {data.trace_id && (
          <Row label="Trace ID">
            <span className="font-mono text-[11px] text-blue-300">{data.trace_id}</span>
          </Row>
        )}
        {data.classification && (
          <Row label="Classification">
            <span className="text-xs text-slate-300">{data.classification}</span>
          </Row>
        )}
        {data.root_cause && (
          <Row label="Root cause">
            <span className="text-xs leading-relaxed text-slate-300">{data.root_cause}</span>
          </Row>
        )}
        {data.confidence !== undefined && (
          <Row label="Confidence">
            <div className="flex items-center gap-2">
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${Math.round(data.confidence * 100)}%`, background: color }}
                />
              </div>
              <span className="font-mono text-[11px] text-white">
                {Math.round(data.confidence * 100)}%
              </span>
            </div>
          </Row>
        )}
        {data.status && (
          <Row label="Status">
            <StatusChip value={data.status} />
          </Row>
        )}
      </div>

      {data.trace_id && (
        <div className="border-t border-white/5 px-4 py-2.5">
          <Link
            to="/incidents/$incidentId"
            params={{ incidentId: data.trace_id }}
            className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
          >
            View full incident <ExternalLink className="h-3 w-3" />
          </Link>
        </div>
      )}
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-0.5 font-mono text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
      {children}
    </div>
  );
}

function IncidentTable({ nodes, onSelect }: { nodes: any[]; onSelect: (d: any) => void }) {
  const incidents = nodes
    .filter((n) => n.data.type === "incident")
    .sort((a, b) => {
      const order: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
      return (order[a.data.severity] ?? 4) - (order[b.data.severity] ?? 4);
    });

  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-border bg-card">
      <div className="border-b border-border px-4 py-3 text-xs font-semibold text-muted-foreground">
        Incident nodes in graph ({incidents.length})
      </div>
      <table className="w-full text-sm">
        <thead className="bg-secondary/30 text-left text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
          <tr>
            <th className="px-4 py-2">Severity</th>
            <th className="px-4 py-2">Label</th>
            <th className="px-4 py-2">Trace ID</th>
            <th className="px-4 py-2">Confidence</th>
            <th className="px-4 py-2">Status</th>
            <th className="px-4 py-2" />
          </tr>
        </thead>
        <tbody>
          {incidents.map((n) => {
            const d = n.data;
            return (
              <tr
                key={d.id}
                className="cursor-pointer border-t border-border/60 hover:bg-secondary/30 transition"
                onClick={() => onSelect(d)}
              >
                <td className="px-4 py-2">
                  <SeverityBadge value={d.severity} />
                </td>
                <td className="px-4 py-2 font-medium text-foreground/90">{d.label}</td>
                <td className="px-4 py-2 font-mono text-[11px] text-muted-foreground">{d.trace_id || "—"}</td>
                <td className="px-4 py-2">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-secondary">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.round((d.confidence ?? 0) * 100)}%`,
                          background: NODE_COLORS[d.severity] ?? NODE_COLORS.MEDIUM,
                        }}
                      />
                    </div>
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {Math.round((d.confidence ?? 0) * 100)}%
                    </span>
                  </div>
                </td>
                <td className="px-4 py-2">
                  <StatusChip value={d.status ?? "RCA_READY"} />
                </td>
                <td className="px-4 py-2 text-right">
                  {d.trace_id && (
                    <Link
                      to="/incidents/$incidentId"
                      params={{ incidentId: d.trace_id }}
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                    >
                      View <ExternalLink className="h-3 w-3" />
                    </Link>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function GraphSkeleton() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4">
      <div className="relative">
        <div className="h-14 w-14 animate-pulse rounded-full bg-primary/20" />
        <div className="absolute -right-8 -top-4 h-8 w-8 animate-pulse rounded-full bg-[#F59E0B]/20" style={{ animationDelay: "0.2s" }} />
        <div className="absolute -left-8 top-2 h-6 w-6 animate-pulse rounded-full bg-[#10B981]/20" style={{ animationDelay: "0.4s" }} />
        <div className="absolute -bottom-4 left-4 h-5 w-5 animate-pulse rounded-full bg-[#8B5CF6]/20" style={{ animationDelay: "0.6s" }} />
      </div>
      <p className="font-mono text-xs text-muted-foreground">Loading knowledge graph…</p>
    </div>
  );
}

function EmptyGraph() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
      <div className="grid h-16 w-16 place-items-center rounded-full border border-border bg-secondary/40">
        <Share2 className="h-7 w-7 text-muted-foreground" />
      </div>
      <div>
        <p className="font-semibold text-foreground">No incidents in graph</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Incidents will appear here once Morphic processes them through RCA.
        </p>
      </div>
      <Link
        to="/incidents"
        className="mt-1 inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
      >
        View incidents
      </Link>
    </div>
  );
}
