import axios from 'axios';
import type {
  APIResponse,
  PaginatedResponse,
  Article,
  DashboardSummary,
  AnalysisResponse,
  EvidenceSearchResponse,
  CoverageGraphResponse,
  MethodologyResponse,
} from '../types/api';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 20000,
});

export const newsApi = {
  // Health
  getHealth: async () => {
    const res = await api.get<APIResponse<any>>('/health/ready');
    return res.data.data;
  },

  // Dashboard
  getDashboardSummary: async () => {
    const res = await api.get<APIResponse<DashboardSummary>>('/dashboard/summary');
    return res.data.data;
  },

  // Articles
  getArticles: async (params?: {
    query?: string;
    source_type?: string;
    sort_order?: string;
    page?: number;
    page_size?: number;
  }) => {
    const res = await api.get<APIResponse<PaginatedResponse<Article>>>('/articles', { params });
    return res.data.data;
  },

  getArticleDetail: async (id: string) => {
    const res = await api.get<APIResponse<Article>>(`/articles/${id}`);
    return res.data.data;
  },

  submitManualArticle: async (payload: { title: string; publisher?: string; summary?: string; url?: string }) => {
    const res = await api.post<APIResponse<Article>>('/articles', payload);
    return res.data.data;
  },

  // Analysis
  analyzeArticle: async (payload: { text: string; title?: string }) => {
    const res = await api.post<APIResponse<AnalysisResponse>>('/analysis', payload);
    return res.data.data;
  },

  // Evidence
  searchEvidence: async (payload: { query: string; top_k?: number }) => {
    const res = await api.post<APIResponse<EvidenceSearchResponse>>('/evidence/search', payload);
    return res.data.data;
  },

  // Coverage
  getCoverageClusters: async (limit: number = 30) => {
    const res = await api.get<APIResponse<any[]>>('/coverage/clusters', { params: { limit } });
    return res.data.data;
  },

  getCoverageGraph: async (limit: number = 40) => {
    const res = await api.get<APIResponse<CoverageGraphResponse>>('/coverage/graph', { params: { limit } });
    return res.data.data;
  },

  // Ingestion
  triggerRefresh: async () => {
    const res = await api.post<APIResponse<any>>('/ingestion/refresh');
    return res.data.data;
  },

  getIngestionStatus: async () => {
    const res = await api.get<APIResponse<any>>('/ingestion/status');
    return res.data.data;
  },

  // Methodology
  getMethodology: async () => {
    const res = await api.get<APIResponse<MethodologyResponse>>('/methodology');
    return res.data.data;
  },
};
