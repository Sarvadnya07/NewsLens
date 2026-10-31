import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { NewsMonitorPage } from './pages/NewsMonitorPage';
import { AnalyzeArticlePage } from './pages/AnalyzeArticlePage';
import { EvidenceCoveragePage } from './pages/EvidenceCoveragePage';
import { MethodologyPage } from './pages/MethodologyPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60 * 2, // 2 minutes
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="news" element={<NewsMonitorPage />} />
            <Route path="analyze" element={<AnalyzeArticlePage />} />
            <Route path="evidence" element={<EvidenceCoveragePage />} />
            <Route path="methodology" element={<MethodologyPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
