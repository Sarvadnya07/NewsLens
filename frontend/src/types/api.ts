export interface APIResponse<T> {
  success: boolean;
  data: T;
  message?: string;
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

export interface AnalysisResponse {
  input_text: string;
  screening: MLScreeningResult;
  related_coverage: any[];
  fact_check_matches: any[];
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
