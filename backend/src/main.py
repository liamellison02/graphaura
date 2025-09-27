"""Main FastAPI application for GraphAura backend."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import uvicorn

from .config import settings
from .database import PostgresDB, Neo4jDB
from .services import Neo4jService, VectorService, R2RService

# Import routers
from .api.routes import documents, graph, search

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global database instances
postgres_db = PostgresDB()
neo4j_db = Neo4jDB()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting GraphAura backend", environment=settings.environment)

    try:
        # Connect to databases
        await postgres_db.connect()
        await neo4j_db.connect()

        # Initialize services
        neo4j_service = Neo4jService()
        await neo4j_service.connect()
        await neo4j_service.create_indices()

        vector_service = VectorService()
        await vector_service.connect()

        r2r_service = R2RService()
        # Store services in app state for access in routes
        app.state.r2r_service = r2r_service
        app.state.neo4j_service = neo4j_service
        app.state.vector_service = vector_service

        logger.info("All services initialized successfully")

    except Exception as e:
        logger.error("Failed to initialize services", error=str(e))
        raise

    yield

    # Shutdown
    logger.info("Shutting down GraphAura backend")

    try:
        await postgres_db.disconnect()
        await neo4j_db.disconnect()
        if hasattr(app.state, 'r2r_service'):
            await app.state.r2r_service.cleanup()
        if hasattr(app.state, 'neo4j_service'):
            await app.state.neo4j_service.disconnect()
        if hasattr(app.state, 'vector_service'):
            await app.state.vector_service.disconnect()
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-modal knowledge graph system integrating R2R and Neo4j",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        method=request.method
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "environment": settings.environment,
        "version": settings.app_version,
        "services": {}
    }

    # Check PostgreSQL
    try:
        await postgres_db.fetchone("SELECT 1")
        health_status["services"]["postgres"] = "healthy"
    except:
        health_status["services"]["postgres"] = "unhealthy"
        health_status["status"] = "degraded"

    # Check Neo4j
    try:
        if neo4j_db.driver:
            await neo4j_db.driver.verify_connectivity()
            health_status["services"]["neo4j"] = "healthy"
        else:
            health_status["services"]["neo4j"] = "disconnected"
            health_status["status"] = "degraded"
    except:
        health_status["services"]["neo4j"] = "unhealthy"
        health_status["status"] = "degraded"

    # Check R2R
    try:
        from .services import R2RService
        async with R2RService() as r2r:
            r2r_healthy = await r2r.health_check()
            health_status["services"]["r2r"] = "healthy" if r2r_healthy else "unhealthy"
            if not r2r_healthy:
                health_status["status"] = "degraded"
    except:
        health_status["services"]["r2r"] = "unhealthy"
        health_status["status"] = "degraded"

    return health_status


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "api_docs": "/docs",
        "api_redoc": "/redoc",
        "health": "/health"
    }


# Register API routers
app.include_router(
    documents.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["documents"]
)

app.include_router(
    graph.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["graph"]
)

app.include_router(
    search.router,
    prefix=f"{settings.api_v1_prefix}",
    tags=["search"]
)


# Metrics endpoint (optional)
@app.get("/metrics")
async def metrics():
    """Get application metrics."""
    try:
        # Get vector statistics
        from .services import VectorService
        async with VectorService() as vector_service:
            vector_stats = await vector_service.get_statistics()

        # Get graph statistics
        from .services import Neo4jService
        async with Neo4jService() as neo4j_service:
            entity_count = await neo4j_service.execute_cypher(
                "MATCH (e:Entity) RETURN count(e) as count"
            )
            relationship_count = await neo4j_service.execute_cypher(
                "MATCH ()-[r]->() RETURN count(r) as count"
            )

        return {
            "vector_embeddings": vector_stats,
            "graph": {
                "entities": entity_count[0]["count"] if entity_count else 0,
                "relationships": relationship_count[0]["count"] if relationship_count else 0
            }
        }
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        return {"error": "Failed to retrieve metrics"}


def run_server():
    """Run the server using uvicorn."""
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers if not settings.debug else 1,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    run_server()