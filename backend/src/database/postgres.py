"""PostgreSQL database connection and management."""

import asyncpg
from typing import Optional, Dict, Any
import structlog

from ..config import settings

logger = structlog.get_logger(__name__)


class PostgresDB:
    """PostgreSQL database connection manager."""

    def __init__(self):
        """Initialize PostgreSQL connection manager."""
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=settings.postgres_host,
                port=settings.postgres_port,
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_db,
                min_size=10,
                max_size=20,
                command_timeout=60,
                statement_cache_size=0  # Required for PgBouncer/Supabase pooler
            )

            await self._init_schema()

            logger.info(
                "Connected to PostgreSQL",
                host=settings.postgres_host,
                database=settings.postgres_db
            )
        except Exception as e:
            logger.error("Failed to connect to PostgreSQL", error=str(e))
            raise

    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Disconnected from PostgreSQL")

    async def _init_schema(self):
        """Initialize database schema."""
        async with self.pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create audit log table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    user_id TEXT,
                    changes JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indices
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_log_entity
                ON audit_log(entity_type, entity_id)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_log_created
                ON audit_log(created_at DESC)
            """)

            logger.info("PostgreSQL schema initialized")

    async def execute(self, query: str, *args):
        """Execute a query."""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetchone(self, query: str, *args):
        """Fetch a single row."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchall(self, query: str, *args):
        """Fetch all rows."""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def log_audit(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        user_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None
    ):
        """Log an audit entry."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO audit_log (entity_type, entity_id, action, user_id, changes)
                VALUES ($1, $2, $3, $4, $5)
            """, entity_type, entity_id, action, user_id, changes or {})