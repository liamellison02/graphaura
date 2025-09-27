# GraphAura Backend

Multi-modal knowledge graph backend integrating R2R and Neo4j.

## Features

- 📄 **Document Processing**: Upload and process documents through R2R
- 🔍 **Hybrid Search**: Combined vector, keyword, and graph search
- 🕸️ **Knowledge Graph**: Neo4j-powered entity and relationship management
- 🎯 **Vector Similarity**: PGVector-based semantic search
- 🚀 **Async API**: Full async/await support with FastAPI
- 📊 **Entity Extraction**: Automatic entity and relationship extraction

## Tech Stack

- **Python 3.13** with uv package manager
- **FastAPI** for async REST API
- **R2R** for RAG and document processing
- **Neo4j** for graph database
- **PostgreSQL** with pgvector for embeddings
- **AsyncPG** for async PostgreSQL operations

## Installation

### Prerequisites

- Python 3.13+
- PostgreSQL with pgvector extension
- Neo4j 5.x
- R2R running locally (port 7272)

### Setup

1. Install dependencies with uv:
```bash
cd backend
uv sync
```

2. Set up environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Initialize databases:
```bash
# PostgreSQL
createdb graphaura
psql -d graphaura -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Neo4j - ensure it's running
```

4. Run the server:
```bash
uv run uvicorn src.main:app --reload
```

## API Endpoints

### Documents
- `POST /api/v1/documents/upload` - Upload and process documents
- `GET /api/v1/documents/{id}` - Get document details
- `DELETE /api/v1/documents/{id}` - Delete document
- `POST /api/v1/documents/batch/upload` - Batch upload documents
- `GET /api/v1/documents/{id}/entities` - Get extracted entities
- `POST /api/v1/documents/create-graph` - Create graph from documents

### Graph
- `POST /api/v1/graph/entities` - Create entity
- `GET /api/v1/graph/entities/{id}` - Get entity
- `PUT /api/v1/graph/entities/{id}` - Update entity
- `DELETE /api/v1/graph/entities/{id}` - Delete entity
- `POST /api/v1/graph/relationships` - Create relationship
- `POST /api/v1/graph/search/entities` - Search entities
- `POST /api/v1/graph/search/similar` - Find similar entities
- `POST /api/v1/graph/traverse` - Traverse graph
- `GET /api/v1/graph/entities/{id}/relationships` - Get entity relationships
- `POST /api/v1/graph/visualize` - Get visualization data
- `POST /api/v1/graph/cypher` - Execute Cypher query

### Search
- `POST /api/v1/search/documents` - Search documents
- `POST /api/v1/search/rag` - RAG search with context
- `POST /api/v1/search/hybrid` - Hybrid search across sources
- `POST /api/v1/search/semantic` - Semantic similarity search
- `POST /api/v1/search/contextual` - Contextual search with graph
- `GET /api/v1/search/suggestions` - Get search suggestions
- `GET /api/v1/search/clusters` - Get entity clusters

### System
- `GET /health` - Health check
- `GET /metrics` - Application metrics
- `GET /docs` - OpenAPI documentation
- `GET /redoc` - ReDoc documentation

## Project Structure

```
backend/
├── pyproject.toml          # Project dependencies
├── src/
│   ├── __init__.py
│   ├── main.py             # FastAPI application
│   ├── config.py           # Configuration settings
│   ├── models/             # Data models
│   │   ├── entities.py     # Entity models
│   │   └── relationships.py # Relationship models
│   ├── services/           # Service layer
│   │   ├── r2r_service.py  # R2R integration
│   │   ├── neo4j_service.py # Neo4j operations
│   │   └── vector_service.py # Vector operations
│   ├── api/                # API routes
│   │   └── routes/
│   │       ├── documents.py # Document endpoints
│   │       ├── graph.py     # Graph endpoints
│   │       └── search.py    # Search endpoints
│   └── database/           # Database connections
│       ├── postgres.py     # PostgreSQL manager
│       └── neo4j.py        # Neo4j manager
```

## Development

### Run with hot reload:
```bash
uv run uvicorn src.main:app --reload --port 8000
```

### Run tests:
```bash
uv run pytest
```

### Format code:
```bash
uv run black src/
uv run ruff check --fix src/
```

### Type checking:
```bash
uv run mypy src/
```

## Configuration

All configuration is done through environment variables. See `.env.example` for available options.

Key configurations:
- `VECTOR_DIMENSION`: Embedding dimension (must match R2R config)
- `MAX_GRAPH_DEPTH`: Maximum graph traversal depth
- `SIMILARITY_THRESHOLD`: Default similarity threshold for vector search

## Docker Support

```bash
docker build -t graphaura-backend .
docker run -p 8000:8000 --env-file .env graphaura-backend
```

## License

MIT