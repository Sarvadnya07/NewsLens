import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { newsApi } from '../services/api';
import type { Article } from '../types/api';
import { Search, RotateCw, ExternalLink, Cpu } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';

export const NewsMonitorPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const query = searchParams.get('q') || '';
  const sourceType = searchParams.get('source') || 'all';
  const sortOrder = searchParams.get('sort') || 'Recency';
  const page = parseInt(searchParams.get('page') || '1', 10);

  const [inputSearch, setInputSearch] = useState(query);

  const { data, isLoading, error } = useQuery({
    queryKey: ['articles', { query, sourceType, sortOrder, page }],
    queryFn: () =>
      newsApi.getArticles({
        query: query || undefined,
        source_type: sourceType !== 'all' ? sourceType : undefined,
        sort_order: sortOrder,
        page,
        page_size: 10,
      }),
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
            Refresh Feed
          </button>
        </div>
      </div>

      {/* Multi-Axis Filter Toolbar */}
      <div className="bg-white p-4 rounded-lg border border-[#E2E8F0] shadow-xs space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-[#94A3B8] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={inputSearch}
              onChange={(e) => setInputSearch(e.target.value)}
              placeholder="Search headline keywords across ingested Indian news archive..."
              className="w-full pl-9 pr-4 py-2 text-xs bg-[#F8FAFC] border border-[#CBD5E1] rounded-md focus:outline-none focus:border-[#315FE8]"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-[#183B56] hover:bg-[#20496B] text-white rounded text-xs font-semibold transition-colors cursor-pointer"
          >
            Search Coverage
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-[#F1F5F9] text-xs">
          <div className="flex items-center gap-2">
            <span className="text-[#64748B] font-medium">Ingestion Pipe:</span>
            <select
              value={sourceType}
              onChange={(e) => handleFilterChange('source', e.target.value)}
              className="px-2 py-1 bg-[#F8FAFC] border border-[#CBD5E1] rounded text-xs focus:outline-none"
            >
              <option value="all">Source: All (GDELT + RSS)</option>
              <option value="rss">Source: Syndicated RSS Only</option>
              <option value="gdelt">Source: GDELT v2 Discovered</option>
              <option value="manual">Source: User Submitted</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[#64748B] font-medium">Ranking Metric:</span>
            <select
              value={sortOrder}
              onChange={(e) => handleFilterChange('sort', e.target.value)}
              className="px-2 py-1 bg-[#F8FAFC] border border-[#CBD5E1] rounded text-xs focus:outline-none"
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
      <div className="p-3 bg-[#EBF8FF] border border-[#BEE3F8] rounded text-xs text-[#087F83] flex items-center justify-between">
        <div>
          <strong>ℹ️ Methodological Note:</strong> Results aggregate open syndicated feeds and GDELT open-data endpoints. Duplicate reports frequently represent wire distribution (PTI/ANI) rather than independent corroboration.
        </div>
        <Link to="/methodology" className="font-bold underline text-[11px] whitespace-nowrap ml-4">
          Review pipeline specs →
        </Link>
      </div>

      {/* Article Results Ledger */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-[#64748B] bg-white rounded-lg border border-[#E2E8F0]">
          Scanning database and retrieving matching records...
        </div>
      ) : error || !data ? (
        <div className="p-6 bg-red-50 text-red-700 rounded-lg border border-red-200 text-xs">
          Error retrieving articles from database.
        </div>
      ) : data.items.length === 0 ? (
        <div className="p-12 text-center text-xs text-[#64748B] bg-white rounded-lg border border-[#E2E8F0]">
          No news articles found matching the current criteria.
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-[#64748B]">
            <span>
              <strong>{data.pagination.total_items}</strong> records identified • Page {data.pagination.page} of {data.pagination.total_pages}
            </span>
          </div>

          <div className="space-y-3">
            {data.items.map((art: Article) => (
              <article
                key={art.id}
                className="bg-white p-5 rounded-lg border border-[#E2E8F0] shadow-xs hover:border-[#CBD5E1] transition-all space-y-3"
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
