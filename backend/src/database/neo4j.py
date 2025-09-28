from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import Optional
import structlog

from ..config import settings

logger = structlog.get_logger(__name__)


class Neo4jDB:
    def __init__(self):
        self.driver: Optional[AsyncDriver] = None

    async def connect(self):
        try:
            self.driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                max_connection_lifetime=3600
            )

            await self.driver.verify_connectivity()

            await self._init_schema()

            logger.info(
                "Connected to Neo4j",
                uri=settings.neo4j_uri,
                database=settings.neo4j_database
            )
        except Exception as e:
            logger.error("Failed to connect to Neo4j", error=str(e))
            raise

    async def disconnect(self):
        if self.driver:
            await self.driver.close()
            logger.info("Disconnected from Neo4j")

    async def _init_schema(self):
        async with self.driver.session(database=settings.neo4j_database) as session:
            try:
                await session.run("""
                    CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
                    FOR (e:Entity) REQUIRE e.id IS UNIQUE
                """)
            except:
                pass  # Constraint might already exist

            indices = [
                "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
                "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
                "CREATE INDEX entity_created IF NOT EXISTS FOR (e:Entity) ON (e.created_at)",
                "CREATE INDEX person_id IF NOT EXISTS FOR (p:Person) ON (p.id)",
                "CREATE INDEX event_id IF NOT EXISTS FOR (e:Event) ON (e.id)",
                "CREATE INDEX location_id IF NOT EXISTS FOR (l:Location) ON (l.id)",
                "CREATE INDEX organization_id IF NOT EXISTS FOR (o:Organization) ON (o.id)",
                "CREATE INDEX document_id IF NOT EXISTS FOR (d:Document) ON (d.id)"
            ]

            for index_query in indices:
                try:
                    await session.run(index_query)
                except:
                    pass  # Index might already exist

            logger.info("Neo4j schema initialized")

    def get_driver(self) -> AsyncDriver:
        if not self.driver:
            raise RuntimeError("Neo4j driver not initialized. Call connect() first.")
        return self.driver