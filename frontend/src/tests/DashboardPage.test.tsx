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
      expect(screen.getByTestId('featured-story')).toBeDefined();
      expect(screen.getByText('Showing 1 of 10 max')).toBeDefined();
    });
  });

  it('strictly bounds rendering to 10 articles when backend returns more than 10', async () => {
    // Generate 15 dummy articles
    const articles = Array.from({ length: 15 }, (_, i) => ({
      id: `art_${i + 1}`,
      title: `News Story Headline Number ${i + 1}`,
      publisher: `Publisher ${i % 3}`,
      url: `https://example.com/story-${i + 1}`,
      published_at: new Date(Date.now() - i * 3600000).toISOString(),
      ingested_at: new Date().toISOString(),
      source_type: 'rss',
      summary: `Summary of news story number ${i + 1}`,
      image_url: i === 0 ? 'https://example.com/featured.jpg' : null,
    }));

    vi.spyOn(newsApi, 'getDashboardSummary').mockResolvedValueOnce({
      total_articles: 100,
      active_sources_count: 5,
      total_configured_sources: 5,
      coverage_clusters_count: 10,
      fact_check_matches_count: 5,
      top_stories_limit: 10,
      top_stories_count: 10,
      recent_articles: articles,
      source_statuses: [],
      sources_distribution: { rss: 100 },
      publishers_distribution: { 'Publisher 0': 50 },
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
      // 1 featured story + 9 compact stories = 10 total displayed articles
      expect(screen.getByTestId('featured-story')).toBeDefined();
      const compactStories = screen.getAllByTestId('compact-story-card');
      expect(compactStories.length).toBe(9);
      expect(screen.getByText('Showing 10 of 10 max')).toBeDefined();

      // 11th through 15th articles should NEVER be rendered
      expect(screen.queryByText('News Story Headline Number 11')).toBeNull();
      expect(screen.queryByText('News Story Headline Number 15')).toBeNull();
    });
  });

  it('renders gracefully when 0 articles are available', async () => {
    vi.spyOn(newsApi, 'getDashboardSummary').mockResolvedValueOnce({
      total_articles: 0,
      active_sources_count: 0,
      total_configured_sources: 5,
      coverage_clusters_count: 0,
      fact_check_matches_count: 0,
      top_stories_limit: 10,
      top_stories_count: 0,
      recent_articles: [],
      source_statuses: [],
      sources_distribution: {},
      publishers_distribution: {},
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
      expect(screen.getByText('No Top Stories Available')).toBeDefined();
      expect(screen.getByText('Showing 0 of 10 max')).toBeDefined();
    });
  });
});
