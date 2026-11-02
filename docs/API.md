# NewsLens India — API Reference & Contract

**Base path:** `/api/v1` · **Current version:** `1.0.0` · **Consumer:** React SPA (single trust domain)

The machine-readable contract is **`docs/openapi.json`**, generated from the running
FastAPI application. This document explains the semantics that OpenAPI cannot
express. When the two disagree, the generated artifact and the runtime behaviour
win — and `python scripts/export_openapi.py --check` fails CI until they are
reconciled.

```powershell
python scripts/export_openapi.py            # regenerate docs/openapi.json
python scripts/export_openapi.py --check    # fail if the committed artifact is stale
python scripts/check_frontend_contract.py   # frontend transport types vs contract
python scripts/check_doc_routes.py          # this document vs the contract
```

---

## 1. Route index

| Method | Endpoint | Class | Description |
|---|---|---|---|
| `GET` | `/api/v1/health` | Public | Liveness probe. |
| `GET` | `/api/v1/health/ready` | Public | Readiness probe (database, model, fact-check index). |
| `GET` | `/api/v1/dashboard/summary` | Public | Aggregate counts, distributions, and at most 10 recent stories. |
| `GET` | `/api/v1/articles` | Public | Paginated article ledger with query/source/sort filters. |
| `POST` | `/api/v1/articles` | Public | Manual article submission (content-addressed, retry-safe). |
| `GET` | `/api/v1/articles/{article_id}` | Public | Single article record. |
| `POST` | `/api/v1/analysis` | Public | ML linguistic screening, coverage, and fact-check matching. |
| `POST` | `/api/v1/evidence/search` | Public | BM25Plus retrieval over curated fact-checks. |
| `GET` | `/api/v1/coverage/clusters` | Public | Multi-publisher story clustering. |
| `GET` | `/api/v1/coverage/graph` | Public | Cytoscape-compatible node/edge topology. |
| `GET` | `/api/v1/ingestion/status` | Public | Ingestion status and provider telemetry. |
| `POST` | `/api/v1/ingestion/refresh` | Administrative¹ | Triggers live ingestion. |
| `GET` | `/api/v1/integrations` | Public | Provider registry with truthful maturity states. |
| `GET` | `/api/v1/integrations/status` | Public | Provider status list. |
| `GET` | `/api/v1/integrations/{provider_id}` | Public | One provider's status and quota telemetry. |
| `GET` | `/api/v1/integrations/{provider_id}/quota` | Public | Request-budget telemetry. |
| `POST` | `/api/v1/integrations/{provider_id}/test` | Administrative | Bounded connectivity test (no ingestion). |
| `POST` | `/api/v1/integrations/{provider_id}/refresh` | Administrative | On-demand provider ingestion. |
| `GET` | `/api/v1/methodology` | Public | Model, dataset, and evaluation documentation. |

¹ Gated only when `REQUIRE_ADMIN_AUTH_FOR_INGESTION=true`; see §3.

Unauthenticated `POST` operations here are read-only computations over server-side
data (`/analysis`, `/evidence/search`) or content-addressed upserts (`/articles`);
none of them mutate privileged configuration.

## 2. Success envelope

Every successful response uses the same envelope:

```json
{ "success": true, "data": { }, "message": "Optional human-readable note" }
```

## 3. Errors — RFC 9457 Problem Details

Every failure — framework, validation, application, provider, database, or
unexpected — returns `Content-Type: application/problem+json`:

```json
{
  "type": "urn:newslens:problem:validation-error",
  "title": "Request validation failed",
  "status": 422,
  "detail": "One or more request fields are invalid.",
  "instance": "/api/v1/analysis",
  "code": "VALIDATION_ERROR",
  "request_id": "9f2c1d7e5b8a4c30",
  "errors": [{ "field": "body.text", "message": "String should have at least 10 characters", "code": "string_too_short" }]
}
```

Guarantees:

* `type` is never null and always starts with `urn:newslens:problem:`.
* `code` is stable across releases; clients branch on it, not on `detail`.
* `request_id` matches the `X-Request-ID` response header.
* `instance` is the request path and never includes query parameters.
* Submitted values, credentials, stack traces, and raw provider payloads are
  never echoed back.
* `errors[]` appears only for validation failures.

### 3.1 Error taxonomy

| `code` | HTTP | `type` suffix |
|---|---:|---|
| `VALIDATION_ERROR` | 422 | `validation-error` |
| `BAD_REQUEST` | 400 | `bad-request` |
| `UNAUTHORIZED` | 401 | `unauthorized` |
| `FORBIDDEN` | 403 | `forbidden` |
| `NOT_FOUND` | 404 | `not-found` |
| `ARTICLE_NOT_FOUND` | 404 | `not-found` |
| `PROVIDER_NOT_FOUND` | 404 | `not-found` |
| `CONFLICT` | 409 | `conflict` |
| `UNPROCESSABLE_ENTITY` | 422 | `unprocessable-entity` |
| `RATE_LIMITED` | 429 | `rate-limited` |
| `PROVIDER_QUOTA_EXCEEDED` | 429 | `provider-quota-exceeded` |
| `PROVIDER_NOT_CONFIGURED` | 503 | `provider-not-configured` |
| `PROVIDER_AUTH_FAILED` | 502 | `provider-auth-failed` |
| `PROVIDER_TIMEOUT` | 504 | `provider-timeout` |
| `PROVIDER_UNAVAILABLE` | 502 | `provider-unavailable` |
| `PROVIDER_NOT_IMPLEMENTED` | 501 | `provider-not-implemented` |
| `DATABASE_ERROR` | 500 | `database-error` |
| `INTERNAL_ERROR` | 500 | `internal-error` |
| `SERVICE_UNAVAILABLE` | 503 | `service-unavailable` |

Retry semantics: `429` carries `Retry-After`; `502`/`503`/`504` are provider or
platform transients; `4xx` are caller errors and must not be retried unchanged.

## 4. Request correlation

* A request id is generated for every request and always returned in `X-Request-ID`.
* A well-formed inbound id (8–64 characters of `[A-Za-z0-9._:-]`) is reused so a
  reverse proxy can trace end-to-end; anything malformed is replaced with a
  generated 32-character hex id.
* The id appears in structured access logs (`status`, `duration_ms`, route
  template), in error logs, and in every problem body.
* Client-supplied ids are never trusted as identity — only as a trace label.

## 5. Authentication and authorization

There is exactly **one** policy, implemented in `backend/main.py` and shared by
every privileged route. It is never re-implemented per router.

**Production** (`APP_ENV=production`, or any unrecognised `APP_ENV`, which fails
closed):

* `ADMIN_API_KEY` must be configured; otherwise administrative requests return
  `503 SERVICE_UNAVAILABLE` and startup rejects the configuration when
  enforcement is enabled.
* `X-Admin-Key` must match, compared in constant time. Missing/blank/wrong →
  `401 UNAUTHORIZED` with `WWW-Authenticate: ApiKey`.
* No loopback or forwarding-header bypass exists.

**Development / test** (`APP_ENV=development|test|staging`):

* Unauthenticated administrative calls are allowed **only** when the transport
  peer is loopback (`127.0.0.1`, `::1`, `localhost`) or the in-process test
  client, **and** `ALLOW_UNAUTHENTICATED_ADMIN_IN_DEV=true` (default),
  **and** `REQUIRE_ADMIN_AUTH_IN_DEV=false` (default).
* `X-Forwarded-For` and similar headers are ignored, so a remote caller cannot
  spoof locality. Remote callers always need `X-Admin-Key`.
* `REQUIRE_ADMIN_AUTH_IN_DEV=true` removes the bypass during development.

**Ingestion trigger:** `POST /ingestion/refresh` is additionally controlled by
`REQUIRE_ADMIN_AUTH_FOR_INGESTION` (default `false`) so local development keeps
working; when enabled it applies the same policy above and adds rate limiting.
Provider `test`/`refresh` are **always** gated by the policy and always
rate-limited, because they spend upstream quota.

**Startup validation** rejects: an unknown `APP_ENV`, an `ADMIN_API_KEY` shorter
than 16 characters, and `REQUIRE_ADMIN_AUTH_FOR_INGESTION=true` without a key.

Secrets never appear in responses or logs: only presence (`[Configured]`) and
redacted fragments are logged.

## 6. Rate limiting

Application rate limiting is deliberately separate from provider quota budgets.

| Scope | Default | Applies |
|---|---|---|
| `integrations:test` | 30 requests/minute per client | Always |
| `integrations:refresh` | 30 requests/minute per client | Always |
| `ingestion:refresh` | 30 requests/minute per client | Only when administrative enforcement is enabled |

Configure with `ADMIN_RATE_LIMIT_PER_MINUTE`. Exceeding a limit returns
`429 RATE_LIMITED` with `Retry-After`.

**Known limitation:** the limiter is an in-process sliding window with bounded
memory. A multi-worker or multi-instance deployment would enforce per process,
not globally. NewsLens runs as a single local instance, so no shared store
(Redis et al.) is introduced. If it is ever deployed multi-instance, enforce
limits at the reverse proxy or move the limiter to a shared backend.

## 7. Pagination

`GET /api/v1/articles` uses offset pagination:

| Parameter | Default | Bounds |
|---|---|---|
| `page` | 1 | 1–100,000 |
| `page_size` | 20 | 1–100 |
| `sort_order` | `Recency` | `Recency`, `Oldest`, `Chronological` |

* Ordering is deterministic: `published_at <dir>, id ASC`. The `id` tie-breaker
  guarantees stable paging when timestamps collide or are null.
* Out-of-range values return `422 VALIDATION_ERROR` (never a silent clamp).
* `page` is capped at 100,000 so offsets stay representable; a larger value is a
  validation error, never a 500.
* Deep pages return `items: []` with accurate `total_items`/`total_pages`.
* Response shape: `data: { items: [...], pagination: { page, page_size, total_items, total_pages } }`.
* `GET /api/v1/dashboard/summary` is capped at **10 unique articles** in
  `recent_articles`, enforced server-side; `top_stories_limit` and
  `top_stories_count` make the cap explicit.

**Not implemented (accepted trade-off):** cursor/keyset pagination. Inserts
between page fetches can shift an offset window. For a single-user research
ledger this is acceptable; the deterministic tie-breaker prevents duplicates
caused by equal timestamps, which was the real defect.

## 8. Idempotency

`POST /api/v1/articles` is content-addressed:

* Identity is the canonicalized `url`; when absent, a hash of the normalized title.
* Repeating an identical submission returns the existing record (HTTP `201`) and
  creates no duplicate row.
* A submission that resolves to an existing article updates nothing privileged
  and never overwrites publisher provenance.

**Not implemented (accepted trade-off):** an `Idempotency-Key` header and stored
response replay. The operation is a single upsert with no external side effects,
so content addressing already provides the retry safety the header would add.

**Bulk creation is unsupported.** There is no bulk endpoint.

## 9. Provider and integration semantics

### 9.1 Status states (`ProviderStatusItem.status_label`)

| State | Meaning |
|---|---|
| `operational` | A successful attempt was recorded within the staleness window. |
| `degraded` | The last recorded attempt succeeded but is older than the window (`PROVIDER_STATUS_STALENESS_HOURS`, default 24). |
| `configured_not_tested` | Configuration/credentials exist, no successful attempt recorded. |
| `not_configured` | Required credentials are absent. |
| `disabled` | Explicitly disabled in configuration. |
| `rate_limited` | Last attempt rejected by an upstream quota. |
| `provider_error` | Last attempt failed (timeout, 5xx, invalid payload). |
| `backlog` | Registered for planning; no active adapter. Never reported operational. |
| `retired` | Withdrawn; excluded from normal ingestion. |

A configured key is **not** connectivity, a registry entry is **not** an adapter,
and a historical success does not stay operational forever.

### 9.2 Connection test — `POST /integrations/{provider_id}/test`

Bounded, quota-aware, and side-effect free: no articles are inserted. Every
provider answers with the same shape:

```json
{
  "provider_id": "newsdata_io",
  "status": "connected",
  "connected": true,
  "configured": true,
  "implemented": true,
  "success": true,
  "message": "NewsData.io connection test completed.",
  "checked_at": "2026-11-01T09:15:00+00:00",
  "http_status": 200,
  "latency_ms": 240.4,
  "error": null,
  "request_id": "9f2c1d7e5b8a4c30"
}
```

`status` is one of `connected`, `not_configured`, `not_implemented`,
`auth_failed`, `rate_limited`, `timeout`, `unavailable`, `invalid_response`,
`error`. `connected` is true only for `connected`; `success` mirrors it for
legacy consumers. `http_status`/`latency_ms` are null when no call was made —
they are never invented. Unknown providers return `404 PROVIDER_NOT_FOUND`.

### 9.3 Refresh — `POST /integrations/{provider_id}/refresh`

Performs real ingestion. `status` uses the ingestion vocabulary (`success`,
`no_results`, `disabled`, `rate_limited`, `provider_unavailable`, `timeout`,
`invalid_response`, `not_implemented`); `items_fetched`, `new_stored`, and
`duration_ms` describe the outcome. Unknown providers return `404 PROVIDER_NOT_FOUND`.

A refresh already running for the same provider or scope is rejected with
`409 CONFLICT` instead of being queued, so a burst of clients cannot stack provider
fan-outs. The refresh runs inside the request, so a slow upstream still occupies that
request until it returns or its per-call timeout expires.

### 9.4 Quota — `GET /integrations/{provider_id}/quota`

These are **NewsLens request budgets**, not provider-reported subscription
quotas (`source: "newslens_request_budget"`):

```json
{
  "provider_id": "newsdata_io",
  "quota_supported": true,
  "limit": 50,
  "used": 12,
  "remaining": 38,
  "window": "daily",
  "reset_at": null,
  "unit": "requests",
  "source": "newslens_request_budget",
  "rolling_15m_used": 2,
  "rolling_15m_limit": 10,
  "is_exhausted": false,
  "last_request_at": "2026-11-01T08:40:00+00:00",
  "last_outcome": "success",
  "last_updated_at": "2026-11-01T09:15:00+00:00"
}
```

Providers without a managed budget return `quota_supported: false` with null
measurements. `reset_at` is null because the upstream does not report one.

## 10. Compatibility policy

* The namespace is `/api/v1/`. There is no `/api/v2`; none is planned.
* Within v1, changes are **additive**: new optional fields, new endpoints, new
  error codes. Removing a field, narrowing a type, renaming a field, or changing
  a status code for the same failure is breaking and requires a migration plan
  plus a regenerated contract, TypeScript types, and docs.
* Error `code` values and problem `type` URNs are part of the contract and are
  never renamed.
* Deprecated fields, if any are ever introduced, are marked `deprecated: true` in
  OpenAPI and listed here with a removal target before removal.

## 11. Verification

| Gate | Command |
|---|---|
| Contract artifact current | `python scripts/export_openapi.py --check` |
| Frontend types match contract | `python scripts/check_frontend_contract.py` |
| Docs match implemented routes | `python scripts/check_doc_routes.py` |
| Contract/security/error tests | `python -m pytest tests/test_api_contract.py -q` |
| Full suite | `python -m pytest -q` |
| Lint/format/SAST | `ruff check . && ruff format --check . && bandit -r src backend scripts -ll` |

**Verification honesty:** CI exercises providers with mocks only. No workflow
makes live upstream calls, so a green CI run proves contract behaviour, not
upstream reachability. Live checks are manual (`scripts/verify_newsdata_live.py`)
and require real credentials.

## 12. Remaining limitations

| Area | Limitation | Status |
|---|---|---|
| Rate limiting | Per-process sliding window; not shared across workers. | Documented |
| Concurrency | Refresh single-flight is per process; a provider fan-out has no
overall request deadline. | Documented |
| Pagination | Offset-based; concurrent inserts can shift a window. | Accepted |
| Pagination | No cursor/keyset mode. | Accepted |
| Idempotency | No `Idempotency-Key` header or response replay. | Accepted |
| Bulk API | Article bulk creation unsupported. | Accepted |
| Provider quota | Internal request budgets only; upstream subscription quotas are not read. | Accepted |
| Provider verification | Mock-verified in CI; live verification is manual. | Documented |
| Authz model | Single shared admin key; no per-user accounts or OAuth. | Accepted (single-consumer app) |
