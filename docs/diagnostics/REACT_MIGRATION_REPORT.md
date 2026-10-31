# NewsLens India — Frontend Architecture & Migration Report

## Executive Summary
The presentation tier of NewsLens India was completely migrated from Streamlit to a modular React 19 + TypeScript application powered by Vite, Tailwind CSS v4, Lucide React, and TanStack Query v5.

## Design System Tokens
- **Midnight Navy:** `#142B4A` (Sidebar background, deep branding)
- **Deep Navy:** `#183B56` (Headings, primary buttons, accents)
- **Royal Blue:** `#315FE8` (Primary brand accent, interactive elements)
- **Deep Teal:** `#087F83` (Ingestion statuses, source badges)
- **Main Surface:** `#F4F6FB` (Application canvas)
- **Typography:**
  - `Newsreader`: High-editorial serifs for page titles and article headlines.
  - `Inter`: UI chrome, tabular telemetry, and form controls.

## Page Implementation & Feature Parity

| Route | Page | Backend Integration | Parity Status |
| :--- | :--- | :--- | :--- |
| `/` | **Overview** | `GET /api/v1/dashboard/summary`<br>`POST /api/v1/analysis` | **COMPLETE** |
| `/news` | **News Monitor** | `GET /api/v1/articles` (query, source, sort, pagination) | **COMPLETE** |
| `/analyze` | **Analyze Article** | `POST /api/v1/analysis` (Linguistic LogReg, TF-IDF tokens, BM25Plus, Coverage) | **COMPLETE** |
| `/evidence` | **Evidence & Coverage** | `GET /api/v1/coverage/clusters`<br>`GET /api/v1/coverage/graph` (Cytoscape.js) | **COMPLETE** |
| `/methodology` | **Methodology** | `GET /api/v1/methodology` (Metrics, Limitations, Dataset split) | **COMPLETE** |

## Verification Run
- **Python Pytest Suite:** 62 tests passing (`tests/test_all.py`, `tests/test_api.py`, `tests/test_backend_phase2.py`, `tests/test_ml_phase4.py`, `tests/test_ui.py`).
- **Frontend Vitest Suite:** 1 test passing.
- **Frontend Vite Production Build:** Succeeded in 706ms (`tsc -b && vite build` clean).
