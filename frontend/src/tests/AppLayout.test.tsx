import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from '../components/layout/AppLayout';

const testQueryClient = new QueryClient();

describe('AppLayout Navigation', () => {
  it('renders brand identity and investigation desk navigation items', () => {
    render(
      <QueryClientProvider client={testQueryClient}>
        <BrowserRouter>
          <AppLayout />
        </BrowserRouter>
      </QueryClientProvider>
    );

    expect(screen.getByText('NewsLens India')).toBeDefined();
    expect(screen.getByText('Overview')).toBeDefined();
    expect(screen.getByText('News Monitor')).toBeDefined();
    expect(screen.getByText('Analyze Article')).toBeDefined();
    expect(screen.getByText('Evidence & Coverage')).toBeDefined();
    expect(screen.getByText('Methodology')).toBeDefined();
    expect(screen.getByText('LIVE DATASTORE')).toBeDefined();
  });
});
