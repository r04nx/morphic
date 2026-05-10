import { useAuth } from '../contexts/AuthContext';
import { motion } from 'framer-motion';
import { Terminal, Activity, Database, LogOut } from 'lucide-react';

export function Dashboard() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-[#0D1117]">
      {/* Header */}
      <header className="bg-[#161B22] border-b border-[#2D333B]">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img src="/logo.png" alt="Morphic" className="w-8 h-8" />
            <span className="text-xl font-bold text-[#E6EDF3]">Morphic</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-[#9DA7B3]">Welcome, {user?.username}</span>
            <button
              onClick={logout}
              className="flex items-center gap-2 px-4 py-2 bg-[#EF4444]/10 border border-[#EF4444]/20 text-[#EF4444] rounded-lg hover:bg-[#EF4444]/20 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-8"
        >
          <div>
            <h1 className="text-3xl font-bold text-[#E6EDF3] mb-2">Dashboard</h1>
            <p className="text-[#9DA7B3]">Welcome to the Morphic AI Incident Platform</p>
          </div>

          {/* Stats Grid */}
          <div className="grid md:grid-cols-3 gap-6">
            <div className="bg-[#161B22] border border-[#2D333B] rounded-xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-[#3B82F6]/20 flex items-center justify-center">
                  <Activity className="w-5 h-5 text-[#3B82F6]" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-[#E6EDF3]">0</div>
                  <div className="text-sm text-[#9DA7B3]">Active Incidents</div>
                </div>
              </div>
            </div>

            <div className="bg-[#161B22] border border-[#2D333B] rounded-xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-[#8B5CF6]/20 flex items-center justify-center">
                  <Terminal className="w-5 h-5 text-[#8B5CF6]" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-[#E6EDF3]">0</div>
                  <div className="text-sm text-[#9DA7B3]">Monitors</div>
                </div>
              </div>
            </div>

            <div className="bg-[#161B22] border border-[#2D333B] rounded-xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-[#10B981]/20 flex items-center justify-center">
                  <Database className="w-5 h-5 text-[#10B981]" />
                </div>
                <div>
                  <div className="text-2xl font-bold text-[#E6EDF3]">0</div>
                  <div className="text-sm text-[#9DA7B3]">Traces</div>
                </div>
              </div>
            </div>
          </div>

          {/* Placeholder for future dashboard content */}
          <div className="bg-[#161B22] border border-[#2D333B] rounded-xl p-8 text-center">
            <Terminal className="w-12 h-12 text-[#6B7280] mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-[#E6EDF3] mb-2">Dashboard Under Construction</h2>
            <p className="text-[#9DA7B3]">
              The full dashboard will be integrated with the existing Morphic platform.
              This is a placeholder to demonstrate the authentication flow.
            </p>
          </div>
        </motion.div>
      </main>
    </div>
  );
}
