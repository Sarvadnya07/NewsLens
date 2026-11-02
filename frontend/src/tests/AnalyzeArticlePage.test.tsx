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

  it('renders dynamic evidence assessment and distinguishes syndication from independent coverage', async () => {
    vi.spyOn(newsApi, 'analyzeArticle').mockResolvedValueOnce({
      input_text: 'Reliance Foundation announces scholarship program across 15 states',
      screening: {
        label: 'Insufficient / No Meaningful Model Signal',
        confidence: 0.5,
        score: 0.5,
        is_uncertain: true,
        explanation: 'None of the words in the submitted text overlap with the trained vocabulary.',
        decision_threshold: 0.5,
        influential_tokens: [],
      },
      related_coverage: [
        {
          title: 'Reliance Foundation launches education grant for students',
          publisher: 'PTI News Wire',
          url: 'https://example.com/pti-grant',
          published_at: '2026-11-01T10:00:00Z',
          similarity: 0.95,
          relationship: 'exact_or_republished',
          is_syndication: true,
        },
        {
          title: 'New scholarship options for rural undergraduate students',
          publisher: 'The Hindu',
          url: 'https://example.com/hindu-scholarship',
          published_at: '2026-11-01T11:00:00Z',
          similarity: 0.62,
          relationship: 'similar_coverage',
          is_syndication: false,
        },
      ],
      fact_check_matches: [],
      evidence_assessment: {
        available_evidence: [
          'Wire republication / syndication pattern: 1 source(s) share identical or verbatim agency copy.',
          'Independent reporting indexed from 1 distinct coverage article(s) across publishers (The Hindu).',
        ],
        missing_evidence: [
          'No indexed records from accredited Indian fact-checking watchdogs match this specific submission.',
          'Primary source documentation is not linked in the input text.',
        ],
        analytical_recommendations:
          'Independent editorial cross-verification required. Consult accredited press agency wire releases.',
      },
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

    const textarea = screen.getByPlaceholderText(
      /Paste news headline or claim body to evaluate framing/i
    ) as HTMLTextAreaElement;
    fireEvent.change(textarea, {
      target: { value: 'Reliance Foundation announces scholarship program across 15 states' },
    });

    const submitBtn = screen.getByText('Screen Article Content');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      // Dynamic evidence assessment rendered (no hardcoded railway text)
      expect(screen.getByText(/Wire republication \/ syndication pattern/i)).toBeDefined();
      expect(screen.getByText(/Independent reporting indexed from 1 distinct coverage/i)).toBeDefined();
      expect(screen.getByText(/Independent editorial cross-verification required/i)).toBeDefined();

      // Syndication vs independent badges
      expect(screen.getByText('Wire Syndication')).toBeDefined();
      expect(screen.getByText('Independent Coverage')).toBeDefined();

      // Model label
      expect(screen.getByText('Insufficient / No Meaningful Model Signal')).toBeDefined();
    });
  });
});
