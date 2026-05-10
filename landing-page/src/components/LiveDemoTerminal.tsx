import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Terminal, 
  Play, 
  Pause, 
  RotateCcw, 
  CheckCircle, 
  AlertTriangle, 
  Brain,
  GitPullRequest,
  Mail,
  Clock,
  Activity,
  Zap
} from 'lucide-react';

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  service: string;
  message: string;
  trace_id?: string;
}

interface DemoStage {
  id: string;
  title: string;
  icon: React.ElementType;
  status: 'pending' | 'active' | 'completed';
  description: string;
}

const demoLogs: LogEntry[] = [
  { id: '1', timestamp: '14:23:01', level: 'INFO', service: 'OrderService', message: 'Processing order ORDER-7829 for user-123' },
  { id: '2', timestamp: '14:23:02', level: 'INFO', service: 'OrderService', message: 'Reserved inventory for PROD-001 x2' },
  { id: '3', timestamp: '14:23:03', level: 'INFO', service: 'PaymentService', message: 'Initiating payment of $159.98', trace_id: 'a1b2c3d4' },
  { id: '4', timestamp: '14:23:08', level: 'WARN', service: 'PaymentService', message: 'Gateway timeout after 5000ms', trace_id: 'a1b2c3d4' },
  { id: '5', timestamp: '14:23:09', level: 'INFO', service: 'PaymentService', message: 'Retry attempt 1/3', trace_id: 'a1b2c3d4' },
  { id: '6', timestamp: '14:23:14', level: 'ERROR', service: 'PaymentService', message: 'Duplicate payment detected: PAY-2847, PAY-2848', trace_id: 'a1b2c3d4' },
  { id: '7', timestamp: '14:23:15', level: 'WARN', service: 'OrderService', message: 'Order status inconsistent: PAID but unfulfilled', trace_id: 'a1b2c3d4' },
];

const rcaResult = {
  classification: 'GATEWAY_TIMEOUT → DUPLICATE_PAYMENT',
  root_cause: 'Payment gateway timeout caused automatic retry without idempotency key validation, resulting in duplicate charges',
  blast_radius: 'HIGH',
  confidence: 0.96,
  affected_services: ['PaymentService', 'OrderService'],
  fix_summary: 'Add idempotency key validation in PaymentGatewayClient.processPayment()'
};

export function LiveDemoTerminal() {
  const [isPlaying, setIsPlaying] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [currentStage, setCurrentStage] = useState(0);
  const [showRCA, setShowRCA] = useState(false);
  const [showPR, setShowPR] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const stages: DemoStage[] = [
    { id: 'logs', title: 'Log Ingestion', icon: Terminal, status: currentStage >= 0 ? (currentStage > 0 ? 'completed' : 'active') : 'pending', description: 'Collecting logs from chaos backend' },
    { id: 'detect', title: 'Anomaly Detection', icon: AlertTriangle, status: currentStage >= 1 ? (currentStage > 1 ? 'completed' : 'active') : 'pending', description: 'LogAI identifies error patterns' },
    { id: 'rca', title: 'AI Analysis', icon: Brain, status: currentStage >= 2 ? (currentStage > 2 ? 'completed' : 'active') : 'pending', description: 'Claude generates RCA' },
    { id: 'fix', title: 'Auto-Remediation', icon: GitPullRequest, status: currentStage >= 3 ? 'completed' : 'pending', description: 'PR created with fix' },
  ];

  useEffect(() => {
    if (!isPlaying) return;

    let logIndex = 0;
    const startTime = Date.now();
    
    const timer = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
    }, 100);

    const interval = setInterval(() => {
      if (logIndex < demoLogs.length) {
        setLogs(prev => [...prev, demoLogs[logIndex]]);
        
        // Trigger stage changes based on log content
        if (demoLogs[logIndex].level === 'ERROR') {
          setTimeout(() => setCurrentStage(1), 500);
        }
        
        logIndex++;
      } else {
        // All logs processed - trigger RCA
        setTimeout(() => {
          setCurrentStage(2);
          setShowRCA(true);
          
          setTimeout(() => {
            setCurrentStage(3);
            setShowPR(true);
          }, 2000);
        }, 500);
        
        clearInterval(interval);
      }
    }, 800);

    return () => {
      clearInterval(interval);
      clearInterval(timer);
    };
  }, [isPlaying]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const handleReset = () => {
    setIsPlaying(false);
    setLogs([]);
    setCurrentStage(0);
    setShowRCA(false);
    setShowPR(false);
    setElapsedTime(0);
  };

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      {/* Main Terminal */}
      <div className="lg:col-span-2">
        <motion.div
          className="bg-[#0D1117] border border-[#2D333B] rounded-xl overflow-hidden"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          {/* Terminal Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-[#161B22] border-b border-[#2D333B]">
            <div className="flex items-center gap-3">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-[#EF4444]" />
                <div className="w-3 h-3 rounded-full bg-[#F59E0B]" />
                <div className="w-3 h-3 rounded-full bg-[#10B981]" />
              </div>
              <span className="text-xs text-[#6B7280] font-mono">morphic-orchestrator — bash</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-[#6B7280] font-mono">
                {elapsedTime.toFixed(1)}s
              </span>
              <motion.button
                onClick={() => setIsPlaying(!isPlaying)}
                className="p-1.5 hover:bg-[#2D333B] rounded transition-colors"
                whileTap={{ scale: 0.95 }}
              >
                {isPlaying ? (
                  <Pause className="w-4 h-4 text-[#9DA7B3]" />
                ) : (
                  <Play className="w-4 h-4 text-[#10B981]" />
                )}
              </motion.button>
              <motion.button
                onClick={handleReset}
                className="p-1.5 hover:bg-[#2D333B] rounded transition-colors"
                whileTap={{ scale: 0.95 }}
              >
                <RotateCcw className="w-4 h-4 text-[#9DA7B3]" />
              </motion.button>
            </div>
          </div>

          {/* Log Output */}
          <div className="h-80 overflow-y-auto p-4 font-mono text-xs">
            <AnimatePresence>
              {logs.length === 0 && !isPlaying && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="h-full flex flex-col items-center justify-center text-[#6B7280]"
                >
                  <Terminal className="w-8 h-8 mb-3 opacity-50" />
                  <p>Click play to start the demo</p>
                </motion.div>
              )}

              {logs.map((log, index) => (
                <motion.div
                  key={log.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="mb-1.5"
                >
                  <span className="text-[#6B7280]">[{log.timestamp}]</span>
                  <span className={`ml-2 px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                    log.level === 'ERROR' ? 'bg-[#EF4444]/20 text-[#EF4444]' :
                    log.level === 'WARN' ? 'bg-[#F59E0B]/20 text-[#F59E0B]' :
                    'bg-[#10B981]/20 text-[#10B981]'
                  }`}>
                    {log.level}
                  </span>
                  <span className="ml-2 text-[#8B5CF6]">{log.service}</span>
                  <span className="ml-2 text-[#9DA7B3]">{log.message}</span>
                  {log.trace_id && (
                    <span className="ml-2 text-[#3B82F6]">trace={log.trace_id}</span>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Blinking Cursor */}
            {isPlaying && (
              <motion.span
                className="inline-block w-2 h-4 bg-[#3B82F6] ml-1"
                animate={{ opacity: [1, 0] }}
                transition={{ repeat: Infinity, duration: 0.8 }}
              />
            )}
            <div ref={logsEndRef} />
          </div>

          {/* Progress Bar */}
          {isPlaying && (
            <div className="h-1 bg-[#161B22]">
              <motion.div
                className="h-full bg-gradient-to-r from-[#10B981] via-[#F59E0B] to-[#3B82F6]"
                initial={{ width: '0%' }}
                animate={{ width: `${(logs.length / demoLogs.length) * 100}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
          )}
        </motion.div>
      </div>

      {/* Side Panel - Stage Progress & Results */}
      <div className="space-y-4">
        {/* Pipeline Stages */}
        <motion.div
          className="bg-[#161B22] border border-[#2D333B] rounded-xl p-4"
          initial={{ opacity: 0, x: 20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
        >
          <h3 className="text-sm font-semibold text-[#E6EDF3] mb-4">Pipeline Progress</h3>
          <div className="space-y-3">
            {stages.map((stage, index) => (
              <motion.div
                key={stage.id}
                className={`flex items-center gap-3 p-2 rounded-lg transition-colors ${
                  stage.status === 'active' ? 'bg-[#3B82F6]/10 border border-[#3B82F6]/30' :
                  stage.status === 'completed' ? 'bg-[#10B981]/10' :
                  'opacity-50'
                }`}
                animate={stage.status === 'active' ? {
                  boxShadow: [
                    '0 0 0 rgba(59, 130, 246, 0)',
                    '0 0 20px rgba(59, 130, 246, 0.2)',
                    '0 0 0 rgba(59, 130, 246, 0)'
                  ]
                } : {}}
                transition={{ duration: 1.5, repeat: Infinity }}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                  stage.status === 'completed' ? 'bg-[#10B981]/20' :
                  stage.status === 'active' ? 'bg-[#3B82F6]/20' :
                  'bg-[#2D333B]'
                }`}>
                  {stage.status === 'completed' ? (
                    <CheckCircle className="w-4 h-4 text-[#10B981]" />
                  ) : (
                    <stage.icon className={`w-4 h-4 ${
                      stage.status === 'active' ? 'text-[#3B82F6]' : 'text-[#6B7280]'
                    }`} />
                  )}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-[#E6EDF3]">{stage.title}</p>
                  <p className="text-xs text-[#6B7280]">{stage.description}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* RCA Card */}
        <AnimatePresence>
          {showRCA && (
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className="bg-[#161B22] border border-[#8B5CF6] rounded-xl p-4"
            >
              <div className="flex items-center gap-2 mb-3">
                <Brain className="w-4 h-4 text-[#8B5CF6]" />
                <span className="text-sm font-semibold text-[#E6EDF3]">AI Analysis Complete</span>
                <span className="ml-auto text-xs px-2 py-0.5 bg-[#8B5CF6]/20 text-[#8B5CF6] rounded">
                  {(rcaResult.confidence * 100).toFixed(0)}%
                </span>
              </div>
              
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Type:</span>
                  <span className="text-[#F59E0B] font-mono text-xs">{rcaResult.classification}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#6B7280]">Impact:</span>
                  <span className="text-[#EF4444] font-semibold">{rcaResult.blast_radius}</span>
                </div>
                <p className="text-xs text-[#9DA7B3] mt-2 leading-relaxed">
                  {rcaResult.root_cause}
                </p>
                <div className="pt-2 border-t border-[#2D333B]">
                  <p className="text-xs text-[#6B7280]">Suggested Fix:</p>
                  <p className="text-xs text-[#10B981] font-mono mt-1">{rcaResult.fix_summary}</p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* PR Card */}
        <AnimatePresence>
          {showPR && (
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className="bg-[#161B22] border border-[#3B82F6] rounded-xl p-4"
            >
              <div className="flex items-center gap-2 mb-3">
                <GitPullRequest className="w-4 h-4 text-[#3B82F6]" />
                <span className="text-sm font-semibold text-[#E6EDF3]">PR #2842 Created</span>
                <motion.div
                  className="ml-auto"
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                >
                  <Zap className="w-4 h-4 text-[#3B82F6]" />
                </motion.div>
              </div>
              
              <p className="text-xs text-[#9DA7B3] mb-2">
                fix(payment): add idempotency key validation to prevent duplicate payments
              </p>
              
              <div className="flex items-center gap-4 text-xs">
                <span className="flex items-center gap-1 text-[#10B981]">
                  <CheckCircle className="w-3 h-3" />
                  Tests passing
                </span>
                <span className="text-[#6B7280]">+127 / -23 lines</span>
              </div>

              <div className="mt-3 pt-3 border-t border-[#2D333B] flex items-center justify-between">
                <span className="text-xs text-[#6B7280]">Auto-merge enabled</span>
                <motion.div
                  className="w-24 h-1.5 bg-[#2D333B] rounded-full overflow-hidden"
                >
                  <motion.div
                    className="h-full bg-[#10B981]"
                    initial={{ width: '0%' }}
                    animate={{ width: '100%' }}
                    transition={{ duration: 2 }}
                  />
                </motion.div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Metrics */}
        <motion.div
          className="bg-[#161B22] border border-[#2D333B] rounded-xl p-4"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.4 }}
        >
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-[#3B82F6]">47s</div>
              <div className="text-xs text-[#6B7280]">Detection → Fix</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-[#10B981]">$0</div>
              <div className="text-xs text-[#6B7280]">Downtime Cost</div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
