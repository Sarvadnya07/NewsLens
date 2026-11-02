# NewsLens India — API Contracts Specification

## Base URL
`/api/v1`

## Common Response Wrapper
All successful responses return:
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional feedback message"
}
```

Error responses return `application/problem+json` (RFC 9457) — the legacy
`{success:false,error:{...}}` envelope is retired. Canonical semantics live in
[`../API.md`](../API.md); the machine-readable contract is `docs/openapi.json`:
```json
{
  "type": "urn:newslens:problem:not-found",
  "title": "Resource not found",
  "status": 404,
  "detail": "The requested article does not exist.",
  "instance": "/api/v1/articles/missing",
  "code": "NOT_FOUND",
  "request_id": "9f2c1d7e5b8a4c30"
}
```

## Route Index

### 1. Health
- `GET /health` — API liveness check.
- `GET /health/ready` — Verifies database connection, ML model artifact readiness, and fact-check index.

### 2. Dashboard
- `GET /dashboard/summary` — Aggregated operational statistics:
  - `total_articles`: int
  - `active_sources_count`: int
  - `coverage_clusters_count`: int
  - `fact_check_matches_count`: int
  - `recent_articles`: Article[]
  - `source_statuses`: SourceStatusItem[]

### 3. Articles
- `GET /articles` — Paginated article ledger with filtering by `query`, `source_type`, `sort_order`, `page`, `page_size`.
- `GET /articles/{article_id}` — Single article record lookup.
- `POST /articles` — Manual user submission of news claim for tracking.

### 4. Analysis
- `POST /analysis` — Runs ML linguistic screening, influential TF-IDF feature extraction, related coverage retrieval, and ClaimReview matching.

### 5. Evidence
- `POST /evidence/search` — BM25Plus ranked claim retrieval over accredited fact-checks.

### 6. Coverage
- `GET /coverage/clusters` — Multi-publisher coverage clustering and syndication classification.
- `GET /coverage/graph` — Cytoscape-compatible node and edge topology.

### 7. Ingestion
- `GET /ingestion/status` — Synchronization state and feed latencies.
- `POST /ingestion/refresh` — Triggers synchronous RSS feed poll and SQLite upsert.

### 8. Methodology
- `GET /methodology` — Institutional specification, dataset breakdown, evaluation metrics, and system limitations.

### 9. Integrations
- `GET /integrations` — Provider registry overview with status/telemetry per provider.
- `GET /integrations/status` — Provider status list.
- `GET /integrations/{provider_id}` — Single provider status and quota telemetry.
- `GET /integrations/{provider_id}/quota` — NewsLens request-budget telemetry (`quota_supported` marks unsupported providers).
- `POST /integrations/{provider_id}/test` — Bounded connectivity test; admin-authorized, no ingestion side effects.
- `POST /integrations/{provider_id}/refresh` — On-demand ingestion; admin-authorized.
