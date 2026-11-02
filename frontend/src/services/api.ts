import axios, { AxiosError } from 'axios';
import type {
  APIResponse,
  PaginatedResponse,
  Article,
  DashboardSummary,
  AnalysisResponse,
  EvidenceSearchResponse,
  CoverageGraphResponse,
  MethodologyResponse,
  IngestionRefreshParams,
  IngestionRefreshResponse,
  ProblemDetails,
  ProblemFieldError,
} from '../types/api';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 20000,
});

/**
 * The API answers every failure with RFC 9457 Problem Details
 * (`application/problem+json`). Parsing lives here so components never
 * interpret error payloads themselves.
 */
export function parseProblem(payload: unknown): ProblemDetails | null {
  if (!payload || typeof payload !== 'object') return null;
  const candidate = payload as Partial<ProblemDetails>;
  if (typeof candidate.type !== 'string' || typeof candidate.code !== 'string') {
    const legacyDetail = (payload as { detail?: unknown }).detail;
    if (typeof legacyDetail === 'string') {
      return {
        type: 'urn:newslens:problem:unknown',
        title: 'Request failed',
        status: 0,
        detail: legacyDetail,
        code: 'UNKNOWN_ERROR',
      };
    }
    return null;
  }
  return candidate as ProblemDetails;
}

export function getProblem(error: unknown): ProblemDetails | null {
  const axiosError = error as AxiosError & { problem?: ProblemDetails | null };
  if (axiosError?.problem) return axiosError.problem;
  return parseProblem(axiosError?.response?.data);
}

export function getFieldErrors(error: unknown): ProblemFieldError[] {
  return getProblem(error)?.errors ?? [];
}

/** Human readable message safe to render in the UI (never raw internals). */
export function getErrorMessage(error: unknown, fallback = 'Something went wrong.'): string {
  const problem = getProblem(error);
  if (problem) {
    return problem.detail || problem.title || fallback;
  }
  const message = (error as { message?: string })?.message;
  return message && message.length < 300 ? message : fallback;
}

export function getErrorCode(error: unknown): string | null {
  return getProblem(error)?.code ?? null;
}

export function getRequestId(error: unknown): string | null {
  return getProblem(error)?.request_id ?? null;
}

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const problem = parseProblem(error?.response?.data);
    if (problem) {
      (error as AxiosError & { problem?: ProblemDetails }).problem = problem;
    }
    return Promise.reject(error);
  },
);

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
    discovery_profile?: string;
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
  triggerRefresh: async (params?: IngestionRefreshParams) => {
    const res = await api.post<APIResponse<IngestionRefreshResponse>>('/ingestion/refresh', params || {}, {
      timeout: 60000,
    });
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

  // Integrations Management
  getIntegrationsOverview: async () => {
    const res = await api.get<APIResponse<import('../types/api').IntegrationsOverview>>('/integrations');
    return res.data.data;
  },

  testProviderConnection: async (providerId: string) => {
    const res = await api.post<APIResponse<import('../types/api').ConnectionTestResult>>(`/integrations/${providerId}/test`);
    return res.data.data;
  },

  refreshProvider: async (providerId: string, params?: { profile?: string; query?: string; max_pages?: number }) => {
    const res = await api.post<APIResponse<import('../types/api').IntegrationRefreshResult>>(`/integrations/${providerId}/refresh`, params || {}, {
      timeout: 60000,
    });
    return res.data.data;
  },
};

export default api;
