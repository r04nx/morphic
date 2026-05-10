import { useEffect, useState, Component, ReactNode } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity,
  Terminal,
  Brain,
  GitPullRequest,
  AlertTriangle,
  Zap,
  Workflow,
  Database,
  Github,
  Cpu,
  Layers,
  Server,
  Bell,
  GitBranch,
  Network,
  Search,
  Shield,
  Clock,
  TrendingUp,
  Box,
  Container,
  ChevronRight,
  Menu,
  X,
  Play,
  ArrowRight,
  Sparkles,
  Monitor,
  FileCode,
  MessageSquare,
  Mail,
  CheckCircle2,
  LogOut
} from 'lucide-react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { Signup } from './pages/Signup';
import { Dashboard } from './pages/Dashboard';

// Error Boundary Component
class ErrorBoundary extends Component<{ children: ReactNode; fallback?: ReactNode }, { hasError: boolean; error?: Error }> {
  constructor(props: { children: ReactNode; fallback?: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="p-8 bg-red-900/20 border border-red-500 rounded-lg">
          <h2 className="text-xl font-bold text-red-400">Something went wrong</h2>
          <p className="text-red-300 mt-2">{this.state.error?.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}

// Lazy load components with error handling
const ComponentWrapper = ({ children, name }: { children: ReactNode; name: string }) => (
  <ErrorBoundary fallback={<div className="p-4 text-red-400">Error in {name}</div>}>
    {children}
  </ErrorBoundary>
);

// Import components
import { HeroTerminal } from './components/HeroTerminal';
import { PipelineFlow } from './components/PipelineFlow';
import { ChaosScenarios } from './components/ChaosScenarios';
import { KnowledgeGraph } from './components/KnowledgeGraph';
import { LiveDemoTerminal } from './components/LiveDemoTerminal';
import { ArchitectureMap } from './components/ArchitectureMap';
import { APIShowcase } from './components/APIShowcase';

// Animation variants
const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.2, 0.8, 0.2, 1] } }
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1
    }
  }
};

const glowPulse = {
  animate: {
    boxShadow: [
      '0 0 20px rgba(59, 130, 246, 0.3)',
      '0 0 40px rgba(59, 130, 246, 0.5)',
      '0 0 20px rgba(59, 130, 246, 0.3)'
    ],
    transition: { duration: 2, repeat: Infinity, ease: 'easeInOut' }
  }
};

// Integration logos
const integrations = [
  { name: 'Claude AI', icon: Brain, color: '#D97757' },
  { name: 'GitHub', icon: Github, color: '#FFFFFF' },
  { name: 'Neo4j', icon: Network, color: '#008CC1' },
  { name: 'PostgreSQL', icon: Database, color: '#336791' },
  { name: 'Redis', icon: Layers, color: '#DC382D' },
  { name: 'Docker', icon: Container, color: '#2496ED' },
  { name: 'Flask', icon: Server, color: '#000000' },
  { name: 'React', icon: Box, color: '#61DAFB' }
];

// Feature cards data
const features = [
  {
    icon: Brain,
    title: 'AI Root Cause Analysis',
    description: 'Claude AI analyzes logs to generate structured RCA with confidence scores and blast radius assessment.',
    gradient: 'from-blue-500/20 to-purple-500/20'
  },
  {
    icon: Network,
    title: 'Neo4j Knowledge Graph',
    description: 'Visualize incident topology, service dependencies, and blast radius with interactive graph analytics.',
    gradient: 'from-orange-500/20 to-red-500/20'
  },
  {
    icon: GitPullRequest,
    title: 'GitHub PR Automation',
    description: 'Automatically create pull requests with AI-generated fixes, tests, and comprehensive PR descriptions.',
    gradient: 'from-green-500/20 to-emerald-500/20'
  },
  {
    icon: Workflow,
    title: 'Distributed Tracing',
    description: 'Follow requests across services with trace correlation. Detect ASYNC-ORPHAN events automatically.',
    gradient: 'from-cyan-500/20 to-blue-500/20'
  },
  {
    icon: AlertTriangle,
    title: 'Blast Radius Detection',
    description: 'Classify incidents by severity: LOW, MEDIUM, HIGH, CRITICAL. Understand impact before it spreads.',
    gradient: 'from-red-500/20 to-orange-500/20'
  },
  {
    icon: Bell,
    title: 'Multi-Channel Alerts',
    description: 'Email, Slack, webhook notifications with severity-based routing and intelligent deduplication.',
    gradient: 'from-yellow-500/20 to-orange-500/20'
  },
  {
    icon: Cpu,
    title: 'Agent Orchestration',
    description: 'Coordinate multiple AI agents: ingestion, triage, RCA, remediation, and notification workflows.',
    gradient: 'from-purple-500/20 to-pink-500/20'
  },
  {
    icon: Activity,
    title: 'Real-Time Monitoring',
    description: '30-second polling with LogAI anomaly detection. Statistical, semantic, and time-series analysis.',
    gradient: 'from-teal-500/20 to-cyan-500/20'
  }
];

function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <motion.nav
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.5, ease: [0.2, 0.8, 0.2, 1] }}
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled 
          ? 'bg-[#0D1117]/90 backdrop-blur-xl border-b border-[#2D333B]' 
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <motion.div
            className="flex items-center gap-2"
            whileHover={{ scale: 1.02 }}
          >
            <img src="/logo.png" alt="Morphic" className="w-8 h-8" />
            <span className="text-xl font-semibold text-[#E6EDF3]">Morphic</span>
          </motion.div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            {['Features', 'Architecture', 'Demo', 'Docs'].map((item) => (
              <motion.a
                key={item}
                href={`#${item.toLowerCase()}`}
                className="text-sm text-[#9DA7B3] hover:text-[#E6EDF3] transition-colors"
                whileHover={{ y: -1 }}
              >
                {item}
              </motion.a>
            ))}
          </div>

          {/* CTA Buttons */}
          <div className="hidden md:flex items-center gap-4">
            <motion.a
              href="https://github.com/morphic"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-[#9DA7B3] hover:text-[#E6EDF3] transition-colors flex items-center gap-2"
              whileHover={{ scale: 1.02 }}
            >
              <Github className="w-4 h-4" />
              GitHub
            </motion.a>
            {isAuthenticated ? (
              <>
                <motion.button
                  onClick={() => navigate('/dashboard')}
                  className="px-4 py-2 bg-[#161B22] hover:bg-[#1C2128] border border-[#2D333B] text-[#E6EDF3] text-sm font-medium rounded-lg transition-colors"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Dashboard
                </motion.button>
                <motion.button
                  onClick={logout}
                  className="px-4 py-2 bg-[#EF4444]/10 border border-[#EF4444]/20 text-[#EF4444] text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <LogOut className="w-4 h-4" />
                  Logout
                </motion.button>
              </>
            ) : (
              <>
                <motion.button
                  onClick={() => navigate('/login')}
                  className="px-4 py-2 text-[#9DA7B3] hover:text-[#E6EDF3] text-sm font-medium transition-colors"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Sign In
                </motion.button>
                <motion.button
                  onClick={() => navigate('/signup')}
                  className="px-4 py-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white text-sm font-medium rounded-lg transition-colors"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Get Started
                </motion.button>
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden text-[#E6EDF3]"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-[#0D1117]/95 backdrop-blur-xl border-b border-[#2D333B]"
          >
            <div className="px-6 py-4 space-y-4">
              {['Features', 'Architecture', 'Demo', 'Docs'].map((item) => (
                <a
                  key={item}
                  href={`#${item.toLowerCase()}`}
                  className="block text-[#9DA7B3] hover:text-[#E6EDF3] transition-colors"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  {item}
                </a>
              ))}
              {isAuthenticated ? (
                <>
                  <button onClick={() => { navigate('/dashboard'); setMobileMenuOpen(false); }} className="w-full px-4 py-2 bg-[#161B22] border border-[#2D333B] text-[#E6EDF3] rounded-lg">
                    Dashboard
                  </button>
                  <button onClick={() => { logout(); setMobileMenuOpen(false); }} className="w-full px-4 py-2 bg-[#EF4444]/10 border border-[#EF4444]/20 text-[#EF4444] rounded-lg">
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <button onClick={() => { navigate('/login'); setMobileMenuOpen(false); }} className="w-full px-4 py-2 text-[#9DA7B3] rounded-lg">
                    Sign In
                  </button>
                  <button onClick={() => { navigate('/signup'); setMobileMenuOpen(false); }} className="w-full px-4 py-2 bg-[#3B82F6] text-white rounded-lg">
                    Get Started
                  </button>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  );
}

function HeroSection() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  return (
    <section className="relative min-h-screen pt-24 pb-16 overflow-hidden">
      {/* Ambient Glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 right-1/4 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 left-1/2 w-72 h-72 bg-cyan-500/10 rounded-full blur-3xl" />
      </div>

      <div className="max-w-7xl mx-auto px-6 lg:px-8 relative z-10">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left: Text Content */}
          <motion.div
            initial="hidden"
            animate="visible"
            variants={staggerContainer}
            className="space-y-8"
          >
            <motion.div variants={fadeInUp} className="space-y-4">
              <motion.div
                className="inline-flex items-center gap-2 px-3 py-1.5 bg-[#161B22] border border-[#2D333B] rounded-full text-xs text-[#9DA7B3]"
                whileHover={{ scale: 1.02 }}
              >
                <Sparkles className="w-3.5 h-3.5 text-[#3B82F6]" />
                <span>AI-Powered Incident Intelligence</span>
                <span className="px-1.5 py-0.5 bg-[#3B82F6]/20 text-[#3B82F6] rounded">v2.0</span>
              </motion.div>

              <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-[#E6EDF3] leading-tight">
                AI that fixes{' '}
                <span className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] bg-clip-text text-transparent">
                  production
                </span>{' '}
                before you wake up
              </h1>

              <p className="text-lg text-[#9DA7B3] max-w-xl leading-relaxed">
                Morphic monitors, analyzes, and remediates incidents autonomously. 
                From log detection to GitHub PR in under 60 seconds using Claude AI 
                and intelligent agent orchestration.
              </p>
            </motion.div>

            <motion.div variants={fadeInUp} className="flex flex-wrap gap-4">
              <motion.button
                onClick={() => isAuthenticated ? navigate('/dashboard') : navigate('/signup')}
                className="group px-6 py-3 bg-[#3B82F6] hover:bg-[#2563EB] text-white font-medium rounded-lg flex items-center gap-2 transition-all"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Play className="w-4 h-4" />
                {isAuthenticated ? 'Dashboard' : 'Live Demo'}
                <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
              </motion.button>

              <motion.a
                href="https://github.com/morphic"
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-3 bg-[#161B22] hover:bg-[#1C2128] border border-[#2D333B] text-[#E6EDF3] font-medium rounded-lg flex items-center gap-2 transition-all"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Github className="w-4 h-4" />
                View on GitHub
              </motion.a>
            </motion.div>

            {/* Floating Metrics */}
            <motion.div 
              variants={fadeInUp}
              className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4"
            >
              {[
                { icon: Clock, label: 'Detection', value: '30s' },
                { icon: Brain, label: 'AI Engine', value: 'Claude 3.5' },
                { icon: Activity, label: 'Algorithms', value: '3 ML' },
                { icon: Layers, label: 'Pipeline', value: '4 Layers' }
              ].map((metric, i) => (
                <motion.div
                  key={metric.label}
                  className="p-3 bg-[#161B22]/80 backdrop-blur-sm border border-[#2D333B] rounded-lg"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 + i * 0.1 }}
                  whileHover={{ y: -2, borderColor: '#3B82F6' }}
                >
                  <metric.icon className="w-4 h-4 text-[#3B82F6] mb-2" />
                  <div className="text-lg font-semibold text-[#E6EDF3]">{metric.value}</div>
                  <div className="text-xs text-[#6B7280]">{metric.label}</div>
                </motion.div>
              ))}
            </motion.div>
          </motion.div>

          {/* Right: Animated Terminal */}
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.3, ease: [0.2, 0.8, 0.2, 1] }}
            className="relative"
          >
            <HeroTerminal />
          </motion.div>
        </div>
      </div>
    </section>
  );
}

function IntegrationBar() {
  return (
    <section className="py-12 border-y border-[#2D333B] bg-[#0B0F14]">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-center mb-8"
        >
          <p className="text-sm text-[#6B7280] uppercase tracking-wider">Powered By</p>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={staggerContainer}
          className="flex flex-wrap justify-center items-center gap-8 md:gap-12"
        >
          {integrations.map((integration, i) => (
            <motion.div
              key={integration.name}
              variants={fadeInUp}
              className="flex items-center gap-2 text-[#6B7280] hover:text-[#9DA7B3] transition-colors cursor-pointer"
              whileHover={{ scale: 1.05 }}
            >
              <integration.icon 
                className="w-5 h-5" 
                style={{ color: integration.color }}
              />
              <span className="text-sm font-medium">{integration.name}</span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function FeaturesSection() {
  return (
    <section id="features" className="py-24 relative">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-[#E6EDF3] mb-4">
            Autonomous Incident Intelligence
          </h2>
          <p className="text-[#9DA7B3] max-w-2xl mx-auto">
            A complete platform for detection, analysis, and remediation. 
            From logs to PR in one seamless workflow.
          </p>
        </motion.div>

        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={staggerContainer}
          className="grid md:grid-cols-2 lg:grid-cols-4 gap-6"
        >
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              variants={fadeInUp}
              className="group relative p-6 bg-[#161B22] border border-[#2D333B] rounded-xl overflow-hidden"
              whileHover={{ y: -4, borderColor: '#3B82F6' }}
            >
              {/* Gradient Background */}
              <div className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />
              
              <div className="relative z-10">
                <div className="w-10 h-10 rounded-lg bg-[#0D1117] border border-[#2D333B] flex items-center justify-center mb-4 group-hover:border-[#3B82F6] transition-colors">
                  <feature.icon className="w-5 h-5 text-[#3B82F6]" />
                </div>
                
                <h3 className="text-lg font-semibold text-[#E6EDF3] mb-2">
                  {feature.title}
                </h3>
                
                <p className="text-sm text-[#9DA7B3] leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function PipelineSection() {
  return (
    <section className="py-24 bg-[#0B0F14]">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-[#E6EDF3] mb-4">
            4-Layer AI Pipeline
          </h2>
          <p className="text-[#9DA7B3] max-w-2xl mx-auto">
            A modular, extensible architecture that processes incidents from 
            detection to remediation with intelligent agent orchestration.
          </p>
        </motion.div>

        <PipelineFlow />
      </div>
    </section>
  );
}

function ChaosSection() {
  return (
    <section className="py-24 relative">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="grid lg:grid-cols-2 gap-16 items-center"
        >
          <div>
            <h2 className="text-3xl md:text-4xl font-bold text-[#E6EDF3] mb-4">
              Chaos Engineering Ready
            </h2>
            <p className="text-[#9DA7B3] mb-8 leading-relaxed">
              Morphic is built to handle real-world failure scenarios. Test your 
              incident response against 5 production-like bugs that occur naturally 
              through API usage patterns.
            </p>

            <div className="space-y-4">
              {[
                { type: 'GATEWAY_TIMEOUT', impact: 'Duplicate Payments', severity: 'CRITICAL' },
                { type: 'PARTIAL_WRITE', impact: 'Orphaned Records', severity: 'HIGH' },
                { type: 'RACE_CONDITION', impact: 'Negative Stock', severity: 'HIGH' },
                { type: 'ASYNC_TRACE_LOSS', impact: 'MDC Failures', severity: 'MEDIUM' },
                { type: 'INCONSISTENT_STATE', impact: 'Stuck Orders', severity: 'MEDIUM' }
              ].map((scenario) => (
                <motion.div
                  key={scenario.type}
                  className="flex items-center justify-between p-4 bg-[#161B22] border border-[#2D333B] rounded-lg"
                  whileHover={{ x: 4, borderColor: '#3B82F6' }}
                >
                  <div className="flex items-center gap-3">
                    <AlertTriangle className={`w-4 h-4 ${
                      scenario.severity === 'CRITICAL' ? 'text-[#EF4444]' :
                      scenario.severity === 'HIGH' ? 'text-[#F59E0B]' :
                      'text-[#6B7280]'
                    }`} />
                    <span className="text-sm font-mono text-[#E6EDF3]">{scenario.type}</span>
                  </div>
                  <span className="text-sm text-[#9DA7B3]">{scenario.impact}</span>
                  <span className={`text-xs px-2 py-1 rounded ${
                    scenario.severity === 'CRITICAL' ? 'bg-[#EF4444]/20 text-[#EF4444]' :
                    scenario.severity === 'HIGH' ? 'bg-[#F59E0B]/20 text-[#F59E0B]' :
                    'bg-[#6B7280]/20 text-[#6B7280]'
                  }`}>
                    {scenario.severity}
                  </span>
                </motion.div>
              ))}
            </div>
          </div>

          <ChaosScenarios />
        </motion.div>
      </div>
    </section>
  );
}

function KnowledgeGraphSection() {
  return (
    <section className="py-24 bg-[#0B0F14]">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-[#E6EDF3] mb-4">
            Visualize Blast Radius
          </h2>
          <p className="text-[#9DA7B3] max-w-2xl mx-auto">
            Neo4j-powered knowledge graphs show incident topology, service dependencies, 
            and the full scope of impact across your infrastructure.
          </p>
        </motion.div>

        <KnowledgeGraph />
      </div>
    </section>
  );
}

function DemoSection() {
  return (
    <section id="demo" className="py-24 relative">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-[#E6EDF3] mb-4">
            See It In Action
          </h2>
          <p className="text-[#9DA7B3] max-w-2xl mx-auto">
            Watch Morphic detect an anomaly, generate an RCA, and create a GitHub PR 
            with an AI-suggested fix in real-time.
          </p>
        </motion.div>

        <LiveDemoTerminal />
      </div>
    </section>
  );
}

function ArchitectureSection() {
  return (
    <section id="architecture" className="py-24 bg-[#0B0F14]">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-[#E6EDF3] mb-4">
            Complete System Architecture
          </h2>
          <p className="text-[#9DA7B3] max-w-2xl mx-auto">
            A production-ready stack with intelligent agents, multiple databases, 
            and seamless GitHub integration.
          </p>
        </motion.div>

        <ArchitectureMap />
      </div>
    </section>
  );
}

function APISection() {
  return (
    <section className="py-24">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-[#E6EDF3] mb-4">
            RESTful API
          </h2>
          <p className="text-[#9DA7B3] max-w-2xl mx-auto">
            Simple, powerful endpoints for incidents, traces, and automated actions.
          </p>
        </motion.div>

        <APIShowcase />
      </div>
    </section>
  );
}

function CTASection() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  return (
    <section className="py-24 relative overflow-hidden">
      {/* Background Glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#3B82F6]/10 rounded-full blur-3xl" />
      </div>

      <div className="max-w-4xl mx-auto px-6 lg:px-8 text-center relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="space-y-8"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-[#E6EDF3]">
            Deploy autonomous incident intelligence{' '}
            <span className="bg-gradient-to-r from-[#3B82F6] to-[#8B5CF6] bg-clip-text text-transparent">
              in minutes
            </span>
          </h2>

          <p className="text-lg text-[#9DA7B3] max-w-2xl mx-auto">
            Get started with Docker Compose and see Morphic monitoring your services 
            with AI-powered root cause analysis and automated remediation.
          </p>

          <div className="flex flex-wrap justify-center gap-4">
            <motion.button
              onClick={() => isAuthenticated ? navigate('/dashboard') : navigate('/signup')}
              className="px-8 py-4 bg-[#3B82F6] hover:bg-[#2563EB] text-white font-semibold rounded-lg flex items-center gap-2 transition-all"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <Box className="w-5 h-5" />
              {isAuthenticated ? 'Go to Dashboard' : 'Get Started'}
            </motion.button>

            <motion.a
              href="https://github.com/morphic"
              target="_blank"
              rel="noopener noreferrer"
              className="px-8 py-4 bg-[#161B22] hover:bg-[#1C2128] border border-[#2D333B] text-[#E6EDF3] font-semibold rounded-lg flex items-center gap-2 transition-all"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <Github className="w-5 h-5" />
              View Documentation
            </motion.a>
          </div>

          {/* Quick Start Command */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3 }}
            className="max-w-xl mx-auto"
          >
            <div className="bg-[#0D1117] border border-[#2D333B] rounded-lg p-4 font-mono text-sm text-left">
              <div className="flex items-center gap-2 mb-2">
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-[#EF4444]" />
                  <div className="w-2.5 h-2.5 rounded-full bg-[#F59E0B]" />
                  <div className="w-2.5 h-2.5 rounded-full bg-[#10B981]" />
                </div>
                <span className="text-xs text-[#6B7280] ml-2">bash</span>
              </div>
              <code className="text-[#E6EDF3]">
                <span className="text-[#6B7280]">$</span> git clone https://github.com/morphic/morphic.git<br />
                <span className="text-[#6B7280]">$</span> cd morphic && docker-compose up<br />
                <span className="text-[#6B7280]">$</span> open http://localhost:3000
              </code>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="py-12 border-t border-[#2D333B]">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="grid md:grid-cols-4 gap-8 mb-8">
          {/* Brand */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <img src="/logo.png" alt="Morphic" className="w-8 h-8" />
              <span className="text-xl font-semibold text-[#E6EDF3]">Morphic</span>
            </div>
            <p className="text-sm text-[#6B7280]">
              AI-powered incident intelligence and autonomous remediation.
            </p>
          </div>

          {/* Product */}
          <div>
            <h4 className="text-sm font-semibold text-[#E6EDF3] mb-4">Product</h4>
            <ul className="space-y-2">
              {['Features', 'Pricing', 'Changelog', 'Roadmap'].map((item) => (
                <li key={item}>
                  <a href="#" className="text-sm text-[#6B7280] hover:text-[#E6EDF3] transition-colors">
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="text-sm font-semibold text-[#E6EDF3] mb-4">Resources</h4>
            <ul className="space-y-2">
              {['Documentation', 'API Reference', 'GitHub', 'Discord'].map((item) => (
                <li key={item}>
                  <a href="#" className="text-sm text-[#6B7280] hover:text-[#E6EDF3] transition-colors">
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Company */}
          <div>
            <h4 className="text-sm font-semibold text-[#E6EDF3] mb-4">Company</h4>
            <ul className="space-y-2">
              {['About', 'Blog', 'Careers', 'Contact'].map((item) => (
                <li key={item}>
                  <a href="#" className="text-sm text-[#6B7280] hover:text-[#E6EDF3] transition-colors">
                    {item}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="pt-8 border-t border-[#2D333B] flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-sm text-[#6B7280]">
            © 2024 Morphic. Built for the AI observability era.
          </p>
          <div className="flex items-center gap-4">
            <a href="#" className="text-sm text-[#6B7280] hover:text-[#E6EDF3] transition-colors">
              Privacy
            </a>
            <a href="#" className="text-sm text-[#6B7280] hover:text-[#E6EDF3] transition-colors">
              Terms
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <AuthProvider>
          <Routes>
            {/* Landing Page */}
            <Route path="/" element={
              <div className="min-h-screen bg-[#0D1117] text-[#E6EDF3] font-sans selection:bg-[#3B82F6]/30">
                <ComponentWrapper name="Navbar"><Navbar /></ComponentWrapper>
                <main>
                  <ComponentWrapper name="HeroSection"><HeroSection /></ComponentWrapper>
                  <ComponentWrapper name="IntegrationBar"><IntegrationBar /></ComponentWrapper>
                  <ComponentWrapper name="FeaturesSection"><FeaturesSection /></ComponentWrapper>
                  <ComponentWrapper name="PipelineSection"><PipelineSection /></ComponentWrapper>
                  <ComponentWrapper name="ChaosSection"><ChaosSection /></ComponentWrapper>
                  <ComponentWrapper name="KnowledgeGraphSection"><KnowledgeGraphSection /></ComponentWrapper>
                  <ComponentWrapper name="DemoSection"><DemoSection /></ComponentWrapper>
                  <ComponentWrapper name="ArchitectureSection"><ArchitectureSection /></ComponentWrapper>
                  <ComponentWrapper name="APISection"><APISection /></ComponentWrapper>
                  <ComponentWrapper name="CTASection"><CTASection /></ComponentWrapper>
                </main>
                <ComponentWrapper name="Footer"><Footer /></ComponentWrapper>
              </div>
            } />

            {/* Auth Pages */}
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />

            {/* Protected Dashboard */}
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } />

            {/* Default redirect */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </Router>
    </ErrorBoundary>
  );
}

export default App;
