export interface APIResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

/** RFC 9457 Problem Details field-level failure. */
export interface ProblemFieldError {
  field: string;
  message: string;
  code?: string | null;
}

/** RFC 9457 Problem Details body returned for every API error. */
export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail?: string | null;
  instance?: string | null;
  code: string;
  request_id?: string | null;
  errors?: ProblemFieldError[] | null;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  pagination: PaginationMeta;
}

export interface Article {
  id: string;
  title: string;
  url: string;
  publisher: string;
  published_at: string;
  ingested_at: string;
  source_type: string;
  summary: string;
  language?: string;
  country?: string;
  query?: string;
  discovery_profile?: string;
  image_url?: string | null;
}

export interface IngestionQuotaTelemetry {
  provider_id: string;
  daily_requests_used: number;
  daily_requests_budget: number;
  rolling_15m_used: number;
  rolling_15m_budget: number;
  is_exhausted: boolean;
  last_request_at?: string | null;
  last_outcome?: string | null;
}

export interface IngestionRefreshParams {
  source_type?: string;
  profile?: string;
  max_pages?: number;
}

export interface IngestionRefreshResponse {
  success: boolean;
  total_fetched: number;
  new_stored: number;
  duration_ms: number;
  all_succeeded: boolean;
  all_failed: boolean;
  summary: Record<string, string>;
  discovery_profile?: string | null;
  quota_telemetry?: IngestionQuotaTelemetry | null;
}

export interface SourceStatusItem {
  source_name: string;
  source_type: string;
  last_status: string;
  items_fetched: number;
  last_fetched_at: string | null;
  error_message: string | null;
}

export interface DashboardSummary {
  total_articles: number;
  active_sources_count: number;
  total_configured_sources: number;
  coverage_clusters_count: number;
  fact_check_matches_count: number;
  recent_articles: Article[];
  top_stories_limit?: number;
  top_stories_count?: number;
  source_statuses: SourceStatusItem[];
  sources_distribution: Record<string, number>;
  publishers_distribution: Record<string, number>;
}

export interface InfluentialToken {
  token: string;
  weight: string;
}

export interface MLScreeningResult {
  label: string;
  confidence: number;
  score: number;
  is_uncertain: boolean;
  explanation: string;
  decision_threshold: number;
  influential_tokens: InfluentialToken[];
}

export interface RelatedCoverageItem {
  title: string;
  publisher: string;
  url: string;
  published_at?: string | null;
  similarity: number;
  relationship: string;
  is_syndication: boolean;
}

export interface EvidenceAssessment {
  available_evidence: string[];
  missing_evidence: string[];
  analytical_recommendations: string;
}

export interface AnalysisResponse {
  input_text: string;
  screening: MLScreeningResult;
  related_coverage: RelatedCoverageItem[];
  fact_check_matches: any[];
  evidence_assessment?: EvidenceAssessment;
  analysis_timestamp: string;
}

export interface FactCheckItem {
  claim_id: string;
  claim: string;
  verdict: string;
  claimant: string;
  fact_checker: string;
  review_date: string;
  source_url: string;
  explanation: string;
  similarity_score?: number;
}

export interface EvidenceSearchResponse {
  query: string;
  matches: FactCheckItem[];
  total_matches: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'article' | 'publisher';
  cluster_id?: string;
  data: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship: string;
  weight: number;
}

export interface CoverageGraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  cluster_count: number;
  article_count: number;
  publisher_count: number;
}

export interface PipelineStage {
  stage_id: string;
  title: string;
  description: string;
  badge: string;
  icon: string;
  details: string;
}

export interface MetricEvaluation {
  metric: string;
  evaluation_score: string;
  baseline_random: string;
  validation_set_description: string;
}

export interface SystemLimitation {
  id: string;
  title: string;
  description: string;
  policy: string;
  policy_badge: string;
}

export interface MethodologyResponse {
  version: string;
  status: string;
  pipeline_stages: PipelineStage[];
  performance_metrics: MetricEvaluation[];
  dataset_split: {
    total_articles: number;
    segments: Array<{ label: string; percentage: number; count: number }>;
    sampling_interval: string;
  };
  limitations: SystemLimitation[];
  architecture_stack: Record<string, string>;
}

export interface ProviderStatusItem {
  id: string;
  name: string;
  category: string;
  source_type: string;
  domain: string;
  is_active: boolean;
  requires_api_key: boolean;
  env_key_name?: string | null;
  is_configured: boolean;
  is_enabled: boolean;
  status_label:
    | 'operational'
    | 'degraded'
    | 'configured_not_tested'
    | 'not_configured'
    | 'disabled'
    | 'rate_limited'
    | 'provider_error'
    | 'retired'
    | 'backlog';
  last_refresh_at?: string | null;
  last_attempt_at?: string | null;
  last_attempt_status?: string | null;
  last_http_status?: number | null;
  last_latency_ms?: number | null;
  items_count: number;
  new_items_inserted: number;
  error_message?: string | null;
  quota?: ProviderQuotaTelemetry | null;
  supported_profiles: string[];
  documentation_url?: string | null;
  terms_url?: string | null;
}

/** NewsLens request-budget telemetry (internal governance, not a provider quota). */
export interface ProviderQuotaTelemetry {
  provider_id: string;
  quota_supported: boolean;
  limit?: number | null;
  used?: number | null;
  remaining?: number | null;
  window: string;
  reset_at?: string | null;
  unit: string;
  source: string;
  rolling_15m_used?: number | null;
  rolling_15m_limit?: number | null;
  is_exhausted?: boolean | null;
  last_request_at?: string | null;
  last_outcome?: string | null;
  last_updated_at?: string | null;
}

export interface IntegrationsOverview {
  total_registered: number;
  configured_count: number;
  operational_count: number;
  disabled_count: number;
  awaiting_credentials_count: number;
  providers: ProviderStatusItem[];
}

/** Canonical connection-test outcome; identical for every provider. */
export interface ConnectionTestResult {
  provider_id: string;
  status:
    | 'connected'
    | 'not_configured'
    | 'not_implemented'
    | 'auth_failed'
    | 'rate_limited'
    | 'timeout'
    | 'unavailable'
    | 'invalid_response'
    | 'error';
  connected: boolean;
  configured: boolean;
  implemented: boolean;
  success: boolean;
  message: string;
  checked_at: string;
  http_status?: number | null;
  latency_ms?: number | null;
  error?: string | null;
  request_id?: string | null;
}

export interface IntegrationRefreshResult {
  provider_id: string;
  profile?: string | null;
  success: boolean;
  status: string;
  items_fetched: number;
  new_stored: number;
  duration_ms: number;
  error_message?: string | null;
}
