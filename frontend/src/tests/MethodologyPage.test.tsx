import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MethodologyPage } from '../pages/MethodologyPage';
import { newsApi } from '../services/api';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

describe('MethodologyPage', () => {
  it('renders pipeline stages, model metrics, and ethical principles from API', async () => {
    vi.spyOn(newsApi, 'getMethodology').mockResolvedValueOnce({
      version: 'Standard Specification 1.4-R',
      status: 'Peer-Review Draft',
      pipeline_stages: [
        {
          stage_id: 'stage_1',
          title: '1. Ingestion Engine',
          description: 'Continuous GDELT & RSS querying.',
          badge: 'STAGE 01',
          icon: 'Radio',
          details: 'Latency Target: < 2500ms',
        },
      ],
      performance_metrics: [
        {
          metric: 'Macro F1-Score',
          evaluation_score: '0.639',
          baseline_random: '0.500',
          validation_set_description: 'Harmonic mean across balanced folds.',
        },
      ],
      dataset_split: {
        total_articles: 4200,
        segments: [{ label: 'National Press', percentage: 65, count: 2730 }],
        sampling_interval: 'Q1 2022 - Q4 2024',
      },
      limitations: [
        {
          id: 'lim_1',
          title: 'No Automated Truth Claims',
          description: 'Statistical models do not determine judicial truth.',
          policy: 'Non-Arbitration Policy',
          policy_badge: 'warning',
        },
      ],
      architecture_stack: {
        Frontend: 'React + TypeScript',
      },
    });

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <MethodologyPage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Methodology & Data Sources')).toBeDefined();
      expect(screen.getByText('1. Ingestion Engine')).toBeDefined();
      expect(screen.getByText('Macro F1-Score')).toBeDefined();
      expect(screen.getByText('No Automated Truth Claims')).toBeDefined();
    });
  });
});
