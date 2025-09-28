# graphaura

bring your memories back to life with graphaura. transform photos and docs into an ai-powered 3d knowledge graph of people, places, and moments to explore your memories and share insights.

<img width="830" height="756" alt="graphaura.dev" src="https://github.com/user-attachments/assets/f6d690be-ae6f-41a0-9fd1-0d0387fb6cb6" />

## repos

- graphaura: this monorepo with frontend and backend
- r2r: external service for ingestion, chunking, embeddings, and RAG

## tech stack

- frontend: next.js, react, tailwind css, react-force-graph-3d
- backend: fastapi (python 3.13), structlog
- data: neo4j, postgresql + pgvector, redis
- ai: r2r for ingestion, NER, embeddings, and RAG

## architecture

```mermaid
graph TB
  u[browser] --> fe[next.js frontend]
  fe -->|rest| be[fastapi backend]
  be -->|http| r2r[r2r service]
  be -->|bolt| neo[(neo4j)]
  be -->|asyncpg + pgvector| pg[(postgres)]
  be -->|redis| redis[(redis)]
  r2r -->|entities + embeddings| be
```

## data flow

```mermaid
flowchart LR
  files[files, photos, notes, pdfs] --> upload[/upload via ui or api/]
  upload --> r2ringest[r2r ingest + chunk + embed + extract]
  r2ringest --> Entities[Entities + Relationships]
  entities --> neo[(neo4j)]
  r2ringest --> embeds[embeddings]
  embeds --> pg[(postgres pgvector)]
  query[user query] --> api[search apis]
  api --> hybrid[hybrid search]
  hybrid --> docs[r2r document search]
  hybrid --> grph[graph traversal]
  grph --> fevis[3d graph ui]
  docs --> fevis
  neo --> api
  pg --> api
```

## monorepo layout

```text
graphaura/
  backend/        fastapi app, services, and apis
  frontend/       next.js app with 3d graph visualization
```

## key endpoints

- `GET /health` - service health
- `GET /metrics` - vector and graph counts
- `POST /api/v1/documents/upload` - upload and process document via r2r
- `GET /api/v1/documents/{id}` - document metadata
- `POST /api/v1/documents/create-graph` - build graph from documents
- `POST /api/v1/graph/entities` - create entity
- `GET /api/v1/graph/entities/{id}` - fetch entity and relationships
- `POST /api/v1/search/hybrid` - hybrid search across documents and graph
