import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  Radio,
  FileSearch,
  Layers,
  Plug,
  BookOpen,
  ShieldCheck,
  RotateCw,
  Search,
} from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { newsApi } from '../../services/api';

const navItems = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/news', label: 'News Monitor', icon: Radio },
  { to: '/analyze', label: 'Analyze Article', icon: FileSearch },
  { to: '/evidence', label: 'Evidence & Coverage', icon: Layers },
  { to: '/integrations', label: 'Integrations', icon: Plug },
  { to: '/methodology', label: 'Methodology', icon: BookOpen },
];

export const AppLayout: React.FC = () => {
  const queryClient = useQueryClient();

  const syncMutation = useMutation({
    mutationFn: () => newsApi.triggerRefresh(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['articles'] });
      queryClient.invalidateQueries({ queryKey: ['coverage'] });
    },
  });

  return (
    <div className="flex min-h-screen bg-[#F4F6FB] text-[#1E293B]">
      {/* Sidebar matching Stitch Specification */}
      <aside className="w-64 bg-[#142B4A] text-white flex flex-col justify-between shrink-0 shadow-lg border-r border-[#1E3A5F]">
        <div>
          {/* Brand header */}
          <div className="p-6 border-b border-[#1E3A5F]">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-md bg-[#315FE8] flex items-center justify-center font-bold text-lg text-white shadow-sm">
                NL
              </div>
              <div>
                <h1 className="font-bold text-lg tracking-tight leading-none text-white">NewsLens India</h1>
                <p className="text-[11px] text-[#A0AEC0] mt-1">See coverage. Examine evidence.</p>
              </div>
            </div>
          </div>

          {/* Section: Investigation Desk */}
          <div className="px-4 py-6">
            <p className="text-[10px] font-bold text-[#718096] uppercase tracking-wider px-3 mb-3">
              Investigation Desk
            </p>
            <nav className="space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/'}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-[#183B56] text-[#27C6C1] border-l-4 border-[#27C6C1] font-semibold pl-2'
                          : 'text-[#CBD5E1] hover:bg-[#1A365D] hover:text-white'
                      }`
                    }
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </nav>
          </div>
        </div>

        {/* Datastore and Sync Widget in Sidebar */}
        <div className="p-4 border-t border-[#1E3A5F] bg-[#0E1F35]">
          <div className="flex items-center justify-between mb-3 text-xs">
            <span className="flex items-center gap-1.5 text-[#27C6C1] font-semibold text-[11px]">
              <span className="w-2 h-2 rounded-full bg-[#27C6C1] animate-pulse"></span>
              LIVE DATASTORE
            </span>
            <span className="text-[10px] bg-[#183B56] text-[#A0AEC0] px-2 py-0.5 rounded font-mono">
              v1.0-prod
            </span>
          </div>
          <p className="text-[11px] text-[#A0AEC0] leading-snug mb-3">
            SQLite persistence active with verified GDELT & RSS Indian news wires.
          </p>
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-[#183B56] hover:bg-[#20496B] text-white rounded text-xs font-medium transition-colors disabled:opacity-50 cursor-pointer"
          >
            <RotateCw className={`w-3.5 h-3.5 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
            {syncMutation.isPending ? 'Syncing...' : 'Sync Data Feeds'}
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header Bar */}
        <header className="h-16 bg-white border-b border-[#E2E8F0] px-8 flex items-center justify-between sticky top-0 z-10 shadow-xs">
          <div className="flex items-center gap-3 w-96">
            <div className="relative w-full">
              <Search className="w-4 h-4 text-[#94A3B8] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search Indian news topics, claims, keywords..."
                className="w-full pl-9 pr-4 py-1.5 text-xs bg-[#F8FAFC] border border-[#CBD5E1] rounded-md focus:outline-none focus:border-[#315FE8] focus:ring-1 focus:ring-[#315FE8]"
              />
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-medium text-[#475569]">
            <div className="flex items-center gap-2 px-3 py-1 bg-[#EBF8FF] text-[#087F83] border border-[#BEE3F8] rounded-full text-[11px]">
              <ShieldCheck className="w-3.5 h-3.5" />
              Evidence-First • Probabilistic Screening
            </div>
            <div className="flex items-center gap-1.5 text-[11px] text-[#64748B]">
              <span className="w-2 h-2 rounded-full bg-[#10B981]"></span>
              API Synchronized
            </div>
          </div>
        </header>

        {/* Dynamic Route Body */}
        <main className="flex-1 p-8 overflow-y-auto">
          <div className="max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
