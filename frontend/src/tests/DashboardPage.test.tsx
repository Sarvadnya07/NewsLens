import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DashboardPage } from '../pages/DashboardPage';
import { newsApi } from '../services/api';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

describe('DashboardPage', () => {
  it('renders 4 key telemetry metric cards and recent articles list', async () => {
    vi.spyOn(newsApi, 'getDashboardSummary').mockResolvedValueOnce({
      total_articles: 824,
      active_sources_count: 8,
      total_configured_sources: 8,
      coverage_clusters_count: 12,
      fact_check_matches_count: 8,
      recent_articles: [
        {
          id: 'art_1',
          title: 'Monsoon Deployment: NDRF Deploys Specialized Units Across Gujarat',
          publisher: 'Press Trust of India',
          url: 'https://example.com/ndrf',
          published_at: new Date().toISOString(),
          ingested_at: new Date().toISOString(),
          source_type: 'rss',
          summary: 'Pre-positioning of rescue teams follows meteorological forecasts.',
        },
      ],
      source_statuses: [
        {
          source_name: 'The Hindu',
          source_type: 'rss',
          last_status: 'success',
          items_fetched: 123,
          last_fetched_at: new Date().toISOString(),
          error_message: null,
        },
      ],
      sources_distribution: { rss: 819, manual: 5 },
      publishers_distribution: { 'The Hindu': 123 },
    });

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <DashboardPage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('ARTICLES RETRIEVED')).toBeDefined();
      expect(screen.getByText('824')).toBeDefined();
      expect(screen.getByText('ACTIVE SOURCES')).toBeDefined();
      expect(screen.getByText('Monsoon Deployment: NDRF Deploys Specialized Units Across Gujarat')).toBeDefined();
    });
  });
});
