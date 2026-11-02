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
  Monitor,
} from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { newsApi } from '../../services/api';

const navItems = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, badge: null },
  { to: '/news', label: 'News Monitor', icon: Radio, badge: 'Live' },
  { to: '/analyze', label: 'Analyze Article', icon: FileSearch, badge: 'ML' },
  { to: '/evidence', label: 'Evidence & Coverage', icon: Layers, badge: 'OSINT' },
  { to: '/integrations', label: 'Integrations', icon: Plug, badge: 'API' },
  { to: '/methodology', label: 'Methodology', icon: BookOpen, badge: null },
];

export const AppLayout: React.FC = () => {
  const queryClient = useQueryClient();

  const syncMutation = useMutation({
    mutationFn: () => newsApi.triggerRefresh(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['articles'] });
      queryClient.invalidateQueries({ queryKey: ['coverage'] });
      queryClient.invalidateQueries({ queryKey: ['integrations-overview'] });
    },
  });

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#F4F6FB] text-[#1E293B]">
      {/* Sidebar matching Stitch Specification - Optimized for 1920x1080 resolution */}
      <aside className="w-68 xl:w-72 bg-gradient-to-b from-[#0F2137] via-[#142B4A] to-[#0A1728] text-white flex flex-col justify-between shrink-0 shadow-2xl border-r border-[#1E3A5F]/80 z-30 select-none">
        <div className="overflow-y-auto">
          {/* Brand header */}
          <div className="p-6 border-b border-[#1E3A5F]/60">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-tr from-[#315FE8] to-[#27C6C1] flex items-center justify-center font-bold text-lg text-white shadow-md ring-1 ring-white/20">
                NL
              </div>
              <div>
                <h1 className="font-bold text-lg tracking-tight leading-none text-white font-serif">
                  NewsLens India
                </h1>
                <p className="text-[11px] text-[#A0AEC0] mt-1 font-sans">
                  See coverage. Examine evidence.
                </p>
              </div>
            </div>
            <div className="mt-3.5 flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-semibold bg-[#183B56]/80 text-[#27C6C1] border border-[#27C6C1]/30">
                <span className="w-1.5 h-1.5 rounded-full bg-[#27C6C1] animate-pulse"></span>
                Indian Media Observatory
              </span>
              <span className="text-[10px] text-[#718096] font-mono">1080p FHD</span>
            </div>
          </div>

          {/* Section: Investigation Desk */}
          <div className="px-4 py-5">
            <p className="text-[10px] font-bold text-[#718096] uppercase tracking-wider px-3 mb-2.5">
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
                      `flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs xl:text-sm font-medium transition-all ${
                        isActive
                          ? 'bg-[#183B56] text-[#27C6C1] border-l-4 border-[#27C6C1] font-semibold shadow-inner pl-2.5'
                          : 'text-[#CBD5E1] hover:bg-[#1A365D]/70 hover:text-white'
                      }`
                    }
                  >
                    <div className="flex items-center gap-3">
                      <Icon className="w-4 h-4 xl:w-4.5 xl:h-4.5 shrink-0" />
                      <span>{item.label}</span>
                    </div>
                    {item.badge && (
                      <span className="text-[9px] px-1.5 py-0.5 rounded font-mono font-bold uppercase tracking-wider bg-white/10 text-[#A0AEC0]">
                        {item.badge}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </nav>
          </div>
        </div>

        {/* Datastore and Sync Widget in Sidebar */}
        <div className="p-4 border-t border-[#1E3A5F]/80 bg-[#0A1626]/90 backdrop-blur-xs">
          <div className="flex items-center justify-between mb-2.5 text-xs">
            <span className="flex items-center gap-1.5 text-[#27C6C1] font-semibold text-[11px] tracking-wide">
              <span className="w-2 h-2 rounded-full bg-[#27C6C1] animate-pulse"></span>
              LIVE DATASTORE
            </span>
            <span className="text-[10px] bg-[#183B56] text-[#A0AEC0] px-2 py-0.5 rounded font-mono border border-white/5">
              v1.0-prod
            </span>
          </div>
          <p className="text-[11px] text-[#A0AEC0] leading-snug mb-3">
            SQLite persistence active with verified GDELT & RSS Indian news wires.
          </p>
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-gradient-to-r from-[#183B56] to-[#20496B] hover:from-[#20496B] hover:to-[#315FE8] text-white rounded-lg text-xs font-semibold transition-all shadow-sm disabled:opacity-50 cursor-pointer"
          >
            <RotateCw className={`w-3.5 h-3.5 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
            {syncMutation.isPending ? 'Syncing...' : 'Sync Data Feeds'}
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        {/* Top Header Bar */}
        <header className="h-16 bg-white/95 backdrop-blur-md border-b border-[#E2E8F0] px-6 lg:px-10 flex items-center justify-between shrink-0 z-20 shadow-xs">
          <div className="flex items-center gap-4 w-full max-w-md lg:max-w-lg xl:max-w-xl">
            <div className="relative w-full">
              <Search className="w-4 h-4 text-[#94A3B8] absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search Indian news topics, claims, keywords... (Press ⌘K)"
                className="w-full pl-10 pr-4 py-2 text-xs bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg focus:outline-none focus:border-[#315FE8] focus:ring-2 focus:ring-[#315FE8]/20 transition-all font-sans"
              />
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs font-medium text-[#475569]">
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-[#EBF8FF] text-[#087F83] border border-[#BEE3F8] rounded-full text-[11px] font-semibold">
              <ShieldCheck className="w-3.5 h-3.5 text-[#087F83]" />
              Evidence-First • Probabilistic Screening
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-[#F1F5F9] rounded-full text-[11px] text-[#475569]">
              <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse"></span>
              API Synchronized
            </div>
            <div className="hidden xl:flex items-center gap-1 px-2.5 py-1 bg-[#F8FAFC] border border-[#E2E8F0] rounded-full text-[10px] text-[#64748B] font-mono">
              <Monitor className="w-3 h-3 text-[#94A3B8]" />
              1920 × 1080 View
            </div>
          </div>
        </header>

        {/* Dynamic Route Body - Fills 1920x1080 widescreen cleanly */}
        <main className="flex-1 overflow-y-auto px-6 py-6 lg:px-10 lg:py-8 scroll-smooth">
          <div className="max-w-[1680px] 2xl:max-w-[1760px] mx-auto w-full space-y-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
