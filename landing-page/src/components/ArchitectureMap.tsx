import { motion } from 'framer-motion';
import { 
  Server, 
  Database, 
  Brain, 
  Github,
  Mail,
  Activity,
  Layers,
  Network,
  Cpu,
  Terminal,
  Zap,
  Shield,
  Clock
} from 'lucide-react';

interface ArchitectureNode {
  id: string;
  label: string;
  icon: React.ElementType;
  color: string;
  description: string;
  tech: string;
  x: number;
  y: number;
  layer: 'frontend' | 'backend' | 'data' | 'external';
}

const nodes: ArchitectureNode[] = [
  // Frontend Layer
  { id: 'react', label: 'React Dashboard', icon: Layers, color: '#61DAFB', description: 'Real-time incident feed', tech: 'React + TypeScript', x: 100, y: 50, layer: 'frontend' },
  { id: 'cytoscape', label: 'Cytoscape.js', icon: Network, color: '#8B5CF6', description: 'Interactive graph visualization', tech: 'Graph Library', x: 250, y: 50, layer: 'frontend' },
  
  // Backend Layer
  { id: 'flask', label: 'Flask API', icon: Server, color: '#000000', description: 'REST API endpoints', tech: 'Python 3.11', x: 100, y: 200, layer: 'backend' },
  { id: 'scheduler', label: 'APScheduler', icon: Clock, color: '#F59E0B', description: '30s polling jobs', tech: 'Background Tasks', x: 250, y: 200, layer: 'backend' },
  { id: 'logai', label: 'LogAI Pipeline', icon: Terminal, color: '#10B981', description: 'Drain3 + ML detection', tech: 'Log Parser + ML', x: 400, y: 200, layer: 'backend' },
  { id: 'agents', label: 'Agent Orchestrator', icon: Cpu, color: '#8B5CF6', description: 'Multi-agent coordination', tech: 'Pipeline Controller', x: 550, y: 200, layer: 'backend' },
  
  // Data Layer
  { id: 'postgres', label: 'PostgreSQL', icon: Database, color: '#336791', description: 'Incidents + Actions', tech: 'Primary Database', x: 100, y: 350, layer: 'data' },
  { id: 'neo4j', label: 'Neo4j', icon: Network, color: '#008CC1', description: 'Trace graphs', tech: 'Graph Database', x: 250, y: 350, layer: 'data' },
  { id: 'redis', label: 'Redis', icon: Zap, color: '#DC382D', description: 'Caching + Dedup', tech: 'In-Memory Store', x: 400, y: 350, layer: 'data' },
  
  // External Services
  { id: 'claude', label: 'Claude AI', icon: Brain, color: '#D97757', description: 'RCA + Code Generation', tech: 'Anthropic API', x: 550, y: 350, layer: 'external' },
  { id: 'github', label: 'GitHub', icon: Github, color: '#FFFFFF', description: 'PR Automation', tech: 'REST API', x: 700, y: 200, layer: 'external' },
  { id: 'email', label: 'SMTP', icon: Mail, color: '#3B82F6', description: 'Alert Notifications', tech: 'Email Service', x: 700, y: 350, layer: 'external' },
  { id: 'chaos', label: 'Chaos Backend', icon: Shield, color: '#EF4444', description: 'Spring Boot Test Target', tech: 'Java 17', x: 700, y: 50, layer: 'external' },
];

const connections = [
  { from: 'react', to: 'flask' },
  { from: 'cytoscape', to: 'neo4j' },
  { from: 'flask', to: 'scheduler' },
  { from: 'flask', to: 'logai' },
  { from: 'flask', to: 'agents' },
  { from: 'scheduler', to: 'postgres' },
  { from: 'logai', to: 'redis' },
  { from: 'agents', to: 'claude' },
  { from: 'agents', to: 'github' },
  { from: 'agents', to: 'email' },
  { from: 'postgres', to: 'neo4j' },
  { from: 'chaos', to: 'logai' },
];

const layerLabels = {
  frontend: { label: 'Frontend', y: 50 },
  backend: { label: 'Backend', y: 200 },
  data: { label: 'Data Layer', y: 350 },
  external: { label: 'External APIs', y: 200 }
};

export function ArchitectureMap() {
  return (
    <motion.div
      className="bg-[#0D1117] border border-[#2D333B] rounded-xl overflow-hidden"
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-[#161B22] border-b border-[#2D333B]">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#3B82F6]" />
          <span className="text-sm font-semibold text-[#E6EDF3]">System Architecture</span>
        </div>
        <div className="flex items-center gap-4 text-xs text-[#6B7280]">
          <span className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-[#10B981]" />
            Production Ready
          </span>
          <span className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-[#3B82F6]" />
            Docker Deployable
          </span>
        </div>
      </div>

      {/* Architecture Diagram */}
      <div className="relative h-[500px] overflow-auto p-6">
        <svg viewBox="0 0 850 450" className="w-full h-full">
          {/* Grid Background */}
          <defs>
            <pattern id="arch-grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#2D333B" strokeWidth="0.5" opacity="0.3" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#arch-grid)" />

          {/* Layer Dividers */}
          <line x1="0" y1="125" x2="850" y2="125" stroke="#2D333B" strokeWidth="1" strokeDasharray="5,5" />
          <line x1="0" y1="275" x2="850" y2="275" stroke="#2D333B" strokeWidth="1" strokeDasharray="5,5" />

          {/* Layer Labels */}
          <text x="20" y="90" fill="#6B7280" fontSize="12" fontWeight="500">Frontend</text>
          <text x="20" y="240" fill="#6B7280" fontSize="12" fontWeight="500">Backend</text>
          <text x="20" y="390" fill="#6B7280" fontSize="12" fontWeight="500">Data Layer</text>
          <text x="750" y="140" fill="#6B7280" fontSize="12" fontWeight="500">External</text>

          {/* Connections */}
          {connections.map((conn, i) => {
            const fromNode = nodes.find(n => n.id === conn.from);
            const toNode = nodes.find(n => n.id === conn.to);
            if (!fromNode || !toNode) return null;

            return (
              <motion.line
                key={`${conn.from}-${conn.to}`}
                x1={fromNode.x + 50}
                y1={fromNode.y + 25}
                x2={toNode.x + 50}
                y2={toNode.y + 25}
                stroke="#3B82F6"
                strokeWidth="1.5"
                opacity="0.4"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 0.5, delay: i * 0.05 }}
              />
            );
          })}

          {/* Nodes */}
          {nodes.map((node, i) => (
            <motion.g
              key={node.id}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: i * 0.05, duration: 0.3 }}
              className="cursor-pointer"
            >
              {/* Node Background */}
              <rect
                x={node.x}
                y={node.y}
                width="100"
                height="50"
                rx="8"
                fill="#161B22"
                stroke={node.color}
                strokeWidth="1.5"
              />

              {/* Icon */}
              <foreignObject
                x={node.x + 8}
                y={node.y + 15}
                width="20"
                height="20"
              >
                <div className="flex items-center justify-center w-full h-full">
                  <node.icon 
                    className="w-5 h-5" 
                    style={{ color: node.color }}
                  />
                </div>
              </foreignObject>

              {/* Label */}
              <text
                x={node.x + 35}
                y={node.y + 22}
                fill="#E6EDF3"
                fontSize="10"
                fontWeight="500"
              >
                {node.label}
              </text>

              {/* Tech */}
              <text
                x={node.x + 35}
                y={node.y + 38}
                fill="#6B7280"
                fontSize="8"
              >
                {node.tech}
              </text>
            </motion.g>
          ))}

          {/* Data Flow Animation */}
          <motion.circle
            r={4}
            fill="#3B82F6"
            initial={{ opacity: 0, cx: 150, cy: 225 }}
            animate={{
              opacity: [0, 1, 0],
              cx: [150, 300, 450],
              cy: [225, 225, 225]
            }}
            transition={{
              duration: 3,
              repeat: Infinity,
              ease: "linear"
            }}
          />
        </svg>
      </div>

      {/* Stats Footer */}
      <div className="grid grid-cols-4 gap-4 px-4 py-3 bg-[#161B22] border-t border-[#2D333B]">
        {[
          { label: 'Services', value: '13' },
          { label: 'Databases', value: '3' },
          { label: 'AI Agents', value: '4' },
          { label: 'APIs', value: '8' }
        ].map((stat) => (
          <div key={stat.label} className="text-center">
            <div className="text-lg font-bold text-[#E6EDF3]">{stat.value}</div>
            <div className="text-xs text-[#6B7280]">{stat.label}</div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
