import { motion } from 'framer-motion';
import { 
  Download, 
  Filter, 
  Brain, 
  Rocket,
  ArrowRight,
  Database,
  AlertTriangle,
  GitPullRequest,
  Mail,
  Clock,
  Zap
} from 'lucide-react';

const layers = [
  {
    id: 'ingestion',
    title: 'Ingestion',
    subtitle: 'Layer 1',
    icon: Download,
    color: '#10B981',
    description: 'Poll logs every 30s with LogAI pipeline',
    details: [
      'Drain3 log parsing',
      'Deduplication by trace_id',
      'ASYNC-ORPHAN detection',
      'TF-IDF vectorization'
    ],
    stats: { label: 'Latency', value: '<30s' }
  },
  {
    id: 'triage',
    title: 'Triage',
    subtitle: 'Layer 2',
    icon: Filter,
    color: '#F59E0B',
    description: 'Classify severity and suppress noise',
    details: [
      'Severity classification',
      'Duplicate suppression',
      'Rate limiting',
      'Blast radius scoring'
    ],
    stats: { label: 'Accuracy', value: '94%' }
  },
  {
    id: 'rca',
    title: 'RCA',
    subtitle: 'Layer 3',
    icon: Brain,
    color: '#8B5CF6',
    description: 'AI-powered root cause analysis',
    details: [
      'Claude 3.5 Sonnet',
      'Structured JSON output',
      'Code fix generation',
      'Confidence scoring'
    ],
    stats: { label: 'Confidence', value: '0.94' }
  },
  {
    id: 'actions',
    title: 'Actions',
    subtitle: 'Layer 4',
    icon: Rocket,
    color: '#3B82F6',
    description: 'Automated remediation workflows',
    details: [
      'GitHub PR creation',
      'Email notifications',
      'Slack webhooks',
      'Custom webhooks'
    ],
    stats: { label: 'Auto-fix', value: '60s' }
  }
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.2
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.5, ease: [0.2, 0.8, 0.2, 1] }
  }
};

export function PipelineFlow() {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true }}
      className="relative"
    >
      {/* Connection Lines - Desktop */}
      <div className="hidden lg:block absolute top-1/2 left-0 right-0 -translate-y-1/2 h-0.5 bg-gradient-to-r from-[#10B981] via-[#F59E0B] via-[#8B5CF6] to-[#3B82F6] opacity-30" />
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {layers.map((layer, index) => (
          <motion.div
            key={layer.id}
            variants={itemVariants}
            className="relative group"
          >
            {/* Arrow connector */}
            {index < layers.length - 1 && (
              <div className="hidden lg:flex absolute top-8 -right-3 z-10">
                <ArrowRight className="w-5 h-5 text-[#3B82F6] opacity-50" />
              </div>
            )}

            <motion.div
              className="relative p-6 bg-[#161B22] border border-[#2D333B] rounded-xl overflow-hidden"
              whileHover={{ 
                y: -4, 
                borderColor: layer.color,
                transition: { duration: 0.2 }
              }}
            >
              {/* Glow effect on hover */}
              <div 
                className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                style={{ 
                  background: `radial-gradient(circle at 50% 0%, ${layer.color}15, transparent 70%)` 
                }}
              />

              <div className="relative z-10">
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div 
                    className="w-12 h-12 rounded-xl flex items-center justify-center"
                    style={{ backgroundColor: `${layer.color}15`, border: `1px solid ${layer.color}30` }}
                  >
                    <layer.icon className="w-6 h-6" style={{ color: layer.color }} />
                  </div>
                  <span className="text-xs text-[#6B7280] font-mono">{layer.subtitle}</span>
                </div>

                {/* Title */}
                <h3 className="text-xl font-semibold text-[#E6EDF3] mb-2">{layer.title}</h3>
                <p className="text-sm text-[#9DA7B3] mb-4 leading-relaxed">{layer.description}</p>

                {/* Details List */}
                <ul className="space-y-2 mb-4">
                  {layer.details.map((detail, i) => (
                    <li key={i} className="flex items-center gap-2 text-xs text-[#9DA7B3]">
                      <div 
                        className="w-1 h-1 rounded-full"
                        style={{ backgroundColor: layer.color }}
                      />
                      {detail}
                    </li>
                  ))}
                </ul>

                {/* Stats Badge */}
                <div 
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs"
                  style={{ 
                    backgroundColor: `${layer.color}15`, 
                    border: `1px solid ${layer.color}30`,
                    color: layer.color 
                  }}
                >
                  <Zap className="w-3 h-3" />
                  <span className="font-mono">{layer.stats.label}:</span>
                  <span className="font-semibold">{layer.stats.value}</span>
                </div>
              </div>
            </motion.div>
          </motion.div>
        ))}
      </div>

      {/* Data Flow Indicators */}
      <motion.div 
        className="mt-12 flex flex-wrap justify-center gap-8 text-sm text-[#6B7280]"
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ delay: 0.5 }}
      >
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-[#10B981]" />
          <span>PostgreSQL + Neo4j + Redis</span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-[#F59E0B]" />
          <span>30s Polling Interval</span>
        </div>
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-[#EF4444]" />
          <span>3 ML Detection Algorithms</span>
        </div>
        <div className="flex items-center gap-2">
          <GitPullRequest className="w-4 h-4 text-[#3B82F6]" />
          <span>Auto PR Creation</span>
        </div>
        <div className="flex items-center gap-2">
          <Mail className="w-4 h-4 text-[#8B5CF6]" />
          <span>Multi-Channel Alerts</span>
        </div>
      </motion.div>
    </motion.div>
  );
}
