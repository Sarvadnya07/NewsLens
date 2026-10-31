import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AnalyzeArticlePage } from '../pages/AnalyzeArticlePage';
import { newsApi } from '../services/api';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

describe('AnalyzeArticlePage', () => {
  it('renders input workbench and allows sample claim loading', async () => {
    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AnalyzeArticlePage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    expect(screen.getByText('DIAGNOSTIC WORKBENCH')).toBeDefined();
    expect(screen.getByText('Analyze Article')).toBeDefined();
    expect(screen.getByText('Load Example Claim')).toBeDefined();

    const loadExampleBtn = screen.getByText('Load Example Claim');
    fireEvent.click(loadExampleBtn);

    const textarea = screen.getByPlaceholderText(
      /Paste news headline or claim body to evaluate framing/i
    ) as HTMLTextAreaElement;
    expect(textarea.value).toContain('Ministry of Railways');
  });

  it('submits text and displays screening results when analyze is clicked', async () => {
    vi.spyOn(newsApi, 'analyzeArticle').mockResolvedValueOnce({
      input_text: 'Test headline',
      screening: {
        label: 'Lower-veracity linguistic pattern',
        confidence: 0.82,
        score: 0.82,
        is_uncertain: false,
        explanation: 'Lexical panic markers detected.',
        decision_threshold: 0.5,
        influential_tokens: [{ token: 'urgent', weight: '+0.42' }],
      },
      related_coverage: [],
      fact_check_matches: [],
      analysis_timestamp: new Date().toISOString(),
    });

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AnalyzeArticlePage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    const loadExampleBtn = screen.getByText('Load Example Claim');
    fireEvent.click(loadExampleBtn);

    const submitBtn = screen.getByText('Screen Article Content');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('Model Screening Result')).toBeDefined();
      expect(screen.getByText('Lower-veracity linguistic pattern')).toBeDefined();
      expect(screen.getByText('urgent')).toBeDefined();
    });
  });
});
