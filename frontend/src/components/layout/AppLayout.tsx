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
import { NewsLensLogo } from '../ui/NewsLensLogo';

const navItems = [
  {
    to: '/',
    label: 'Overview',
    icon: LayoutDashboard,
    badge: null,
    activeColor: 'text-[#38BDF8] border-[#38BDF8]',
    badgeColor: '',
  },
  {
    to: '/news',
    label: 'News Monitor',
    icon: Radio,
    badge: 'LIVE',
    activeColor: 'text-[#34D399] border-[#34D399]',
    badgeColor: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
  },
  {
    to: '/analyze',
    label: 'Analyze Article',
    icon: FileSearch,
    badge: 'ML',
    activeColor: 'text-[#A78BFA] border-[#A78BFA]',
    badgeColor: 'bg-purple-500/20 text-purple-300 border border-purple-500/30',
  },
  {
    to: '/evidence',
    label: 'Evidence & Coverage',
    icon: Layers,
    badge: 'OSINT',
    activeColor: 'text-[#FBBF24] border-[#FBBF24]',
    badgeColor: 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
  },
  {
    to: '/integrations',
    label: 'Integrations',
    icon: Plug,
    badge: 'API',
    activeColor: 'text-[#22D3EE] border-[#22D3EE]',
    badgeColor: 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30',
  },
  {
    to: '/methodology',
    label: 'Methodology',
    icon: BookOpen,
    badge: null,
    activeColor: 'text-[#F472B6] border-[#F472B6]',
    badgeColor: '',
  },
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
      <aside className="w-68 xl:w-72 bg-gradient-to-b from-[#0B1528] via-[#10223D] to-[#070D18] text-white flex flex-col justify-between shrink-0 shadow-2xl border-r border-[#1E3A5F]/80 z-30 select-none">
        <div className="overflow-y-auto">
          {/* Brand header with Generated Rich Vector Logo */}
          <div className="p-5 xl:p-6 border-b border-[#1E3A5F]/70">
            <div className="flex items-center gap-3">
              <NewsLensLogo size="md" showText={false} />
              <div>
                <div className="flex items-center gap-1.5">
                  <h1 className="font-bold text-lg tracking-tight leading-none text-white font-serif">
                    NewsLens India
                  </h1>
                </div>
                <p className="text-[11px] text-[#94A3B8] mt-1 font-sans">
                  See coverage. Examine evidence.
                </p>
              </div>
            </div>
            <div className="mt-3.5 flex items-center justify-between">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-[#183B56] text-[#27C6C1] border border-[#27C6C1]/30">
                <span className="w-1.5 h-1.5 rounded-full bg-[#27C6C1] animate-pulse"></span>
                Media Observatory
              </span>
              <span className="text-[10px] text-[#718096] font-mono bg-white/5 px-2 py-0.5 rounded border border-white/5">
                FHD 1080p
              </span>
            </div>
          </div>

          {/* Section: Investigation Desk */}
          <div className="px-4 py-5">
            <p className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider px-3 mb-2.5">
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
                      `flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs xl:text-sm font-medium transition-all ${
                        isActive
                          ? `bg-[#183B56] ${item.activeColor} border-l-4 font-semibold shadow-md pl-2.5`
                          : 'text-[#CBD5E1] hover:bg-[#1A365D]/70 hover:text-white'
                      }`
                    }
                  >
                    <div className="flex items-center gap-3">
                      <Icon className="w-4 h-4 xl:w-4.5 xl:h-4.5 shrink-0" />
                      <span>{item.label}</span>
                    </div>
                    {item.badge && (
                      <span
                        className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-bold uppercase tracking-wider ${
                          item.badgeColor || 'bg-white/10 text-[#A0AEC0]'
                        }`}
                      >
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
        <div className="p-4 border-t border-[#1E3A5F]/80 bg-[#070D18]/95 backdrop-blur-xs">
          <div className="flex items-center justify-between mb-2.5 text-xs">
            <span className="flex items-center gap-1.5 text-[#27C6C1] font-semibold text-[11px] tracking-wide">
              <span className="w-2 h-2 rounded-full bg-[#27C6C1] animate-pulse"></span>
              LIVE DATASTORE
            </span>
            <span className="text-[10px] bg-emerald-950/80 text-emerald-400 px-2 py-0.5 rounded font-mono border border-emerald-500/30">
              v1.0-prod
            </span>
          </div>
          <p className="text-[11px] text-[#94A3B8] leading-snug mb-3">
            SQLite persistence active with verified GDELT & RSS Indian news wires.
          </p>
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-gradient-to-r from-[#2563EB] to-[#0D9488] hover:from-[#1D4ED8] hover:to-[#0F766E] text-white rounded-lg text-xs font-semibold transition-all shadow-md hover:shadow-lg disabled:opacity-50 cursor-pointer"
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
            <div className="hidden sm:flex items-center gap-2 px-3.5 py-1.5 bg-gradient-to-r from-emerald-50 to-teal-50 text-[#0F766E] border border-emerald-200/80 rounded-full text-[11px] font-semibold shadow-xs">
              <ShieldCheck className="w-3.5 h-3.5 text-[#0D9488]" />
              Evidence-First • Probabilistic Screening
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/70 rounded-full text-[11px] text-[#1E40AF] font-medium shadow-xs">
              <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse"></span>
              API Synchronized
            </div>
            <div className="hidden xl:flex items-center gap-1 px-2.5 py-1 bg-[#F8FAFC] border border-[#CBD5E1] rounded-full text-[10px] text-[#64748B] font-mono">
              <Monitor className="w-3 h-3 text-[#3B82F6]" />
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

