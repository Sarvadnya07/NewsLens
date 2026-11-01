import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { IntegrationsPage } from '../pages/IntegrationsPage';
import { newsApi } from '../services/api';

vi.mock('../services/api', () => ({
  newsApi: {
    getIntegrationsOverview: vi.fn(),
    testProviderConnection: vi.fn(),
    refreshProvider: vi.fn(),
  },
}));

describe('IntegrationsPage', () => {
  it('renders overview metrics and provider cards without exposing secrets', async () => {
    vi.mocked(newsApi.getIntegrationsOverview).mockResolvedValueOnce({
      total_registered: 3,
      configured_count: 2,
      operational_count: 1,
      disabled_count: 0,
      awaiting_credentials_count: 1,
      providers: [
        {
          id: 'toi_national',
          name: 'The Times of India (National)',
          category: 'National',
          source_type: 'rss',
          domain: 'timesofindia.indiatimes.com',
          is_active: true,
          requires_api_key: false,
          is_configured: true,
          is_enabled: true,
          status_label: 'operational',
          items_count: 25,
          new_items_inserted: 5,
          supported_profiles: ['default'],
        },
        {
          id: 'newsdata_io',
          name: 'NewsData.io',
          category: 'Global Aggregator',
          source_type: 'newsdata',
          domain: 'newsdata.io',
          is_active: true,
          requires_api_key: true,
          env_key_name: 'NEWSDATA_API_KEY',
          is_configured: false,
          is_enabled: false,
          status_label: 'not_configured',
          items_count: 0,
          new_items_inserted: 0,
          supported_profiles: ['india_publishers', 'global_latest'],
        },
      ],
    });

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <IntegrationsPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Header assertions
    const title = await screen.findByText('API Integration Manager');
    expect(title).toBeDefined();
    expect(screen.getByText('Registered Providers')).toBeDefined();

    // Provider cards rendered
    expect(screen.getByText('The Times of India (National)')).toBeDefined();
    expect(screen.getByText('NewsData.io')).toBeDefined();
    expect(screen.getByText('NEWSDATA_API_KEY')).toBeDefined();

    // Verify secret non-disclosure: no raw fake keys or token values
    expect(screen.queryByText(/sk_live_/i)).toBeNull();
    expect(screen.queryByText(/Bearer [a-zA-Z0-9]/i)).toBeNull();
  });
});
