import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileCode, 
  Copy, 
  CheckCircle, 
  ChevronRight,
  Terminal,
  Database,
  GitBranch,
  Activity
} from 'lucide-react';

interface Endpoint {
  id: string;
  method: string;
  path: string;
  description: string;
  icon: React.ElementType;
  request?: string;
  response: string;
}

const endpoints: Endpoint[] = [
  {
    id: 'incidents',
    method: 'GET',
    path: '/api/incidents',
    description: 'Fetch all incidents with optional filtering',
    icon: Database,
    response: JSON.stringify({
      incidents: [
        {
          id: "inc-2847",
          trace_id: "a1b2c3d4",
          title: "Gateway Timeout - Duplicate Payment",
          status: "RESOLVED",
          blast_radius: "HIGH",
          confidence_score: 0.96,
          created_at: "2024-05-08T14:23:15Z"
        }
      ],
      total: 147,
      page: 1
    }, null, 2)
  },
  {
    id: 'graph',
    method: 'GET',
    path: '/api/graph/incidents/{id}',
    description: 'Get Neo4j graph visualization data for an incident',
    icon: GitBranch,
    response: JSON.stringify({
      nodes: [
        { id: "inc-2847", label: "INC-2847", type: "incident", status: "critical" },
        { id: "payment", label: "PaymentService", type: "service", status: "degraded" },
        { id: "postgres", label: "PostgreSQL", type: "database", status: "healthy" }
      ],
      edges: [
        { source: "inc-2847", target: "payment", type: "affects" },
        { source: "payment", target: "postgres", type: "uses" }
      ],
      blast_radius: "HIGH"
    }, null, 2)
  },
  {
    id: 'actions',
    method: 'POST',
    path: '/api/incidents/{id}/actions/github-pr',
    description: 'Trigger GitHub PR creation for an incident',
    icon: Activity,
    request: JSON.stringify({
      auto_merge: true,
      run_tests: true
    }, null, 2),
    response: JSON.stringify({
      action_id: "act-8923",
      status: "RUNNING",
      type: "GITHUB_PR",
      incident_id: "inc-2847",
      triggered_at: "2024-05-08T14:24:02Z",
      result: {
        pr_number: 2842,
        pr_url: "https://github.com/org/repo/pull/2842",
        branch: "morphic/fix-inc-2847",
        status: "created"
      }
    }, null, 2)
  },
  {
    id: 'rca',
    method: 'GET',
    path: '/api/incidents/{id}/rca',
    description: 'Get AI-generated Root Cause Analysis',
    icon: Terminal,
    response: JSON.stringify({
      rca: {
        classification: "GATEWAY_TIMEOUT",
        root_cause: "Payment gateway timeout caused client retry, creating duplicate payment records",
        blast_radius: "HIGH",
        impact: "Multiple charges for single order. Customer financial impact.",
        confidence_score: 0.96,
        suggested_fix: {
          language: "java",
          target_class: "PaymentService",
          patch: "@@ -45,7 +45,12 @@...",
          rationale: "Add idempotency key validation before processing payment"
        }
      }
    }, null, 2)
  }
];

const getMethodColor = (method: string) => {
  switch (method) {
    case 'GET': return '#10B981';
    case 'POST': return '#3B82F6';
    case 'PUT': return '#F59E0B';
    case 'DELETE': return '#EF4444';
    default: return '#6B7280';
  }
};

export function APIShowcase() {
  const [activeEndpoint, setActiveEndpoint] = useState(endpoints[0]);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="grid lg:grid-cols-5 gap-6">
      {/* Endpoint List */}
      <div className="lg:col-span-2 space-y-3">
        {endpoints.map((endpoint) => (
          <motion.button
            key={endpoint.id}
            onClick={() => setActiveEndpoint(endpoint)}
            className={`w-full text-left p-4 rounded-lg border transition-all ${
              activeEndpoint.id === endpoint.id
                ? 'bg-[#161B22] border-[#3B82F6]'
                : 'bg-[#0D1117] border-[#2D333B] hover:border-[#4B5563]'
            }`}
            whileHover={{ x: 2 }}
            whileTap={{ scale: 0.98 }}
          >
            <div className="flex items-start gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                activeEndpoint.id === endpoint.id ? 'bg-[#3B82F6]/20' : 'bg-[#161B22]'
              }`}>
                <endpoint.icon className={`w-5 h-5 ${
                  activeEndpoint.id === endpoint.id ? 'text-[#3B82F6]' : 'text-[#6B7280]'
                }`} />
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span 
                    className="text-xs font-mono font-semibold"
                    style={{ color: getMethodColor(endpoint.method) }}
                  >
                    {endpoint.method}
                  </span>
                  <span className="text-sm text-[#E6EDF3] font-mono truncate">
                    {endpoint.path}
                  </span>
                </div>
                <p className="text-xs text-[#6B7280]">{endpoint.description}</p>
              </div>

              <ChevronRight className={`w-4 h-4 transition-transform ${
                activeEndpoint.id === endpoint.id ? 'rotate-90 text-[#3B82F6]' : 'text-[#6B7280]'
              }`} />
            </div>
          </motion.button>
        ))}
      </div>

      {/* Code Display */}
      <div className="lg:col-span-3">
        <motion.div
          className="bg-[#0D1117] border border-[#2D333B] rounded-xl overflow-hidden"
          key={activeEndpoint.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-[#161B22] border-b border-[#2D333B]">
            <div className="flex items-center gap-2">
              <FileCode className="w-4 h-4 text-[#6B7280]" />
              <span className="text-sm text-[#9DA7B3]">Response</span>
            </div>
            <motion.button
              onClick={() => handleCopy(activeEndpoint.response, 'response')}
              className="flex items-center gap-1.5 px-2 py-1 text-xs text-[#6B7280] hover:text-[#E6EDF3] transition-colors"
              whileTap={{ scale: 0.95 }}
            >
              {copiedId === 'response' ? (
                <>
                  <CheckCircle className="w-3.5 h-3.5 text-[#10B981]" />
                  <span className="text-[#10B981]">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy</span>
                </>
              )}
            </motion.button>
          </div>

          {/* Request Body (if present) */}
          {activeEndpoint.request && (
            <div className="border-b border-[#2D333B]">
              <div className="flex items-center justify-between px-4 py-2 bg-[#111827]">
                <span className="text-xs text-[#6B7280]">Request Body</span>
              </div>
              <pre className="p-4 overflow-x-auto text-xs font-mono text-[#9DA7B3] bg-[#0D1117]">
                <code>{activeEndpoint.request}</code>
              </pre>
            </div>
          )}

          {/* Response Body */}
          <div>
            <div className="flex items-center justify-between px-4 py-2 bg-[#111827]">
              <span className="text-xs text-[#6B7280]">200 OK — Response Body</span>
              <span className="text-xs text-[#10B981]">application/json</span>
            </div>
            <pre className="p-4 overflow-x-auto text-xs font-mono text-[#9DA7B3] bg-[#0D1117] max-h-80 overflow-y-auto">
              <code>{activeEndpoint.response}</code>
            </pre>
          </div>

          {/* Footer Info */}
          <div className="px-4 py-3 bg-[#161B22] border-t border-[#2D333B] flex items-center justify-between text-xs">
            <span className="text-[#6B7280]">
              Base URL: <span className="text-[#9DA7B3]">https://api.morphic.dev/v1</span>
            </span>
            <span className="text-[#6B7280]">
              Authentication: <span className="text-[#F59E0B]">Bearer Token</span>
            </span>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
