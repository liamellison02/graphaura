"""Neo4j graph database service for GraphAura."""

from typing import Optional, Dict, Any, List, Tuple
from neo4j import AsyncGraphDatabase, AsyncDriver
import structlog

from ..config import settings
from ..models.entities import Entity, EntityFilter
from ..models.relationships import (
    Relationship,
    RelationshipFilter,
    GraphTraversalRequest
)

logger = structlog.get_logger(__name__)


class Neo4jService:
    """Service for Neo4j graph database operations."""

    def __init__(self):
        """Initialize Neo4j service."""
        self.uri = settings.neo4j_uri
        self.auth = (settings.neo4j_user, settings.neo4j_password)
        self.database = settings.neo4j_database
        self.driver: Optional[AsyncDriver] = None

    async def connect(self):
        """Connect to Neo4j database."""
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=self.auth,
                max_connection_lifetime=3600
            )
            await self.driver.verify_connectivity()
            logger.info("Connected to Neo4j", uri=self.uri)
        except Exception as e:
            logger.error("Failed to connect to Neo4j", error=str(e))
            raise

    async def disconnect(self):
        """Disconnect from Neo4j database."""
        if self.driver:
            await self.driver.close()
            logger.info("Disconnected from Neo4j")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def create_entity(self, entity: Entity) -> str:
        """
        Create an entity node in Neo4j.

        Args:
            entity: Entity to create

        Returns:
            Entity ID
        """
        async with self.driver.session(database=self.database) as session:
            query = """
            CREATE (e:Entity {props})
            SET e:""" + entity.type.value.capitalize() + """
            RETURN e.id as id
            """

            result = await session.run(
                query,
                props=entity.to_neo4j()
            )
            record = await result.single()

            logger.info("Entity created", entity_id=entity.id, type=entity.type)
            return record["id"]

    async def update_entity(self, entity_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an entity in Neo4j.

        Args:
            entity_id: Entity ID
            updates: Properties to update

        Returns:
            True if update was successful
        """
        async with self.driver.session(database=self.database) as session:
            query = """
            MATCH (e:Entity {id: $entity_id})
            SET e += $updates
            SET e.updated_at = datetime()
            RETURN e.id as id
            """

            result = await session.run(
                query,
                entity_id=entity_id,
                updates=updates
            )
            record = await result.single()

            if record:
                logger.info("Entity updated", entity_id=entity_id)
                return True
            return False

    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an entity from Neo4j.

        Args:
            entity_id: Entity ID

        Returns:
            Entity data or None if not found
        """
        async with self.driver.session(database=self.database) as session:
            query = """
            MATCH (e:Entity {id: $entity_id})
            RETURN e
            """

            result = await session.run(query, entity_id=entity_id)
            record = await result.single()

            if record:
                return dict(record["e"])
            return None

    async def delete_entity(self, entity_id: str) -> bool:
        """
        Delete an entity and its relationships.

        Args:
            entity_id: Entity ID

        Returns:
            True if deletion was successful
        """
        async with self.driver.session(database=self.database) as session:
            query = """
            MATCH (e:Entity {id: $entity_id})
            DETACH DELETE e
            RETURN count(e) as deleted
            """

            result = await session.run(query, entity_id=entity_id)
            record = await result.single()

            if record["deleted"] > 0:
                logger.info("Entity deleted", entity_id=entity_id)
                return True
            return False

    async def create_relationship(self, relationship: Relationship) -> str:
        """
        Create a relationship between entities.

        Args:
            relationship: Relationship to create

        Returns:
            Relationship ID
        """
        async with self.driver.session(database=self.database) as session:
            query = f"""
            MATCH (source:Entity {{id: $source_id}})
            MATCH (target:Entity {{id: $target_id}})
            CREATE (source)-[r:{relationship.type.value.upper()} $props]->(target)
            RETURN id(r) as rel_id
            """

            result = await session.run(
                query,
                source_id=relationship.source_id,
                target_id=relationship.target_id,
                props=relationship.to_neo4j()
            )
            record = await result.single()

            if record:
                logger.info(
                    "Relationship created",
                    relationship_id=relationship.id,
                    type=relationship.type
                )
                return relationship.id
            raise ValueError("Failed to create relationship")

    async def find_entities(
        self,
        filter: Optional[EntityFilter] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Find entities matching filter criteria.

        Args:
            filter: Entity filter criteria
            limit: Maximum number of results
            offset: Result offset

        Returns:
            List of matching entities
        """
        async with self.driver.session(database=self.database) as session:
            where_clauses = []
            params = {"limit": limit, "offset": offset}

            if filter:
                if filter.types:
                    type_labels = [t.value.capitalize() for t in filter.types]
                    where_clauses.append(
                        f"any(label in labels(e) WHERE label IN {type_labels})"
                    )

                if filter.tags:
                    where_clauses.append("any(tag IN $tags WHERE tag IN e.tags)")
                    params["tags"] = filter.tags

                if filter.min_confidence is not None:
                    where_clauses.append("e.confidence_score >= $min_confidence")
                    params["min_confidence"] = filter.min_confidence

            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

            query = f"""
            MATCH (e:Entity)
            WHERE {where_clause}
            RETURN e
            ORDER BY e.created_at DESC
            SKIP $offset
            LIMIT $limit
            """

            result = await session.run(query, **params)
            entities = []
            async for record in result:
                entities.append(dict(record["e"]))

            return entities

    async def traverse_graph(
        self,
        request: GraphTraversalRequest
    ) -> Dict[str, Any]:
        """
        Traverse the graph from a starting entity.

        Args:
            request: Graph traversal request

        Returns:
            Traversal results with nodes and edges
        """
        async with self.driver.session(database=self.database) as session:
            rel_filter = ""
            if request.relationship_types:
                rel_types = [r.value.upper() for r in request.relationship_types]
                rel_filter = f":{"|".join(rel_types)}"

            direction = "*" if request.bidirectional else ">"

            if request.find_shortest_path and request.target_entity_id:
                query = f"""
                MATCH path = shortestPath(
                    (start:Entity {{id: $start_id}})-
                    [r{rel_filter}*..{request.max_depth}]-
                    (end:Entity {{id: $target_id}})
                )
                WHERE all(rel IN relationships(path)
                         WHERE rel.confidence_score >= $min_confidence)
                RETURN path
                LIMIT 1
                """
                params = {
                    "start_id": request.start_entity_id,
                    "target_id": request.target_entity_id,
                    "min_confidence": request.min_confidence
                }
            else:
                query = f"""
                MATCH path = (start:Entity {{id: $start_id}})-
                      [r{rel_filter}*1..{request.max_depth}]-{direction}
                      (connected:Entity)
                WHERE all(rel IN relationships(path)
                         WHERE rel.confidence_score >= $min_confidence)
                RETURN DISTINCT connected, relationships(path) as rels
                LIMIT $limit
                """
                params = {
                    "start_id": request.start_entity_id,
                    "min_confidence": request.min_confidence,
                    "limit": request.limit
                }

            result = await session.run(query, **params)

            nodes = []
            edges = []
            node_ids = set()

            async for record in result:
                if "path" in record:
                    # Process shortest path
                    path = record["path"]
                    for node in path.nodes:
                        if node["id"] not in node_ids:
                            nodes.append(dict(node))
                            node_ids.add(node["id"])
                    for rel in path.relationships:
                        edges.append({
                            "source": rel.start_node["id"],
                            "target": rel.end_node["id"],
                            "type": rel.type,
                            "properties": dict(rel)
                        })
                else:
                    # Process general traversal
                    node = dict(record["connected"])
                    if node["id"] not in node_ids:
                        nodes.append(node)
                        node_ids.add(node["id"])

                    for rel in record["rels"]:
                        edges.append({
                            "source": rel.start_node["id"],
                            "target": rel.end_node["id"],
                            "type": rel.type,
                            "properties": dict(rel)
                        })

            return {
                "nodes": nodes,
                "edges": edges,
                "node_count": len(nodes),
                "edge_count": len(edges)
            }

    async def get_entity_relationships(
        self,
        entity_id: str,
        direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """
        Get all relationships for an entity.

        Args:
            entity_id: Entity ID
            direction: Relationship direction (in, out, both)

        Returns:
            List of relationships
        """
        async with self.driver.session(database=self.database) as session:
            if direction == "out":
                query = """
                MATCH (e:Entity {id: $entity_id})-[r]->(target:Entity)
                RETURN r, target
                """
            elif direction == "in":
                query = """
                MATCH (source:Entity)-[r]->(e:Entity {id: $entity_id})
                RETURN r, source
                """
            else:
                query = """
                MATCH (e:Entity {id: $entity_id})-[r]-(other:Entity)
                RETURN r, other,
                       CASE WHEN startNode(r) = e THEN 'out' ELSE 'in' END as direction
                """

            result = await session.run(query, entity_id=entity_id)
            relationships = []

            async for record in result:
                rel_data = dict(record["r"])
                if "direction" in record:
                    rel_data["direction"] = record["direction"]

                if "target" in record:
                    rel_data["target"] = dict(record["target"])
                elif "source" in record:
                    rel_data["source"] = dict(record["source"])
                else:
                    rel_data["other"] = dict(record["other"])

                relationships.append(rel_data)

            return relationships

    async def execute_cypher(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a raw Cypher query.

        Args:
            query: Cypher query
            parameters: Query parameters

        Returns:
            Query results
        """
        async with self.driver.session(database=self.database) as session:
            result = await session.run(query, parameters or {})
            records = []
            async for record in result:
                records.append(dict(record))
            return records

    async def create_indices(self):
        """Create database indices for performance."""
        async with self.driver.session(database=self.database) as session:
            indices = [
                "CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.id)",
                "CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.type)",
                "CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.name)",
                "CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.created_at)",
                "CREATE INDEX IF NOT EXISTS FOR (e:Person) ON (e.id)",
                "CREATE INDEX IF NOT EXISTS FOR (e:Event) ON (e.id)",
                "CREATE INDEX IF NOT EXISTS FOR (e:Location) ON (e.id)",
                "CREATE INDEX IF NOT EXISTS FOR (e:Organization) ON (e.id)",
                "CREATE INDEX IF NOT EXISTS FOR (e:Document) ON (e.id)"
            ]

            for index_query in indices:
                await session.run(index_query)

            logger.info("Neo4j indices created")