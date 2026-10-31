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

Error responses return:
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": null
  }
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
