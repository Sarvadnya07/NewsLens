import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NewsMonitorPage } from '../pages/NewsMonitorPage';
import { newsApi } from '../services/api';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

describe('NewsMonitorPage', () => {
  it('renders search input, filter toolbar, and paginated article items', async () => {
    vi.spyOn(newsApi, 'getArticles').mockResolvedValueOnce({
      items: [
        {
          id: 'test_1',
          title: 'Reserve Bank of India Issues Directives on Lending',
          publisher: 'The Financial Express',
          url: 'https://example.com/article1',
          published_at: new Date().toISOString(),
          ingested_at: new Date().toISOString(),
          source_type: 'rss',
          summary: 'Central bank guidelines on lending apps.',
        },
      ],
      pagination: {
        page: 1,
        page_size: 10,
        total_items: 824,
        total_pages: 83,
      },
    });

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <NewsMonitorPage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('News Monitor')).toBeDefined();
      expect(screen.getByText('Reserve Bank of India Issues Directives on Lending')).toBeDefined();
      expect(screen.getByText('824')).toBeDefined();
    });
  });

  it('updates search query when form is submitted', async () => {
    vi.spyOn(newsApi, 'getArticles').mockResolvedValue({
      items: [],
      pagination: {
        page: 1,
        page_size: 10,
        total_items: 0,
        total_pages: 0,
      },
    });

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <NewsMonitorPage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    const input = screen.getByPlaceholderText(/Search headline keywords/i);
    fireEvent.change(input, { target: { value: 'Cyclone' } });
    const searchBtn = screen.getByText('Search Coverage');
    fireEvent.click(searchBtn);

    await waitFor(() => {
      expect((input as HTMLInputElement).value).toBe('Cyclone');
    });
  });
});
