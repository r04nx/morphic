import { motion } from 'framer-motion';
import { 
  AlertTriangle, 
  Clock, 
  Database, 
  Zap,
  Activity,
  XCircle,
  GitBranch,
  Server
} from 'lucide-react';
import { useState, useEffect } from 'react';

interface Scenario {
  id: string;
  type: string;
  impact: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  icon: React.ElementType;
  color: string;
  description: string;
  logPattern: string;
  service: string;
}

const scenarios: Scenario[] = [
  {
    id: 'gateway-timeout',
    type: 'GATEWAY_TIMEOUT',
    impact: 'Duplicate Payments',
    severity: 'CRITICAL',
    icon: Clock,
    color: '#EF4444',
    description: 'Payment gateway timeout causes client retry, creating duplicate payment records',
    logPattern: '{"error_type": "GATEWAY_TIMEOUT", "message": "Payment gateway did not respond"}',
    service: 'PaymentService'
  },
  {
    id: 'partial-write',
    type: 'PARTIAL_WRITE',
    impact: 'Orphaned Records',
    severity: 'HIGH',
    icon: Database,
    color: '#F59E0B',
    description: 'Payment recorded but order status update fails, leaving orphaned data',
    logPattern: '{"error_type": "ORDER_UPDATE_FAILURE", "orderId": "ORD-7829"}',
    service: 'OrderService'
  },
  {
    id: 'race-condition',
    type: 'RACE_CONDITION',
    impact: 'Negative Stock',
    severity: 'HIGH',
    icon: Zap,
    color: '#F59E0B',
    description: 'Concurrent requests bypass stock check due to non-atomic operations',
    logPattern: '{"error_type": "NEGATIVE_STOCK", "stock": -5, "productId": "PROD-001"}',
    service: 'InventoryService'
  },
  {
    id: 'async-orphan',
    type: 'ASYNC_ORPHAN',
    impact: 'Trace Loss',
    severity: 'MEDIUM',
    icon: GitBranch,
    color: '#8B5CF6',
    description: 'Background async jobs lose MDC context, breaking trace correlation',
    logPattern: '{"trace_id": "unknown", "message": "Async audit: verifying integrity"}',
    service: 'AuditService'
  },
  {
    id: 'inconsistent-state',
    type: 'INCONSISTENT_STATE',
    impact: 'Stuck Orders',
    severity: 'MEDIUM',
    icon: Server,
    color: '#6B7280',
    description: 'Order persisted before inventory reservation, leaving order stuck in CREATED',
    logPattern: '{"error_type": "INCONSISTENT_STATE", "status": "CREATED", "hasReservation": false}',
    service: 'OrderService'
  }
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2
    }
  }
};

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 }
};

export function ChaosScenarios() {
  const [activeScenario, setActiveScenario] = useState<string | null>(null);
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    let currentIndex = 0;
    const interval = setInterval(() => {
      setActiveScenario(scenarios[currentIndex].id);
      currentIndex = (currentIndex + 1) % scenarios.length;
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative">
      {/* Animated Background Grid */}
      <div className="absolute inset-0 opacity-10">
        <div className="grid grid-cols-6 gap-4 h-full">
          {[...Array(24)].map((_, i) => (
            <motion.div
              key={i}
              className="border border-[#2D333B] rounded-lg"
              animate={{
                opacity: [0.3, 0.6, 0.3],
                transition: {
                  duration: 2,
                  delay: i * 0.1,
                  repeat: Infinity
                }
              }}
            />
          ))}
        </div>
      </div>

      <div className="relative z-10">
        {/* Central Hub */}
        <div className="flex justify-center mb-8">
          <motion.div
            className="relative w-32 h-32"
            animate={{ rotate: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          >
            {/* Orbiting dots */}
            {[0, 72, 144, 216, 288].map((angle, i) => (
              <motion.div
                key={i}
                className="absolute w-3 h-3 rounded-full"
                style={{
                  backgroundColor: scenarios[i]?.color || '#3B82F6',
                  top: '50%',
                  left: '50%',
                  transform: `rotate(${angle}deg) translateX(60px) rotate(-${angle}deg)`
                }}
                animate={{
                  scale: activeScenario === scenarios[i]?.id ? 1.5 : 1,
                  boxShadow: activeScenario === scenarios[i]?.id 
                    ? `0 0 20px ${scenarios[i]?.color}` 
                    : 'none'
                }}
              />
            ))}
          </motion.div>

          {/* Center Logo */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
            <motion.div
              className="w-16 h-16 bg-[#161B22] border border-[#2D333B] rounded-xl flex items-center justify-center"
              animate={{
                boxShadow: [
                  '0 0 0 rgba(59, 130, 246, 0)',
                  '0 0 30px rgba(59, 130, 246, 0.3)',
                  '0 0 0 rgba(59, 130, 246, 0)'
                ]
              }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <Activity className="w-8 h-8 text-[#EF4444]" />
            </motion.div>
          </div>
        </div>

        {/* Scenario Cards */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="grid gap-3"
        >
          {scenarios.map((scenario) => (
            <motion.div
              key={scenario.id}
              variants={cardVariants}
              className={`relative p-4 bg-[#161B22] border rounded-lg cursor-pointer transition-all ${
                activeScenario === scenario.id 
                  ? 'border-[#3B82F6] ring-1 ring-[#3B82F6]' 
                  : 'border-[#2D333B] hover:border-[#4B5563]'
              }`}
              onClick={() => setActiveScenario(scenario.id)}
              whileHover={{ x: 4 }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div 
                    className="w-10 h-10 rounded-lg flex items-center justify-center"
                    style={{ 
                      backgroundColor: `${scenario.color}15`,
                      border: `1px solid ${scenario.color}30`
                    }}
                  >
                    <scenario.icon className="w-5 h-5" style={{ color: scenario.color }} />
                  </div>
                  
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono text-[#E6EDF3]">{scenario.type}</span>
                      <span 
                        className="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                        style={{ 
                          backgroundColor: `${scenario.color}20`,
                          color: scenario.color
                        }}
                      >
                        {scenario.severity}
                      </span>
                    </div>
                    <span className="text-xs text-[#6B7280]">{scenario.service}</span>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-sm text-[#9DA7B3]">{scenario.impact}</span>
                </div>
              </div>

              {/* Expanded Details */}
              <motion.div
                initial={false}
                animate={{
                  height: activeScenario === scenario.id ? 'auto' : 0,
                  opacity: activeScenario === scenario.id ? 1 : 0
                }}
                className="overflow-hidden"
              >
                <div className="mt-3 pt-3 border-t border-[#2D333B]">
                  <p className="text-xs text-[#9DA7B3] mb-2">{scenario.description}</p>
                  <div className="bg-[#0D1117] rounded p-2 font-mono text-[10px] text-[#6B7280] overflow-x-auto">
                    {scenario.logPattern}
                  </div>
                </div>
              </motion.div>
            </motion.div>
          ))}
        </motion.div>

        {/* Detection Badge */}
        <motion.div
          className="mt-6 flex justify-center"
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <div className="flex items-center gap-2 px-4 py-2 bg-[#161B22] border border-[#10B981] rounded-full">
            <div className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse" />
            <span className="text-xs text-[#10B981] font-medium">
              AI Detection Active — Monitoring {scenarios.length} Failure Patterns
            </span>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
