import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { newsApi } from '../services/api';
import type { Article } from '../types/api';
import {
  RefreshCw,
  ExternalLink,
  Cpu,
  Activity,
  ArrowRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [quickText, setQuickText] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'gdelt' | 'rss'>('all');

  const { data: summary, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => newsApi.getDashboardSummary(),
  });

  const screenMutation = useMutation({
    mutationFn: (text: string) => newsApi.analyzeArticle({ text }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-[#315FE8] animate-spin" />
          <p className="text-sm font-medium text-[#64748B]">Loading investigative news observatory...</p>
        </div>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-red-700">
        <h3 className="font-bold text-base">Observatory Synchronization Failure</h3>
        <p className="text-xs mt-1">Unable to connect to the FastAPI intelligence service. Ensure the backend server is running.</p>
      </div>
    );
  }

  const filteredArticles = summary.recent_articles.filter((art: Article) => {
    if (activeTab === 'gdelt') return art.source_type.toLowerCase() === 'gdelt';
    if (activeTab === 'rss') return art.source_type.toLowerCase() === 'rss';
    return true;
  });

  return (
    <div className="space-y-8">
      {/* Page Title & Context Header matching Stitch */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#E2E8F0]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-[#10B981]"></span>
            <span className="text-[11px] font-bold tracking-wider text-[#64748B] uppercase">
              REAL-TIME INDIAN MEDIA OBSERVABILITY
            </span>
          </div>
          <h2 className="text-3xl font-bold font-serif text-[#183B56] tracking-tight">Overview</h2>
          <p className="text-xs text-[#64748B] mt-1 max-w-2xl">
            Monitor recent coverage, screen news content, and examine available evidence across high-frequency syndicated wires and linguistic registers.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['dashboard'] })}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-[#CBD5E1] rounded-md text-xs font-semibold text-[#183B56] hover:bg-[#F8FAFC] shadow-xs cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh Sources
          </button>
        </div>
      </div>

      {/* 4-Box Key Metrics Layout */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="bg-white p-5 rounded-lg border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] transition-all">
          <div className="flex items-center justify-between text-xs text-[#64748B] mb-2 font-medium">
            <span>ARTICLES RETRIEVED</span>
            <span className="px-2 py-0.5 rounded bg-[#EAF0FF] text-[#315FE8] text-[10px] font-bold">LIVE SYNC</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-[#142B4A] tabular-nums font-serif">
              {summary.total_articles.toLocaleString()}
            </span>
            <span className="text-xs text-[#10B981] font-semibold">Active</span>
          </div>
          <p className="text-[11px] text-[#94A3B8] mt-2">Across GDELT & 8 RSS syndicated feeds</p>
        </div>

        {/* Metric 2 */}
        <div className="bg-white p-5 rounded-lg border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] transition-all">
          <div className="flex items-center justify-between text-xs text-[#64748B] mb-2 font-medium">
            <span>ACTIVE SOURCES</span>
            <span className="px-2 py-0.5 rounded bg-[#E5F6F3] text-[#087F83] text-[10px] font-bold">MONITORED</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-[#142B4A] tabular-nums font-serif">
              {summary.active_sources_count}
            </span>
            <span className="text-xs text-[#64748B]">/ {summary.total_configured_sources} configured</span>
          </div>
          <p className="text-[11px] text-[#94A3B8] mt-2">GDELT Doc API + English/Hindi syndicates</p>
        </div>

        {/* Metric 3 */}
        <div className="bg-white p-5 rounded-lg border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] transition-all">
          <div className="flex items-center justify-between text-xs text-[#64748B] mb-2 font-medium">
            <span>COVERAGE CLUSTERS</span>
            <span className="px-2 py-0.5 rounded bg-[#F0EDFF] text-[#7867D8] text-[10px] font-bold">DENSE NODES</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-[#142B4A] tabular-nums font-serif">
              {summary.coverage_clusters_count}
            </span>
            <span className="text-xs text-[#64748B]">stories</span>
          </div>
          <p className="text-[11px] text-[#94A3B8] mt-2">Similarity threshold cosine ≥ 0.55</p>
        </div>

        {/* Metric 4 */}
        <div className="bg-white p-5 rounded-lg border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] transition-all">
          <div className="flex items-center justify-between text-xs text-[#64748B] mb-2 font-medium">
            <span>FACT-CHECK MATCHES</span>
            <span className="px-2 py-0.5 rounded bg-[#FFF5E5] text-[#E5A440] text-[10px] font-bold">INDEXED</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-[#142B4A] tabular-nums font-serif">
              {summary.fact_check_matches_count}
            </span>
            <span className="text-xs text-[#64748B]">verified logs</span>
          </div>
          <p className="text-[11px] text-[#94A3B8] mt-2">BM25Plus accredited claim corpus</p>
        </div>
      </div>

      {/* Main Grid: Feed Triage (Left) & Right-Rail Widgets */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Feed Triage */}
        <div className="lg:col-span-8 space-y-4">
          <div className="flex items-center justify-between border-b border-[#E2E8F0] pb-2">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('all')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
                  activeTab === 'all'
                    ? 'bg-[#183B56] text-white'
                    : 'text-[#64748B] hover:text-[#183B56] hover:bg-[#F1F5F9]'
                }`}
              >
                All Sources ({summary.recent_articles.length})
              </button>
              <button
                onClick={() => setActiveTab('gdelt')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
                  activeTab === 'gdelt'
                    ? 'bg-[#183B56] text-white'
                    : 'text-[#64748B] hover:text-[#183B56] hover:bg-[#F1F5F9]'
                }`}
              >
                GDELT Discovered
              </button>
              <button
                onClick={() => setActiveTab('rss')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
                  activeTab === 'rss'
                    ? 'bg-[#183B56] text-white'
                    : 'text-[#64748B] hover:text-[#183B56] hover:bg-[#F1F5F9]'
                }`}
              >
                Regional Feeds
              </button>
            </div>
            <span className="text-[11px] text-[#94A3B8]">Sorted by Recency</span>
          </div>

          {/* Article List */}
          <div className="space-y-4">
            {filteredArticles.map((article: Article) => (
              <article
                key={article.id}
                className="bg-white p-5 rounded-lg border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] transition-all space-y-3"
              >
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-[#F1F5F9] text-[#475569]">
                      {article.source_type}
                    </span>
                    <span className="font-semibold text-[#183B56]">{article.publisher}</span>
                    <span className="text-[#94A3B8]">• {new Date(article.published_at).toLocaleString()}</span>
                  </div>
                  <span className="text-[11px] font-medium text-[#087F83] bg-[#E5F6F3] px-2 py-0.5 rounded">
                    Indexed
                  </span>
                </div>

                <h3 className="text-lg font-bold text-[#142B4A] font-serif leading-snug">
                  {article.title}
                </h3>

                {article.summary && (
                  <p className="text-xs text-[#64748B] leading-relaxed line-clamp-2">
                    {article.summary}
                  </p>
                )}

                <div className="flex items-center justify-between pt-2 border-t border-[#F1F5F9] text-xs">
                  <div className="flex items-center gap-3">
                    <Link
                      to={`/evidence?article_id=${article.id}`}
                      className="text-[#315FE8] hover:text-[#1E40AF] font-semibold flex items-center gap-1"
                    >
                      Examine Coverage <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                    <Link
                      to={`/analyze?text=${encodeURIComponent(article.title)}`}
                      className="text-[#64748B] hover:text-[#183B56] font-medium"
                    >
                      Screen in ML Analyzer
                    </Link>
                  </div>

                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-[#94A3B8] hover:text-[#475569]"
                  >
                    Original Wire <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </article>
            ))}
          </div>
        </div>

        {/* Right Column: Quick Article Screening & Ingestion Health */}
        <div className="lg:col-span-4 space-y-6">
          {/* Quick Screening Widget */}
          <div className="bg-white p-5 rounded-lg border border-[#E2E8F0] shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-[#315FE8]" />
                <h4 className="font-bold text-sm text-[#183B56]">Quick Article Screening</h4>
              </div>
              <span className="text-[10px] font-bold text-[#64748B] uppercase">Fast Inference</span>
            </div>

            <p className="text-xs text-[#64748B]">
              Evaluate claim syntax or unverified headlines against trained linguistic distortion benchmarks.
            </p>

            <textarea
              rows={4}
              value={quickText}
              onChange={(e) => setQuickText(e.target.value)}
              placeholder="Paste headline or text excerpt to screen for linguistic framing anomalies..."
              className="w-full p-3 text-xs bg-[#F8FAFC] border border-[#CBD5E1] rounded-md focus:outline-none focus:border-[#315FE8]"
            />

            <div className="flex items-center justify-between">
              <button
                onClick={() => setQuickText('')}
                className="text-xs text-[#94A3B8] hover:text-[#64748B] cursor-pointer"
              >
                Clear input
              </button>
              <button
                onClick={() => quickText.trim() && screenMutation.mutate(quickText)}
                disabled={screenMutation.isPending || !quickText.trim()}
                className="px-4 py-2 bg-[#183B56] hover:bg-[#20496B] text-white rounded text-xs font-semibold transition-colors disabled:opacity-50 cursor-pointer"
              >
                {screenMutation.isPending ? 'Screening...' : 'Run Screening'}
              </button>
            </div>

            {/* Screening Result if executed */}
            {screenMutation.data && (
              <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-md text-xs space-y-2 mt-3">
                <div className="flex items-center justify-between font-semibold">
                  <span className="text-[#183B56]">Predicted Signal:</span>
                  <span className="px-2 py-0.5 rounded bg-[#FFF0E9] text-[#EF806B] font-bold">
                    {screenMutation.data.screening.label}
                  </span>
                </div>
                <div className="text-[11px] text-[#64748B]">
                  Confidence: {(screenMutation.data.screening.confidence * 100).toFixed(1)}%
                </div>
                <p className="text-[11px] text-[#64748B] border-t border-[#E2E8F0] pt-1">
                  {screenMutation.data.screening.explanation}
                </p>
              </div>
            )}

            <div className="p-3 bg-[#F0FDF4] border border-[#DCFCE7] rounded text-[11px] text-[#166534] leading-relaxed">
              <strong>ℹ️ Probabilistic ML signal:</strong> Does not establish truth or empirical validity. Requires analyst corroboration.
            </div>
          </div>

          {/* Source Ingestion Health */}
          <div className="bg-white p-5 rounded-lg border border-[#E2E8F0] shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-[#087F83]" />
                <h4 className="font-bold text-sm text-[#183B56]">Source Ingestion Health</h4>
              </div>
              <span className="text-[10px] font-bold text-[#10B981] flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]"></span> {summary.active_sources_count} / {summary.total_configured_sources} Active
              </span>
            </div>

            <div className="space-y-3 text-xs">
              {summary.source_statuses.slice(0, 4).map((src: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-2 rounded bg-[#F8FAFC] border border-[#E2E8F0]">
                  <div>
                    <div className="font-semibold text-[#183B56]">{src.source_name}</div>
                    <div className="text-[10px] text-[#94A3B8]">
                      Fetched: {src.items_fetched} articles • {src.last_fetched_at ? new Date(src.last_fetched_at).toLocaleDateString() : 'Active'}
                    </div>
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 font-bold rounded ${
                    src.last_status === 'success' || src.last_status === 'active'
                      ? 'bg-[#E5F6F3] text-[#087F83]'
                      : 'bg-[#FFF5E5] text-[#E5A440]'
                  }`}>
                    {src.last_status.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
