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
  Sparkles,
  Newspaper,
  Image as ImageIcon,
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [quickText, setQuickText] = useState('');
  const [activeTab, setActiveTab] = useState<'all' | 'gdelt' | 'rss' | 'newsdata'>('all');
  const [failedImages, setFailedImages] = useState<Record<string, boolean>>({});

  const { data: summary, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => newsApi.getDashboardSummary(),
  });

  const screenMutation = useMutation({
    mutationFn: (text: string) => newsApi.analyzeArticle({ text }),
  });

  const handleImageError = (articleId: string) => {
    setFailedImages((prev) => ({ ...prev, [articleId]: true }));
  };

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
    if (activeTab === 'newsdata') return art.source_type.toLowerCase() === 'newsdata';
    return true;
  });

  // Strict hard limit enforcement: max 10 stories on Dashboard
  const top10Articles = filteredArticles.slice(0, 10);
  const featuredArticle = top10Articles.length > 0 ? top10Articles[0] : null;
  const compactArticles = top10Articles.slice(1);

  return (
    <div className="space-y-8">
      {/* Page Title & Context Header */}
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
            Finite, curated observatory displaying top verified intelligence. Capped strictly at a maximum of 10 stories with recency and publisher diversity guarantees.
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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Metric 1 */}
        <div className="bg-white p-5 rounded-xl border border-[#E2E8F0] shadow-xs hover:shadow-md hover:border-[#CBD5E1] transition-all relative overflow-hidden group">
          <div className="absolute top-0 left-0 right-0 h-1 bg-[#315FE8] group-hover:h-1.5 transition-all" />
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
          <p className="text-[11px] text-[#94A3B8] mt-2">Across GDELT & configured RSS feeds</p>
        </div>

        {/* Metric 2 */}
        <div className="bg-white p-5 rounded-xl border border-[#E2E8F0] shadow-xs hover:shadow-md hover:border-[#CBD5E1] transition-all relative overflow-hidden group">
          <div className="absolute top-0 left-0 right-0 h-1 bg-[#087F83] group-hover:h-1.5 transition-all" />
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
        <div className="bg-white p-5 rounded-xl border border-[#E2E8F0] shadow-xs hover:shadow-md hover:border-[#CBD5E1] transition-all relative overflow-hidden group">
          <div className="absolute top-0 left-0 right-0 h-1 bg-[#7867D8] group-hover:h-1.5 transition-all" />
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
        <div className="bg-white p-5 rounded-xl border border-[#E2E8F0] shadow-xs hover:shadow-md hover:border-[#CBD5E1] transition-all relative overflow-hidden group">
          <div className="absolute top-0 left-0 right-0 h-1 bg-[#E5A440] group-hover:h-1.5 transition-all" />
          <div className="flex items-center justify-between text-xs text-[#64748B] mb-2 font-medium">
            <span>FACT-CHECK MATCHES</span>
            <span className="px-2 py-0.5 rounded bg-[#FFF5E5] text-[#E5A440] text-[10px] font-bold">INDEXED</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-[#142B4A] tabular-nums font-serif">
              {summary.fact_check_matches_count}
            </span>
            <span className="text-xs text-[#64748B]">archived claims</span>
          </div>
          <p className="text-[11px] text-[#94A3B8] mt-2">BM25Plus fact-check claim archive</p>
        </div>
      </div>

      {/* Main Grid: Editorial Top 10 Layout (Left) & Right-Rail Widgets */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-8">
        {/* Left Column: Top 10 Editorial Experience */}
        <div className="xl:col-span-8 space-y-6">
          {/* Header & Source Filter Tabs */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E2E8F0] pb-3">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 bg-[#183B56] text-white text-xs font-bold rounded flex items-center gap-1.5 shadow-xs">
                <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                Curated Top Stories
              </span>
              <span className="text-xs text-[#64748B] font-medium bg-[#F1F5F9] px-2 py-1 rounded">
                Showing {top10Articles.length} of {Math.min(10, summary.top_stories_limit || 10)} max
              </span>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setActiveTab('all')}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
                  activeTab === 'all'
                    ? 'bg-[#183B56] text-white shadow-xs'
                    : 'text-[#64748B] hover:text-[#183B56] hover:bg-[#F1F5F9]'
                }`}
              >
                All Sources
              </button>
              <button
                onClick={() => setActiveTab('gdelt')}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
                  activeTab === 'gdelt'
                    ? 'bg-[#183B56] text-white shadow-xs'
                    : 'text-[#64748B] hover:text-[#183B56] hover:bg-[#F1F5F9]'
                }`}
              >
                GDELT
              </button>
              <button
                onClick={() => setActiveTab('rss')}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
                  activeTab === 'rss'
                    ? 'bg-[#183B56] text-white shadow-xs'
                    : 'text-[#64748B] hover:text-[#183B56] hover:bg-[#F1F5F9]'
                }`}
              >
                RSS
              </button>
              <button
                onClick={() => setActiveTab('newsdata')}
                className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors cursor-pointer ${
                  activeTab === 'newsdata'
                    ? 'bg-[#183B56] text-white shadow-xs'
                    : 'text-[#64748B] hover:text-[#183B56] hover:bg-[#F1F5F9]'
                }`}
              >
                NewsData
              </button>
            </div>
          </div>

          {top10Articles.length === 0 ? (
            <div className="p-10 bg-white border border-[#E2E8F0] rounded-xl text-center space-y-3 shadow-xs">
              <Newspaper className="w-10 h-10 text-[#94A3B8] mx-auto" />
              <h3 className="font-serif font-bold text-lg text-[#183B56]">No Top Stories Available</h3>
              <p className="text-xs text-[#64748B] max-w-sm mx-auto">
                No articles found matching the current source filter. Try selecting 'All Sources' or refreshing ingestion.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* FEATURED STORY (1 Story with Prominent Layout) */}
              {featuredArticle && (
                <article
                  data-testid="featured-story"
                  className="bg-white rounded-xl border border-[#CBD5E1] shadow-sm hover:shadow-md hover:border-[#94A3B8] transition-all overflow-hidden"
                >
                  <div className="relative">
                    {/* Featured Image or Styled Editorial Fallback */}
                    {featuredArticle.image_url && !failedImages[featuredArticle.id] ? (
                      <div className="relative h-72 sm:h-80 xl:h-96 w-full bg-[#0F172A] overflow-hidden">
                        <img
                          src={featuredArticle.image_url}
                          alt={featuredArticle.title}
                          onError={() => handleImageError(featuredArticle.id)}
                          className="w-full h-full object-cover transition-transform duration-700 hover:scale-105"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-transparent" />
                        <div className="absolute top-4 left-4 flex items-center gap-2">
                          <span className="px-3 py-1 rounded-md bg-amber-500 text-black text-[10px] font-black uppercase tracking-wider shadow">
                            ★ FEATURED LEAD STORY
                          </span>
                          <span className="px-2.5 py-1 rounded-md bg-black/60 backdrop-blur-xs text-white text-[10px] font-bold uppercase tracking-wider">
                            {featuredArticle.source_type}
                          </span>
                        </div>
                        <div className="absolute bottom-4 left-5 right-5 flex items-center justify-between text-xs text-white/95">
                          <span className="font-semibold text-sm">{featuredArticle.publisher}</span>
                          <span className="text-xs text-white/80 font-mono">
                            {new Date(featuredArticle.published_at).toLocaleString()}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="h-52 sm:h-60 w-full bg-gradient-to-br from-[#142B4A] via-[#1E4E79] to-[#0A192F] p-6 sm:p-8 flex flex-col justify-between text-white relative overflow-hidden">
                        <div className="absolute -right-8 -bottom-8 opacity-10 pointer-events-none">
                          <Newspaper className="w-64 h-64 text-white" />
                        </div>
                        <div className="flex items-center justify-between relative z-10">
                          <div className="flex items-center gap-2">
                            <span className="px-3 py-1 rounded-md bg-amber-400 text-black text-[10px] font-black uppercase tracking-wider shadow">
                              ★ FEATURED LEAD STORY
                            </span>
                            <span className="px-2.5 py-1 rounded-md bg-white/20 backdrop-blur-xs text-white text-[10px] font-bold uppercase tracking-wider">
                              {featuredArticle.source_type}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5 text-white/80 text-xs font-medium">
                            <ImageIcon className="w-4 h-4" />
                            <span>Editorial Archival View</span>
                          </div>
                        </div>
                        <div className="flex items-center justify-between text-xs text-white/90 border-t border-white/15 pt-3 relative z-10">
                          <span className="font-bold tracking-wide text-amber-300 text-sm">{featuredArticle.publisher}</span>
                          <span className="text-xs text-white/80 font-mono">
                            {new Date(featuredArticle.published_at).toLocaleString()}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Featured Content Details */}
                  <div className="p-6 sm:p-7 space-y-3.5">
                    <h3 className="text-xl sm:text-2xl xl:text-3xl font-bold font-serif text-[#142B4A] leading-snug">
                      {featuredArticle.title}
                    </h3>

                    {featuredArticle.summary && (
                      <p className="text-sm xl:text-base text-[#475569] leading-relaxed line-clamp-3 font-normal">
                        {featuredArticle.summary}
                      </p>
                    )}

                    <div className="flex flex-wrap items-center justify-between pt-4 border-t border-[#F1F5F9] gap-4 text-xs">
                      <div className="flex items-center gap-4">
                        <Link
                          to={`/evidence?article_id=${featuredArticle.id}`}
                          className="text-[#315FE8] hover:text-[#1E40AF] font-bold flex items-center gap-1"
                        >
                          Examine Coverage <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                        <Link
                          to={`/analyze?text=${encodeURIComponent(featuredArticle.title)}`}
                          className="text-[#64748B] hover:text-[#183B56] font-medium"
                        >
                          Screen in ML Analyzer
                        </Link>
                      </div>

                      <a
                        href={featuredArticle.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-[#64748B] hover:text-[#183B56] font-semibold"
                      >
                        Read Source Article <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </div>
                  </div>
                </article>
              )}

              {/* COMPACT STORIES (Up to 9 stories in a responsive 3-column grid for 1080p) */}
              {compactArticles.length > 0 && (
                <div className="space-y-3.5">
                  <div className="flex items-center justify-between text-xs font-semibold text-[#64748B] uppercase tracking-wider px-1">
                    <span>Selected Briefings ({compactArticles.length})</span>
                    <span>Finite Curated Feed (3×3 Grid)</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4.5" data-testid="compact-stories-grid">
                    {compactArticles.map((article: Article) => (
                      <article
                        key={article.id}
                        data-testid="compact-story-card"
                        className="bg-white p-4.5 rounded-xl border border-[#E2E8F0] shadow-xs hover:shadow-md hover:border-[#CBD5E1] transition-all flex flex-col justify-between space-y-3"
                      >
                        <div className="space-y-2.5">
                          <div className="flex items-center justify-between text-xs">
                            <div className="flex items-center gap-1.5 overflow-hidden">
                              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider bg-[#F1F5F9] text-[#475569] shrink-0">
                                {article.source_type}
                              </span>
                              <span className="font-semibold text-[#183B56] truncate max-w-[130px]">
                                {article.publisher}
                              </span>
                            </div>
                            <span className="text-[10px] text-[#94A3B8] font-mono shrink-0">
                              {new Date(article.published_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>

                          {/* Thumbnail if available */}
                          {article.image_url && !failedImages[article.id] && (
                            <div className="w-full h-32 bg-[#F1F5F9] rounded-lg overflow-hidden">
                              <img
                                src={article.image_url}
                                alt={article.title}
                                onError={() => handleImageError(article.id)}
                                className="w-full h-full object-cover transition-transform duration-500 hover:scale-105"
                              />
                            </div>
                          )}

                          <h4 className="text-sm font-bold text-[#142B4A] font-serif leading-snug line-clamp-2">
                            {article.title}
                          </h4>

                          {article.summary && (
                            <p className="text-xs text-[#64748B] leading-relaxed line-clamp-2">
                              {article.summary}
                            </p>
                          )}
                        </div>

                        <div className="flex items-center justify-between pt-2.5 border-t border-[#F8FAFC] text-xs">
                          <Link
                            to={`/evidence?article_id=${article.id}`}
                            className="text-[#315FE8] hover:text-[#1E40AF] font-semibold text-[11px] flex items-center gap-0.5"
                          >
                            Examine <ArrowRight className="w-3 h-3" />
                          </Link>

                          <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-[#94A3B8] hover:text-[#475569] text-[11px]"
                          >
                            Source <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        </div>
                      </article>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Quick Article Screening, Ingestion Health & Publisher Density */}
        <div className="xl:col-span-4 space-y-6">
          {/* Quick Screening Widget */}
          <div className="bg-white p-5 rounded-xl border border-[#E2E8F0] shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-[#315FE8]" />
                <h4 className="font-bold text-sm text-[#183B56]">Quick Article Screening</h4>
              </div>
              <span className="text-[10px] font-bold text-[#64748B] uppercase bg-[#F1F5F9] px-2 py-0.5 rounded">Fast Inference</span>
            </div>

            <p className="text-xs text-[#64748B] leading-relaxed">
              Evaluate claim syntax or unverified headlines against trained linguistic distortion benchmarks.
            </p>

            <textarea
              rows={4}
              value={quickText}
              onChange={(e) => setQuickText(e.target.value)}
              placeholder="Paste headline or text excerpt to screen for linguistic framing anomalies..."
              className="w-full p-3 text-xs bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg focus:outline-none focus:border-[#315FE8] focus:ring-1 focus:ring-[#315FE8] font-sans"
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
                className="px-4 py-2 bg-[#183B56] hover:bg-[#20496B] text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 shadow-xs cursor-pointer"
              >
                {screenMutation.isPending ? 'Screening...' : 'Run Screening'}
              </button>
            </div>

            {/* Screening Result if executed */}
            {screenMutation.data && (
              <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-xs space-y-2 mt-3">
                <div className="flex items-center justify-between font-semibold">
                  <span className="text-[#183B56]">Predicted Signal:</span>
                  <span className="px-2 py-0.5 rounded bg-[#FFF0E9] text-[#EF806B] font-bold">
                    {screenMutation.data.screening.label}
                  </span>
                </div>
                <div className="text-[11px] text-[#64748B] font-mono">
                  Confidence: {(screenMutation.data.screening.confidence * 100).toFixed(1)}%
                </div>
                <p className="text-[11px] text-[#64748B] border-t border-[#E2E8F0] pt-1 leading-relaxed">
                  {screenMutation.data.screening.explanation}
                </p>
              </div>
            )}

            <div className="p-3 bg-[#F0FDF4] border border-[#DCFCE7] rounded-lg text-[11px] text-[#166534] leading-relaxed">
              <strong>ℹ️ Probabilistic ML signal:</strong> Does not establish truth or empirical validity. Requires analyst corroboration.
            </div>
          </div>

          {/* Publisher Density Visualizer */}
          {summary.publishers_distribution && Object.keys(summary.publishers_distribution).length > 0 && (
            <div className="bg-white p-5 rounded-xl border border-[#E2E8F0] shadow-xs space-y-3.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Newspaper className="w-4 h-4 text-[#315FE8]" />
                  <h4 className="font-bold text-sm text-[#183B56]">Top Publisher Density</h4>
                </div>
                <span className="text-[10px] text-[#64748B] font-mono">Diversity Metric</span>
              </div>
              <div className="space-y-2.5">
                {Object.entries(summary.publishers_distribution)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 4)
                  .map(([pub, count], idx) => {
                    const pct = Math.min(Math.round((count / (summary.total_articles || 1)) * 100), 100);
                    return (
                      <div key={idx} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="font-semibold text-[#183B56] truncate max-w-[190px]">{pub}</span>
                          <span className="text-[#64748B] text-[11px] font-mono tabular-nums">{count} ({pct}%)</span>
                        </div>
                        <div className="w-full h-1.5 bg-[#F1F5F9] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-[#315FE8] to-[#27C6C1] rounded-full"
                            style={{ width: `${Math.max(pct, 5)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Source Ingestion Health */}
          <div className="bg-white p-5 rounded-xl border border-[#E2E8F0] shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-[#087F83]" />
                <h4 className="font-bold text-sm text-[#183B56]">Source Ingestion Health</h4>
              </div>
              <span className="text-[10px] font-bold text-[#10B981] flex items-center gap-1 bg-[#E5F6F3] px-2 py-0.5 rounded">
                <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] animate-pulse"></span> {summary.active_sources_count} / {summary.total_configured_sources} Active
              </span>
            </div>

            <div className="space-y-2.5 text-xs">
              {summary.source_statuses.slice(0, 4).map((src: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-2.5 rounded-lg bg-[#F8FAFC] border border-[#E2E8F0]">
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
