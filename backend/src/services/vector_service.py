"""Vector search and similarity service for GraphAura."""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sklearn.metrics.pairwise import cosine_similarity
import structlog
import asyncpg

from ..config import settings
from ..models.entities import Entity

logger = structlog.get_logger(__name__)


class VectorService:
    """Service for vector operations and similarity search."""

    def __init__(self):
        """Initialize vector service."""
        self.dimension = settings.vector_dimension
        self.similarity_threshold = settings.similarity_threshold
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Connect to PostgreSQL with pgvector."""
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

            # Create pgvector extension if not exists
            async with self.pool.acquire() as conn:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                await self._create_tables(conn)

            logger.info("Connected to PostgreSQL with pgvector")
        except Exception as e:
            logger.error("Failed to connect to PostgreSQL", error=str(e))
            raise

    async def disconnect(self):
        """Disconnect from PostgreSQL."""
        if self.pool:
            await self.pool.close()
            logger.info("Disconnected from PostgreSQL")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def _create_tables(self, conn: asyncpg.Connection):
        """Create necessary tables for vector storage."""
        # Use string formatting for CREATE TABLE since parameters aren't supported
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS entity_embeddings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                entity_id TEXT NOT NULL UNIQUE,
                entity_type TEXT NOT NULL,
                embedding vector({self.dimension}) NOT NULL,
                metadata JSONB DEFAULT '{{}}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create index for vector similarity search
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_embeddings_vector
            ON entity_embeddings USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)

        # Create index for entity lookups
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_entity_embeddings_entity_id
            ON entity_embeddings(entity_id)
        """)

    async def store_embedding(
        self,
        entity_id: str,
        entity_type: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store an entity embedding.

        Args:
            entity_id: Entity ID
            entity_type: Type of entity
            embedding: Embedding vector
            metadata: Optional metadata

        Returns:
            Embedding record ID
        """
        if len(embedding) != self.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.dimension}, "
                f"got {len(embedding)}"
            )

        async with self.pool.acquire() as conn:
            # Convert list to pgvector format
            embedding_str = f"[{','.join(map(str, embedding))}]"

            result = await conn.fetchrow("""
                INSERT INTO entity_embeddings (entity_id, entity_type, embedding, metadata)
                VALUES ($1, $2, $3::vector, $4)
                ON CONFLICT (entity_id)
                DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, entity_id, entity_type, embedding_str, metadata or {})

            logger.info("Embedding stored", entity_id=entity_id)
            return str(result["id"])

    async def get_embedding(self, entity_id: str) -> Optional[np.ndarray]:
        """
        Get embedding for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            Embedding vector or None if not found
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT embedding::float[] as embedding
                FROM entity_embeddings
                WHERE entity_id = $1
            """, entity_id)

            if result:
                return np.array(result["embedding"])
            return None

    async def similarity_search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        entity_types: Optional[List[str]] = None,
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar entities based on embedding similarity.

        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            entity_types: Filter by entity types
            threshold: Similarity threshold (default from config)

        Returns:
            List of similar entities with scores
        """
        if len(query_embedding) != self.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.dimension}, "
                f"got {len(query_embedding)}"
            )

        threshold = threshold or self.similarity_threshold
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        async with self.pool.acquire() as conn:
            # Build query with optional entity type filter
            where_clause = ""
            params = [embedding_str, limit]

            if entity_types:
                where_clause = f"AND entity_type = ANY($3)"
                params.append(entity_types)

            query = f"""
                SELECT
                    entity_id,
                    entity_type,
                    metadata,
                    1 - (embedding <=> $1::vector) as similarity
                FROM entity_embeddings
                WHERE 1 - (embedding <=> $1::vector) >= {threshold}
                    {where_clause}
                ORDER BY embedding <=> $1::vector
                LIMIT $2
            """

            results = await conn.fetch(query, *params)

            return [
                {
                    "entity_id": row["entity_id"],
                    "entity_type": row["entity_type"],
                    "metadata": dict(row["metadata"]),
                    "similarity": float(row["similarity"])
                }
                for row in results
            ]

    async def batch_similarity(
        self,
        entity_ids: List[str]
    ) -> np.ndarray:
        """
        Compute pairwise similarity matrix for entities.

        Args:
            entity_ids: List of entity IDs

        Returns:
            Similarity matrix
        """
        async with self.pool.acquire() as conn:
            results = await conn.fetch("""
                SELECT entity_id, embedding::float[] as embedding
                FROM entity_embeddings
                WHERE entity_id = ANY($1)
                ORDER BY array_position($1::text[], entity_id)
            """, entity_ids)

            if not results:
                return np.array([])

            embeddings = np.array([row["embedding"] for row in results])
            return cosine_similarity(embeddings)

    async def find_clusters(
        self,
        min_similarity: float = 0.8,
        min_cluster_size: int = 2
    ) -> List[List[str]]:
        """
        Find clusters of similar entities.

        Args:
            min_similarity: Minimum similarity for clustering
            min_cluster_size: Minimum cluster size

        Returns:
            List of entity clusters
        """
        async with self.pool.acquire() as conn:
            # Get all embeddings
            results = await conn.fetch("""
                SELECT entity_id, embedding::float[] as embedding
                FROM entity_embeddings
            """)

            if len(results) < min_cluster_size:
                return []

            entity_ids = [row["entity_id"] for row in results]
            embeddings = np.array([row["embedding"] for row in results])

            # Compute similarity matrix
            similarity_matrix = cosine_similarity(embeddings)

            # Simple clustering based on similarity threshold
            clusters = []
            visited = set()

            for i, entity_id in enumerate(entity_ids):
                if entity_id in visited:
                    continue

                cluster = [entity_id]
                visited.add(entity_id)

                for j, other_id in enumerate(entity_ids):
                    if i != j and other_id not in visited:
                        if similarity_matrix[i][j] >= min_similarity:
                            cluster.append(other_id)
                            visited.add(other_id)

                if len(cluster) >= min_cluster_size:
                    clusters.append(cluster)

            return clusters

    async def update_embedding(
        self,
        entity_id: str,
        embedding: List[float]
    ) -> bool:
        """
        Update embedding for an entity.

        Args:
            entity_id: Entity ID
            embedding: New embedding vector

        Returns:
            True if update was successful
        """
        if len(embedding) != self.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.dimension}, "
                f"got {len(embedding)}"
            )

        async with self.pool.acquire() as conn:
            embedding_str = f"[{','.join(map(str, embedding))}]"

            result = await conn.fetchval("""
                UPDATE entity_embeddings
                SET embedding = $2::vector, updated_at = CURRENT_TIMESTAMP
                WHERE entity_id = $1
                RETURNING id
            """, entity_id, embedding_str)

            if result:
                logger.info("Embedding updated", entity_id=entity_id)
                return True
            return False

    async def delete_embedding(self, entity_id: str) -> bool:
        """
        Delete embedding for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            True if deletion was successful
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("""
                DELETE FROM entity_embeddings
                WHERE entity_id = $1
                RETURNING id
            """, entity_id)

            if result:
                logger.info("Embedding deleted", entity_id=entity_id)
                return True
            return False

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored embeddings.

        Returns:
            Statistics dictionary
        """
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_embeddings,
                    COUNT(DISTINCT entity_type) as unique_types,
                    AVG((metadata->>'confidence_score')::float) as avg_confidence
                FROM entity_embeddings
            """)

            type_counts = await conn.fetch("""
                SELECT entity_type, COUNT(*) as count
                FROM entity_embeddings
                GROUP BY entity_type
                ORDER BY count DESC
            """)

            return {
                "total_embeddings": stats["total_embeddings"],
                "unique_types": stats["unique_types"],
                "avg_confidence": float(stats["avg_confidence"] or 0),
                "type_distribution": {
                    row["entity_type"]: row["count"]
                    for row in type_counts
                }
            }