import { createFileRoute } from '@tanstack/react-router';
import { useEffect, useState, useMemo } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import { Activity } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

cytoscape.use(dagre);

export const Route = createFileRoute('/graph')({
  component: GraphRoute,
});

const API_URL = "/api/graph/incidents";

function GraphRoute() {
  const [data, setData] = useState<{ nodes: any[]; edges: any[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIncident, setSelectedIncident] = useState<any | null>(null);
  const [mounted, setMounted] = useState(false);

  const fetchData = async () => {
    try {
      const res = await fetch(API_URL);
      if (!res.ok) throw new Error("Failed to fetch graph data");
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setMounted(true);
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const elements = useMemo(() => {
    if (!data) return [];
    return [...data.nodes, ...data.edges];
  }, [data]);

  const style = useMemo(() => {
    return [
      {
        selector: 'node',
        style: {
          'background-color': '#888',
          'label': 'data(label)',
          'color': '#fff',
          'font-size': '10px',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': '4px',
          'width': 30,
          'height': 30,
          'border-width': 0,
        }
      },
      {
        selector: 'node[type = "incident"]',
        style: {
          'shape': 'hexagon',
          'width': (ele: any) => {
            const sev = ele.data('severity');
            if (sev === 'CRITICAL') return 50;
            if (sev === 'HIGH') return 40;
            if (sev === 'MEDIUM') return 30;
            return 20;
          },
          'height': (ele: any) => {
            const sev = ele.data('severity');
            if (sev === 'CRITICAL') return 50;
            if (sev === 'HIGH') return 40;
            if (sev === 'MEDIUM') return 30;
            return 20;
          },
          'background-color': (ele: any) => {
            const sev = ele.data('severity');
            if (sev === 'CRITICAL') return '#EF4444';
            if (sev === 'HIGH') return '#F59E0B';
            if (sev === 'MEDIUM') return '#8B5CF6';
            return '#3B82F6';
          }
        }
      },
      {
        selector: 'node[type = "service"]',
        style: {
          'background-color': '#10B981',
          'shape': 'round-rectangle',
          'width': 40,
          'height': 40,
        }
      },
      {
        selector: 'node[type = "user"]',
        style: {
          'background-color': '#06B6D4',
          'shape': 'ellipse',
          'width': 25,
          'height': 25,
        }
      },
      {
        selector: 'node[type = "order"]',
        style: {
          'background-color': '#F59E0B',
          'shape': 'diamond',
          'width': 30,
          'height': 30,
        }
      },
      {
        selector: 'node[type = "javaclass"]',
        style: {
          'background-color': '#EAB308',
          'shape': 'barrel',
          'width': 35,
          'height': 35,
        }
      },
      {
        selector: 'edge',
        style: {
          'width': 2,
          'line-color': '#334155',
          'target-arrow-color': '#334155',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'label': 'data(label)',
          'font-size': '8px',
          'color': '#94A3B8',
          'text-rotation': 'autorotate',
          'text-background-opacity': 1,
          'text-background-color': '#0D1117',
          'text-background-padding': '2px',
        }
      }
    ];
  }, []);

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-140px)] flex-col gap-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="flex-1 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center text-red-400">
        Error loading graph: {error}
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div className="flex h-[calc(100vh-140px)] flex-col items-center justify-center text-muted-foreground">
        <Activity className="h-12 w-12 mb-4 opacity-20" />
        <p className="text-lg">No incidents found in Neo4j.</p>
        <p className="text-sm">Wait for the ingestion pipeline or check backend.</p>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-100px)] flex-col rounded-lg border border-border bg-[#0D1117] overflow-hidden relative shadow-2xl ring-1 ring-white/10">
      <div className="flex h-12 items-center justify-between border-b border-border/50 bg-[#0D1117]/80 px-4 backdrop-blur">
        <div className="font-semibold text-white/90">Threat Intelligence Graph</div>
        <div className="flex items-center gap-4 text-xs font-mono text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-[#EF4444]"></div>
            Critical
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-[#F59E0B]"></div>
            High
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-[#10B981]"></div>
            Service
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-[#06B6D4]"></div>
            User
          </div>
          <div className="ml-4 border-l border-border/50 pl-4">
            Nodes: <span className="text-white">{data.nodes.length}</span>
          </div>
          <div>
            Edges: <span className="text-white">{data.edges.length}</span>
          </div>
        </div>
      </div>
      
      <div className="flex-1 relative">
        {mounted ? (
          <CytoscapeComponent
          elements={elements}
          style={{ width: '100%', height: '100%', background: '#0D1117' }}
          stylesheet={style as any}
          layout={{ name: 'dagre', rankDir: 'TB', fit: true, padding: 50, spacingFactor: 1.2 } as any}
          cy={(cy) => {
            cy.on('tap', 'node', (evt) => {
              const nodeData = evt.target.data();
              if (nodeData.type === 'incident') {
                setSelectedIncident(nodeData);
              } else {
                setSelectedIncident(null);
              }
            });
            cy.on('tap', (evt) => {
              if (evt.target === cy) {
                setSelectedIncident(null);
              }
            });
          }}
        />
        ) : null}
        
        {selectedIncident && (
          <div className="absolute right-4 top-4 w-80 rounded-md border border-border/50 bg-[#161B22]/95 p-4 shadow-xl backdrop-blur-sm">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-semibold text-white/90">Incident Details</h3>
              <button 
                onClick={() => setSelectedIncident(null)}
                className="text-muted-foreground hover:text-white"
              >
                ✕
              </button>
            </div>
            <div className="space-y-3 text-sm">
              <div>
                <div className="text-xs text-muted-foreground mb-1">Trace ID</div>
                <div className="font-mono text-xs text-white break-all bg-black/30 p-1.5 rounded border border-white/5">
                  {selectedIncident.trace_id}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Classification</div>
                <div className="text-white/90">{selectedIncident.classification || "Unknown"}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Confidence Score</div>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-full bg-black/50 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-500" 
                      style={{ width: `${Math.min(100, Math.max(0, selectedIncident.confidence * 100))}%` }}
                    />
                  </div>
                  <div className="font-mono text-xs text-white">
                    {(selectedIncident.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
              {selectedIncident.root_cause && (
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Root Cause</div>
                  <div className="text-white/80 line-clamp-4 text-xs bg-black/20 p-2 rounded border border-white/5">
                    {selectedIncident.root_cause}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
