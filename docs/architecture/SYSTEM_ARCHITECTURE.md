# NewsLens India — System Architecture

## 1. Overview & Tier Topology

NewsLens India is an open-source, investigative intelligence platform for near-real-time monitoring of Indian news syndicates and probabilistic screening of linguistic misinformation cues.

```
                           +----------------------------------------+
                           |     React 19 + TypeScript (Vite)       |
                           |  Tailwind CSS v4 • TanStack Query v5   |
                           +-------------------+--------------------+
                                               |
                                     JSON / HTTP REST
                                               |
                           +-------------------v--------------------+
                           |        FastAPI REST API Adapter        |
                           |  Pydantic Schemas • Worker Thread Pool |
                           +-------------------+--------------------+
                                               |
                     +-------------------------+-------------------------+
                     |                         |                         |
           +---------v---------+     +---------v---------+     +---------v---------+
           | NewsLensService   |     | Linguistic ML     |     | Retrieval & Graph |
           | Orchestration     |     | TF-IDF + LogReg   |     | BM25Plus + Cosine |
           +---------+---------+     +-------------------+     +-------------------+
                     |
       +-------------+-------------+
       |                           |
+------v------+             +------v------+
| GDELT v2    |             | RSS Feeds   |
| Doc API     |             | (8 Wires)   |
+-------------+             +-------------+
       |                           |
       +-------------+-------------+
                     |
           +---------v---------+
           | SQLite Datastore  |
           | WAL Mode + Index  |
           +-------------------+
```

## 2. Key Architecture Decisions

1. **Clean Separation of Concerns:**
   - The React frontend handles all presentation, routing, state caching, and responsive rendering.
   - The FastAPI backend orchestrates existing Python intelligence modules without duplicating ML weights or calculations in TypeScript.
2. **Synchronous Worker Offloading:**
   - FastAPI route functions execute synchronous operations in Starlette's threadpool to prevent blocking the event loop.
3. **Multi-Source Evidence Integration:**
   - Probabilistic lexical screening output is always presented side-by-side with external fact-check matches and syndication cluster analyses.
