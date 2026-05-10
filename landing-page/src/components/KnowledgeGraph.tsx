import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Network, 
  AlertTriangle, 
  Server, 
  Database, 
  Shield,
  Zap,
  Activity,
  GitBranch,
  Cpu
} from 'lucide-react';

interface Node {
  id: string;
  x: number;
  y: number;
  label: string;
  type: 'incident' | 'service' | 'database' | 'gateway';
  status: 'healthy' | 'degraded' | 'critical';
  connections: string[];
}

const nodes: Node[] = [
  { id: 'incident-1', x: 400, y: 200, label: 'INC-2847', type: 'incident', status: 'critical', connections: ['payment', 'order'] },
  { id: 'payment', x: 300, y: 300, label: 'PaymentService', type: 'service', status: 'critical', connections: ['postgres', 'redis'] },
  { id: 'order', x: 500, y: 300, label: 'OrderService', type: 'service', status: 'degraded', connections: ['postgres', 'neo4j'] },
  { id: 'inventory', x: 400, y: 400, label: 'InventoryService', type: 'service', status: 'healthy', connections: ['postgres'] },
  { id: 'gateway', x: 400, y: 100, label: 'API Gateway', type: 'gateway', status: 'healthy', connections: ['incident-1'] },
  { id: 'postgres', x: 200, y: 500, label: 'PostgreSQL', type: 'database', status: 'healthy', connections: [] },
  { id: 'redis', x: 400, y: 500, label: 'Redis', type: 'database', status: 'healthy', connections: [] },
  { id: 'neo4j', x: 600, y: 500, label: 'Neo4j', type: 'database', status: 'healthy', connections: [] }
];

const getNodeIcon = (type: string) => {
  switch (type) {
    case 'incident': return AlertTriangle;
    case 'service': return Server;
    case 'database': return Database;
    case 'gateway': return Shield;
    default: return Activity;
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'critical': return '#EF4444';
    case 'degraded': return '#F59E0B';
    case 'healthy': return '#10B981';
    default: return '#6B7280';
  }
};

export function KnowledgeGraph() {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [pulseNodes, setPulseNodes] = useState<string[]>(['incident-1', 'payment']);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      setPulseNodes(prev => {
        const next = [...prev];
        if (next.includes('incident-1')) {
          return ['payment', 'postgres'];
        } else if (next.includes('postgres')) {
          return ['order', 'neo4j'];
        }
        return ['incident-1', 'payment'];
      });
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative bg-[#0D1117] border border-[#2D333B] rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-[#161B22] border-b border-[#2D333B]">
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-[#8B5CF6]" />
          <span className="text-sm font-semibold text-[#E6EDF3]">Incident Topology</span>
        </div>
        <div className="flex items-center gap-4 text-xs text-[#6B7280]">
          <span className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-[#EF4444]" />
            Critical
          </span>
          <span className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-[#F59E0B]" />
            Degraded
          </span>
          <span className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-[#10B981]" />
            Healthy
          </span>
        </div>
      </div>

      {/* Graph Visualization */}
      <div className="relative h-[400px] overflow-hidden">
        <svg 
          ref={svgRef}
          viewBox="0 0 800 600" 
          className="w-full h-full"
          style={{ background: '#0D1117' }}
        >
          {/* Grid Background */}
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#2D333B" strokeWidth="0.5" opacity="0.3" />
            </pattern>
            
            {/* Glow Filter */}
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* Arrow Marker */}
            <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
              <polygon points="0 0, 10 3, 0 6" fill="#3B82F6" opacity="0.6" />
            </marker>
          </defs>
          
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Connection Lines */}
          {nodes.map(node => 
            node.connections.map(targetId => {
              const target = nodes.find(n => n.id === targetId);
              if (!target) return null;
              
              const isPulsing = pulseNodes.includes(node.id) && pulseNodes.includes(targetId);
              
              return (
                <motion.line
                  key={`${node.id}-${targetId}`}
                  x1={node.x}
                  y1={node.y}
                  x2={target.x}
                  y2={target.y}
                  stroke="#3B82F6"
                  strokeWidth={isPulsing ? 2 : 1}
                  opacity={isPulsing ? 0.8 : 0.3}
                  markerEnd="url(#arrowhead)"
                  animate={isPulsing ? {
                    strokeDasharray: ["5,5", "10,5", "5,5"],
                    strokeDashoffset: [0, -15, 0]
                  } : {}}
                  transition={isPulsing ? {
                    duration: 1,
                    repeat: Infinity,
                    ease: "linear"
                  } : {}}
                />
              );
            })
          )}

          {/* Nodes */}
          {nodes.map(node => {
            const Icon = getNodeIcon(node.type);
            const color = getStatusColor(node.status);
            const isHovered = hoveredNode === node.id;
            const isPulsing = pulseNodes.includes(node.id);

            return (
              <motion.g
                key={node.id}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ 
                  scale: isHovered ? 1.1 : 1, 
                  opacity: 1,
                }}
                transition={{ duration: 0.3 }}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                style={{ cursor: 'pointer' }}
              >
                {/* Node Circle */}
                <motion.circle
                  cx={node.x}
                  cy={node.y}
                  r={isHovered ? 32 : 28}
                  fill="#161B22"
                  stroke={color}
                  strokeWidth={isHovered ? 3 : 2}
                  filter={isHovered ? "url(#glow)" : undefined}
                  animate={isPulsing ? {
                    strokeWidth: [2, 4, 2],
                    strokeOpacity: [0.5, 1, 0.5]
                  } : {}}
                  transition={isPulsing ? {
                    duration: 1.5,
                    repeat: Infinity
                  } : {}}
                />

                {/* Icon */}
                <foreignObject
                  x={node.x - 10}
                  y={node.y - 10}
                  width={20}
                  height={20}
                >
                  <div className="flex items-center justify-center w-full h-full">
                    <Icon 
                      className="w-5 h-5" 
                      style={{ color }}
                    />
                  </div>
                </foreignObject>

                {/* Label */}
                <text
                  x={node.x}
                  y={node.y + 45}
                  textAnchor="middle"
                  fill="#9DA7B3"
                  fontSize="11"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {node.label}
                </text>

                {/* Status Indicator */}
                <circle
                  cx={node.x + 20}
                  cy={node.y - 20}
                  r={5}
                  fill={color}
                >
                  <animate
                    attributeName="opacity"
                    values="1;0.5;1"
                    dur="2s"
                    repeatCount="indefinite"
                  />
                </circle>
              </motion.g>
            );
          })}

          {/* Blast Radius Indicator */}
          <motion.circle
            cx={400}
            cy={250}
            r={120}
            fill="none"
            stroke="#EF4444"
            strokeWidth={2}
            strokeDasharray="5,5"
            opacity={0.5}
            animate={{
              r: [100, 140, 100],
              opacity: [0.3, 0.6, 0.3]
            }}
            transition={{
              duration: 3,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          />
          
          <text x={520} y={200} fill="#EF4444" fontSize="10" fontFamily="JetBrains Mono, monospace">
            BLAST RADIUS: HIGH
          </text>
        </svg>

        {/* Overlay Stats */}
        <div className="absolute bottom-4 left-4 right-4 flex justify-between">
          <div className="flex gap-4">
            <div className="px-3 py-2 bg-[#161B22]/90 backdrop-blur-sm border border-[#2D333B] rounded-lg">
              <div className="text-xs text-[#6B7280]">Services Affected</div>
              <div className="text-lg font-semibold text-[#EF4444]">2/4</div>
            </div>
            <div className="px-3 py-2 bg-[#161B22]/90 backdrop-blur-sm border border-[#2D333B] rounded-lg">
              <div className="text-xs text-[#6B7280]">Trace Depth</div>
              <div className="text-lg font-semibold text-[#8B5CF6]">3 hops</div>
            </div>
          </div>

          <motion.div
            className="px-3 py-2 bg-[#161B22]/90 backdrop-blur-sm border border-[#3B82F6] rounded-lg flex items-center gap-2"
            animate={{
              boxShadow: [
                '0 0 0 rgba(59, 130, 246, 0)',
                '0 0 20px rgba(59, 130, 246, 0.3)',
                '0 0 0 rgba(59, 130, 246, 0)'
              ]
            }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            <Cpu className="w-4 h-4 text-[#3B82F6]" />
            <span className="text-xs text-[#E6EDF3]">AI Analysis Running</span>
          </motion.div>
        </div>
      </div>

      {/* Neo4j Query Example */}
      <div className="px-4 py-3 bg-[#111827] border-t border-[#2D333B]">
        <div className="flex items-center justify-between">
          <span className="text-xs text-[#6B7280] font-mono">Cypher Query</span>
          <GitBranch className="w-3 h-3 text-[#8B5CF6]" />
        </div>
        <code className="text-xs text-[#9DA7B3] font-mono mt-1 block">
          MATCH (i:Incident)-[:AFFECTS]-&gt;(s:Service)-[:DEPENDS_ON]-&gt;(d:Database)
          WHERE i.id = "INC-2847" RETURN s.name, d.name, i.blast_radius
        </code>
      </div>
    </div>
  );
}
