import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, CheckCircle, AlertTriangle, Brain, GitPullRequest, Mail, Activity } from 'lucide-react';

interface LogEntry {
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
  trace_id?: string;
  service?: string;
}

interface PipelineStep {
  id: string;
  icon: React.ElementType;
  label: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  color: string;
}

const mockLogs: LogEntry[] = [
  { timestamp: '2024-05-08T14:23:01.123Z', level: 'INFO', message: 'OrderService: Processing order ORDER-7829', service: 'OrderService' },
  { timestamp: '2024-05-08T14:23:01.234Z', level: 'INFO', message: 'PaymentService: Initiating payment for ORDER-7829', service: 'PaymentService' },
  { timestamp: '2024-05-08T14:23:06.789Z', level: 'WARN', message: 'PaymentService: Gateway timeout after 5000ms', service: 'PaymentService', trace_id: 'a1b2c3d4' },
  { timestamp: '2024-05-08T14:23:07.012Z', level: 'ERROR', message: 'PaymentService: Duplicate payment detected for ORDER-7829', service: 'PaymentService', trace_id: 'a1b2c3d4' },
];

const rcaOutput = {
  classification: 'GATEWAY_TIMEOUT',
  root_cause: 'Payment gateway timeout caused client retry, creating duplicate payment records. Missing idempotency key validation.',
  blast_radius: 'HIGH',
  confidence_score: 0.94,
  impact: 'Multiple charges for single order. Customer financial impact. Reconciliation issues.',
  suggested_fix: {
    target_class: 'PaymentService.java',
    rationale: 'Add idempotency key validation before processing payment'
  }
};

export function HeroTerminal() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [showRCA, setShowRCA] = useState(false);
  const [showPR, setShowPR] = useState(false);
  const [showEmail, setShowEmail] = useState(false);
  const [anomalyDetected, setAnomalyDetected] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const steps: PipelineStep[] = [
    { id: 'ingest', icon: Activity, label: 'Ingest', status: currentStep >= 0 ? 'completed' : 'pending', color: '#10B981' },
    { id: 'detect', icon: AlertTriangle, label: 'Detect', status: currentStep >= 1 ? (anomalyDetected ? 'error' : 'completed') : 'pending', color: '#F59E0B' },
    { id: 'analyze', icon: Brain, label: 'Analyze', status: currentStep >= 2 ? 'running' : 'pending', color: '#8B5CF6' },
    { id: 'remediate', icon: GitPullRequest, label: 'Remediate', status: currentStep >= 3 ? 'completed' : 'pending', color: '#3B82F6' },
    { id: 'notify', icon: Mail, label: 'Notify', status: currentStep >= 4 ? 'completed' : 'pending', color: '#10B981' }
  ];

  useEffect(() => {
    let logIndex = 0;
    const interval = setInterval(() => {
      if (logIndex < mockLogs.length) {
        setLogs(prev => [...prev, mockLogs[logIndex]]);
        
        if (mockLogs[logIndex].level === 'ERROR') {
          setTimeout(() => {
            setAnomalyDetected(true);
            setCurrentStep(1);
          }, 500);
        }
        
        logIndex++;
      } else if (logIndex === mockLogs.length) {
        setTimeout(() => {
          setCurrentStep(2);
          setShowRCA(true);
          
          setTimeout(() => {
            setCurrentStep(3);
            setShowPR(true);
            
            setTimeout(() => {
              setCurrentStep(4);
              setShowEmail(true);
            }, 1500);
          }, 2000);
        }, 800);
        logIndex++;
      }
    }, 1200);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="relative">
      {/* Main Terminal */}
      <motion.div
        className="bg-[#0D1117] border border-[#2D333B] rounded-xl overflow-hidden shadow-2xl"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        {/* Terminal Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-[#161B22] border-b border-[#2D333B]">
          <div className="flex items-center gap-2">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-[#EF4444]" />
              <div className="w-3 h-3 rounded-full bg-[#F59E0B]" />
              <div className="w-3 h-3 rounded-full bg-[#10B981]" />
            </div>
            <span className="ml-3 text-xs text-[#6B7280] font-mono">morphic — incident-monitor</span>
          </div>
          <Terminal className="w-4 h-4 text-[#6B7280]" />
        </div>

        {/* Pipeline Steps */}
        <div className="flex items-center justify-between px-4 py-3 bg-[#111827] border-b border-[#2D333B]">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center">
              <motion.div
                className={`flex flex-col items-center gap-1 ${
                  step.status === 'completed' ? 'opacity-100' :
                  step.status === 'running' ? 'opacity-100' :
                  step.status === 'error' ? 'opacity-100' :
                  'opacity-40'
                }`}
                animate={step.status === 'running' ? {
                  scale: [1, 1.05, 1],
                  transition: { repeat: Infinity, duration: 1 }
                } : {}}
              >
                <div 
                  className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    step.status === 'completed' ? 'bg-[#10B981]/20' :
                    step.status === 'running' ? 'bg-[#8B5CF6]/20' :
                    step.status === 'error' ? 'bg-[#EF4444]/20' :
                    'bg-[#2D333B]'
                  }`}
                >
                  <step.icon 
                    className={`w-4 h-4 ${
                      step.status === 'completed' ? 'text-[#10B981]' :
                      step.status === 'running' ? 'text-[#8B5CF6]' :
                      step.status === 'error' ? 'text-[#EF4444]' :
                      'text-[#6B7280]'
                    }`}
                  />
                </div>
                <span className="text-[10px] text-[#9DA7B3] uppercase tracking-wider">{step.label}</span>
              </motion.div>
              {index < steps.length - 1 && (
                <div className="w-8 h-px bg-[#2D333B] mx-2" />
              )}
            </div>
          ))}
        </div>

        {/* Log Output */}
        <div className="p-4 h-48 overflow-y-auto font-mono text-xs bg-[#0D1117]">
          <AnimatePresence>
            {logs.filter(log => log && log.timestamp).map((log, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="mb-1"
              >
                <span className="text-[#6B7280]">[{new Date(log.timestamp || '').toLocaleTimeString()}]</span>
                <span className={`ml-2 ${
                  log.level === 'ERROR' ? 'text-[#EF4444]' :
                  log.level === 'WARN' ? 'text-[#F59E0B]' :
                  'text-[#10B981]'
                }`}>
                  {log.level || 'INFO'}
                </span>
                <span className="ml-2 text-[#9DA7B3]">{log.service || 'unknown'}:</span>
                <span className={`ml-2 ${
                  log.level === 'ERROR' ? 'text-[#EF4444]' :
                  log.level === 'WARN' ? 'text-[#F59E0B]' :
                  'text-[#E6EDF3]'
                }`}>
                  {log.message || ''}
                </span>
                {log.trace_id && (
                  <span className="ml-2 text-[#8B5CF6]">trace_id={log.trace_id}</span>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
          
          {/* Blinking Cursor */}
          <motion.span
            className="inline-block w-2 h-4 bg-[#3B82F6] ml-1"
            animate={{ opacity: [1, 0] }}
            transition={{ repeat: Infinity, duration: 0.8 }}
          />
          <div ref={logsEndRef} />
        </div>
      </motion.div>

      {/* RCA Card */}
      <AnimatePresence>
        {showRCA && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20 }}
            className="absolute -bottom-4 -right-4 w-80 bg-[#161B22] border border-[#8B5CF6] rounded-xl p-4 shadow-2xl"
          >
            <div className="flex items-center gap-2 mb-3">
              <Brain className="w-4 h-4 text-[#8B5CF6]" />
              <span className="text-sm font-semibold text-[#E6EDF3]">AI Root Cause Analysis</span>
              <span className="ml-auto text-xs px-2 py-0.5 bg-[#8B5CF6]/20 text-[#8B5CF6] rounded">
                {(rcaOutput.confidence_score * 100).toFixed(0)}% confidence
              </span>
            </div>
            
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-[#6B7280]">Classification:</span>
                <span className="text-[#F59E0B] font-mono">{rcaOutput.classification}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6B7280]">Blast Radius:</span>
                <span className="text-[#EF4444] font-semibold">{rcaOutput.blast_radius}</span>
              </div>
              <p className="text-[#9DA7B3] mt-2 leading-relaxed">{rcaOutput.root_cause}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* PR Card */}
      <AnimatePresence>
        {showPR && (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="absolute top-20 -right-20 w-64 bg-[#161B22] border border-[#3B82F6] rounded-xl p-4 shadow-2xl"
          >
            <div className="flex items-center gap-2 mb-3">
              <GitPullRequest className="w-4 h-4 text-[#3B82F6]" />
              <span className="text-sm font-semibold text-[#E6EDF3]">PR Created</span>
            </div>
            <div className="text-xs text-[#9DA7B3] mb-2">
              fix(payment): add idempotency validation
            </div>
            <div className="flex items-center gap-2 text-xs text-[#6B7280]">
              <CheckCircle className="w-3 h-3 text-[#10B981]" />
              <span>Auto-merged after tests passed</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Email Card */}
      <AnimatePresence>
        {showEmail && (
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="absolute top-32 -left-16 w-56 bg-[#161B22] border border-[#10B981] rounded-xl p-4 shadow-2xl"
          >
            <div className="flex items-center gap-2 mb-2">
              <Mail className="w-4 h-4 text-[#10B981]" />
              <span className="text-sm font-semibold text-[#E6EDF3]">Alert Sent</span>
            </div>
            <p className="text-xs text-[#9DA7B3]">
              HIGH severity incident resolved. PR #2842 created.
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Ambient Glow */}
      <div className="absolute -inset-4 bg-[#3B82F6]/5 rounded-2xl blur-xl -z-10" />
    </div>
  );
}
