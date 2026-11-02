import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { newsApi } from '../services/api';
import type { Article, IngestionRefreshParams, IngestionRefreshResponse } from '../types/api';
import {
  Search,
  RotateCw,
  ExternalLink,
  Cpu,
  AlertCircle,
  CheckCircle,
  Clock,
  Zap,
} from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';

export const NewsMonitorPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const query = searchParams.get('q') || '';
  const sourceType = searchParams.get('source') || 'all';
  const sortOrder = searchParams.get('sort') || 'Recency';
  const page = parseInt(searchParams.get('page') || '1', 10);

  const [inputSearch, setInputSearch] = useState(query);

  // Ingestion control state (independent from article filter state)
  const [selectedIngestTarget, setSelectedIngestTarget] = useState<
    'newsdata_india' | 'newsdata_global' | 'newsdata_intl_india' | 'rss' | 'gdelt' | 'all'
  >('newsdata_india');
  const [syncResult, setSyncResult] = useState<IngestionRefreshResponse | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  // Status & Quota Telemetry Query
  const { data: statusData } = useQuery({
    queryKey: ['ingestionStatus'],
    queryFn: () => newsApi.getIngestionStatus(),
    refetchInterval: 30000,
  });

  // Profile-specific Ingestion Mutation
  const syncMutation = useMutation({
    mutationFn: async () => {
      setSyncError(null);
      let payload: IngestionRefreshParams = { max_pages: 1 };
      if (selectedIngestTarget === 'newsdata_india') {
        payload = { source_type: 'newsdata', profile: 'india_publishers', max_pages: 1 };
      } else if (selectedIngestTarget === 'newsdata_global') {
        payload = { source_type: 'newsdata', profile: 'global_latest', max_pages: 1 };
      } else if (selectedIngestTarget === 'newsdata_intl_india') {
        payload = { source_type: 'newsdata', profile: 'india_global_coverage', max_pages: 1 };
      } else if (selectedIngestTarget === 'rss') {
        payload = { source_type: 'rss' };
      } else if (selectedIngestTarget === 'gdelt') {
        payload = { source_type: 'gdelt' };
      } else if (selectedIngestTarget === 'all') {
        payload = { source_type: 'all' };
      }
      return await newsApi.triggerRefresh(payload);
    },
    onSuccess: (res) => {
      setSyncResult(res);
      queryClient.invalidateQueries({ queryKey: ['articles'] });
      queryClient.invalidateQueries({ queryKey: ['ingestionStatus'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardSummary'] });
    },
    onError: (err: any) => {
      if (err?.code === 'ECONNABORTED' || err?.message?.includes('timeout')) {
        setSyncError(
          'Synchronization request timed out after 60 seconds. Upstream ingestion tasks may still be continuing in the background; refresh the feed view shortly to inspect updated articles.'
        );
      } else {
        setSyncError(err?.response?.data?.detail || err?.message || 'Sync failed.');
      }
    },
  });

  const getFilterParams = () => {
    if (sourceType === 'newsdata_india') {
      return { source_type: 'newsdata', discovery_profile: 'india_publishers' };
    }
    if (sourceType === 'newsdata_global') {
      return { source_type: 'newsdata', discovery_profile: 'global_latest' };
    }
    if (sourceType === 'newsdata_intl_india') {
      return { source_type: 'newsdata', discovery_profile: 'india_global_coverage' };
    }
    if (sourceType === 'newsdata') {
      return { source_type: 'newsdata', discovery_profile: undefined };
    }
    return {
      source_type: sourceType !== 'all' ? sourceType : undefined,
      discovery_profile: undefined,
    };
  };

  const { data, isLoading, error } = useQuery({
    queryKey: ['articles', { query, sourceType, sortOrder, page }],
    queryFn: () => {
      const filters = getFilterParams();
      return newsApi.getArticles({
        query: query || undefined,
        source_type: filters.source_type,
        discovery_profile: filters.discovery_profile,
        sort_order: sortOrder,
        page,
        page_size: 10,
      });
    },
  });

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchParams({
      q: inputSearch,
      source: sourceType,
      sort: sortOrder,
      page: '1',
    });
  };

  const handleFilterChange = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value === 'all' && key === 'source') {
      next.delete('source');
    } else {
      next.set(key, value);
    }
    next.set('page', '1');
    setSearchParams(next);
  };

  const quota = statusData?.quota;
  const isNewsDataTarget = selectedIngestTarget.startsWith('newsdata');
  const newsDataDisabled = isNewsDataTarget && quota && quota.daily_requests_used === 0 && quota.last_outcome === null && !quota.last_request_at;

  return (
    <div className="space-y-6">
      {/* Header matching Stitch Spec */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#E2E8F0]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-[#315FE8]"></span>
            <span className="text-[11px] font-bold tracking-wider text-[#64748B] uppercase">
              CONTINUOUS NEWS STREAM LEDGER
            </span>
          </div>
          <h2 className="text-3xl font-bold font-serif text-[#183B56] tracking-tight">News Monitor</h2>
          <p className="text-xs text-[#64748B] mt-1 max-w-2xl">
            Discover, audit, and cross-reference recent coverage across the Indian news ecosystem.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['articles'] })}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-[#CBD5E1] rounded-md text-xs font-semibold text-[#183B56] hover:bg-[#F8FAFC] shadow-xs cursor-pointer"
          >
            <RotateCw className="w-3.5 h-3.5" />
            Refresh Feed View
          </button>
        </div>
      </div>

      {/* Upstream Ingestion & Quota Governance Trigger Panel */}
      <div className="bg-[#F8FAFC] border border-[#CBD5E1] rounded-xl p-5 space-y-3.5 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-[#315FE8]" />
            <h3 className="text-xs font-bold text-[#183B56] uppercase tracking-wide">
              Live Ingestion & Profile Synchronization
            </h3>
          </div>

          {/* Last Sync Timestamp */}
          <div className="flex items-center gap-1.5 text-[11px] text-[#64748B]">
            <Clock className="w-3.5 h-3.5 text-[#94A3B8]" />
            <span>
              Last Sync:{' '}
              {statusData?.last_sync_timestamp
                ? new Date(statusData.last_sync_timestamp).toLocaleTimeString()
                : 'Awaiting initial trigger'}
            </span>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-1">
          <div className="flex-1">
            <label className="block text-[11px] font-medium text-[#475569] mb-1">
              Select Ingestion Channel / Discovery Profile:
            </label>
            <select
              value={selectedIngestTarget}
              onChange={(e) => {
                setSelectedIngestTarget(e.target.value as any);
                setSyncResult(null);
                setSyncError(null);
              }}
              disabled={syncMutation.isPending}
              className="w-full px-3 py-2 bg-white border border-[#CBD5E1] rounded-lg text-xs text-[#183B56] focus:outline-none focus:border-[#315FE8] font-sans"
            >
              <option value="newsdata_india">NewsData.io — Indian Publishers (country='in')</option>
              <option value="newsdata_global">NewsData.io — Global Latest (international)</option>
              <option value="newsdata_intl_india">
                NewsData.io — Intl Coverage on India (excludecountry='in', q='India')
              </option>
              <option value="rss">Curated Indian RSS Feeds (6 Newsrooms)</option>
              <option value="gdelt">GDELT 2.0 DOC API (Global Monitored)</option>
              <option value="all">All Channels (Parallel Sync)</option>
            </select>
          </div>

          <div className="sm:self-end">
            <button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className={`w-full sm:w-auto flex items-center justify-center gap-2 px-5 py-2 rounded-lg text-xs font-semibold text-white transition-all shadow-xs cursor-pointer ${
                syncMutation.isPending
                  ? 'bg-[#94A3B8] cursor-not-allowed'
                  : 'bg-gradient-to-r from-[#183B56] to-[#20496B] hover:from-[#20496B] hover:to-[#315FE8]'
              }`}
            >
              <RotateCw className={`w-3.5 h-3.5 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
              {syncMutation.isPending ? 'Synchronizing...' : 'Trigger Ingestion'}
            </button>
          </div>
        </div>

        {/* Live Quota Governance Display for NewsData.io */}
        {isNewsDataTarget && quota && (
          <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-[#E2E8F0] text-[11px] text-[#475569]">
            <span className="font-semibold text-[#183B56]">Quota Ledger:</span>
            <span>
              Daily Used:{' '}
              <strong className={quota.daily_requests_used >= quota.daily_requests_budget ? 'text-red-600' : 'text-[#183B56]'}>
                {quota.daily_requests_used} / {quota.daily_requests_budget}
              </strong>
            </span>
            <span>•</span>
            <span>
              Rolling 15m:{' '}
              <strong className={quota.rolling_15m_used >= quota.rolling_15m_budget ? 'text-red-600' : 'text-[#183B56]'}>
                {quota.rolling_15m_used} / {quota.rolling_15m_budget}
              </strong>
            </span>
            <span>•</span>
            <span>
              Remaining:{' '}
              <strong className="text-[#087F83]">
                {Math.max(0, quota.daily_requests_budget - quota.daily_requests_used)} requests
              </strong>
            </span>
            {quota.is_exhausted && (
              <span className="ml-auto inline-flex items-center gap-1 text-red-600 font-bold">
                <AlertCircle className="w-3.5 h-3.5" /> Quota Exhausted
              </span>
            )}
          </div>
        )}

        {/* Configuration Notice when NewsData.io Key is Unset */}
        {newsDataDisabled && (
          <div className="p-2 bg-amber-50 border border-amber-200 rounded text-[11px] text-amber-800 flex items-center gap-2">
            <AlertCircle className="w-3.5 h-3.5 shrink-0 text-amber-600" />
            <span>
              <strong>Provider Key Pending:</strong> <code>NEWSDATA_API_KEY</code> is not yet configured. Live upstream calls will cleanly degrade to disabled status until an API key is provided.
            </span>
          </div>
        )}

        {/* Sync Execution Outcome Banner */}
        {syncResult && (
          <div
            className={`p-2.5 rounded text-xs flex flex-col md:flex-row md:items-center justify-between gap-2 border ${
              syncResult.success
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-amber-50 border-amber-200 text-amber-800'
            }`}
          >
            <div className="flex items-center gap-2">
              {syncResult.success ? (
                <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
              )}
              <span>
                <strong>Execution Result:</strong> Profile{' '}
                <code>{syncResult.discovery_profile || selectedIngestTarget}</code> executed in{' '}
                {syncResult.duration_ms.toFixed(0)}ms • Fetched{' '}
                <strong>{syncResult.total_fetched}</strong> items • Inserted{' '}
                <strong>{syncResult.new_stored}</strong> new articles.
              </span>
            </div>

            {syncResult.quota_telemetry && (
              <span className="text-[11px] font-medium text-emerald-700 bg-white/60 px-2 py-0.5 rounded shrink-0">
                Quota Left: {syncResult.quota_telemetry.daily_requests_budget - syncResult.quota_telemetry.daily_requests_used}
              </span>
            )}
          </div>
        )}

        {syncError && (
          <div className="p-2.5 bg-red-50 border border-red-200 rounded text-xs text-red-700 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
            <span>
              <strong>Ingestion Error:</strong> {syncError}
            </span>
          </div>
        )}
      </div>

      {/* Multi-Axis Filter Toolbar */}
      <div className="bg-white p-5 rounded-xl border border-[#E2E8F0] shadow-xs space-y-3.5 hover:border-[#CBD5E1] transition-all">
        <form onSubmit={handleSearchSubmit} className="flex gap-2.5">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-[#94A3B8] absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={inputSearch}
              onChange={(e) => setInputSearch(e.target.value)}
              placeholder="Search headline keywords across ingested Indian news archive..."
              className="w-full pl-10 pr-4 py-2 text-xs bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg focus:outline-none focus:border-[#315FE8] font-sans"
            />
          </div>
          <button
            type="submit"
            className="px-5 py-2 bg-gradient-to-r from-[#183B56] to-[#20496B] hover:from-[#20496B] hover:to-[#315FE8] text-white rounded-lg text-xs font-semibold transition-all shadow-xs cursor-pointer"
          >
            Search Coverage
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-4 pt-2.5 border-t border-[#F1F5F9] text-xs">
          <div className="flex items-center gap-2">
            <span className="text-[#64748B] font-medium">Ingestion Pipe:</span>
            <select
              value={sourceType}
              onChange={(e) => handleFilterChange('source', e.target.value)}
              className="px-3 py-1.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg text-xs focus:outline-none font-sans"
            >
              <option value="all">Source: All (GDELT + RSS + NewsData)</option>
              <option value="rss">Source: Syndicated RSS Only</option>
              <option value="gdelt">Source: GDELT v2 Discovered</option>
              <option value="newsdata">Source: NewsData.io (All Profiles)</option>
              <option value="newsdata_india">Source: NewsData.io (Indian Publishers)</option>
              <option value="newsdata_global">Source: NewsData.io (Global Latest)</option>
              <option value="newsdata_intl_india">Source: NewsData.io (Intl on India)</option>
              <option value="manual">Source: User Submitted</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[#64748B] font-medium">Ranking Metric:</span>
            <select
              value={sortOrder}
              onChange={(e) => handleFilterChange('sort', e.target.value)}
              className="px-3 py-1.5 bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg text-xs focus:outline-none font-sans"
            >
              <option value="Recency">Sort: Recency (Newest First)</option>
              <option value="Oldest">Sort: Chronological (Oldest First)</option>
            </select>
          </div>

          {query && (
            <button
              onClick={() => {
                setInputSearch('');
                setSearchParams({ source: sourceType, sort: sortOrder, page: '1' });
              }}
              className="text-xs text-[#EF806B] hover:underline ml-auto font-medium cursor-pointer"
            >
              Clear Search Query
            </button>
          )}
        </div>
      </div>

      {/* Methodological Alert Banner */}
      <div className="p-3.5 bg-[#EBF8FF] border border-[#BEE3F8] rounded-xl text-xs text-[#087F83] flex items-center justify-between shadow-xs">
        <div>
          <strong>ℹ️ Methodological Note:</strong> Results aggregate open syndicated feeds and GDELT open-data endpoints. Duplicate reports frequently represent wire distribution (PTI/ANI) rather than independent corroboration.
        </div>
        <Link to="/methodology" className="font-bold underline text-[11px] whitespace-nowrap ml-4">
          Review pipeline specs →
        </Link>
      </div>

      {/* Article Results Ledger */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-[#64748B] bg-white rounded-xl border border-[#E2E8F0] shadow-xs">
          Scanning database and retrieving matching records...
        </div>
      ) : error || !data ? (
        <div className="p-6 bg-red-50 text-red-700 rounded-xl border border-red-200 text-xs shadow-xs">
          Error retrieving articles from database.
        </div>
      ) : data.items.length === 0 ? (
        <div className="p-12 text-center text-xs text-[#64748B] bg-white rounded-xl border border-[#E2E8F0] shadow-xs">
          No news articles found matching the current criteria.
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-[#64748B] px-1">
            <span>
              <strong>{data.pagination.total_items}</strong> records identified • Page {data.pagination.page} of {data.pagination.total_pages}
            </span>
          </div>

          <div className="space-y-3.5">
            {data.items.map((art: Article) => (
              <article
                key={art.id}
                className="bg-white p-5 sm:p-6 rounded-xl border border-[#E2E8F0] shadow-xs hover:shadow-md hover:border-[#CBD5E1] transition-all space-y-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[#F1F5F9] text-[#475569]">
                      {art.source_type}
                    </span>
                    <span className="font-semibold text-[#183B56]">{art.publisher}</span>
                    <span className="text-[#94A3B8]">
                      • {new Date(art.published_at).toLocaleString()}
                    </span>
                  </div>

                  <span className="text-[10px] px-2 py-0.5 bg-[#E5F6F3] text-[#087F83] font-bold rounded">
                    Archived Still
                  </span>
                </div>

                <h3 className="text-lg font-bold font-serif text-[#142B4A] leading-snug">
                  {art.title}
                </h3>

                {art.summary && (
                  <p className="text-xs text-[#64748B] leading-relaxed line-clamp-2">
                    {art.summary}
                  </p>
                )}

                <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[#F1F5F9] text-xs">
                  <div className="flex items-center gap-3">
                    <Link
                      to={`/analyze?text=${encodeURIComponent(art.title)}`}
                      className="px-3 py-1 bg-[#183B56] hover:bg-[#20496B] text-white rounded text-xs font-semibold flex items-center gap-1.5 transition-colors"
                    >
                      <Cpu className="w-3.5 h-3.5" /> Analyze in Model
                    </Link>

                    <Link
                      to={`/evidence?article_id=${art.id}`}
                      className="px-3 py-1 bg-white border border-[#CBD5E1] text-[#183B56] hover:bg-[#F8FAFC] rounded text-xs font-semibold flex items-center gap-1.5 transition-colors"
                    >
                      Trace Provenance & Coverage
                    </Link>
                  </div>

                  <a
                    href={art.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-[#64748B] hover:text-[#183B56] font-medium"
                  >
                    Open Source <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </article>
            ))}
          </div>

          {/* Pagination Controls */}
          {data.pagination.total_pages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-[#E2E8F0] text-xs">
              <button
                disabled={page <= 1}
                onClick={() => handleFilterChange('page', String(page - 1))}
                className="px-3 py-1.5 bg-white border border-[#CBD5E1] rounded text-[#183B56] font-semibold disabled:opacity-40 cursor-pointer"
              >
                Previous
              </button>
              <span className="text-[#64748B] font-medium">
                Page {page} of {data.pagination.total_pages}
              </span>
              <button
                disabled={page >= data.pagination.total_pages}
                onClick={() => handleFilterChange('page', String(page + 1))}
                className="px-3 py-1.5 bg-white border border-[#CBD5E1] rounded text-[#183B56] font-semibold disabled:opacity-40 cursor-pointer"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
