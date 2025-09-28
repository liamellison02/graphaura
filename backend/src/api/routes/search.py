# Search and retrieval API routes.

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, Any, List
import structlog

from ...services import R2RService, Neo4jService, VectorService
from ...models.entities import EntitySearchRequest

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


async def get_r2r_service():
    async with R2RService() as service:
        yield service


async def get_neo4j_service():
    async with Neo4jService() as service:
        yield service


async def get_vector_service():
    async with VectorService() as service:
        yield service


@router.post("/documents")
async def search_documents(
    query: str,
    search_type: str = "hybrid",
    limit: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    r2r_service: R2RService = Depends(get_r2r_service)
):
    """
    Search for documents using R2R.

    Args:
        query: Search query
        search_type: Type of search (vector, keyword, hybrid)
        limit: Maximum results
        filters: Optional filters

    Returns:
        Search results from documents
    """
    try:
        results = await r2r_service.search(
            query=query,
            search_type=search_type,
            limit=limit,
            filters=filters
        )

        return {
            "query": query,
            "search_type": search_type,
            "count": len(results),
            "results": results
        }

    except Exception as e:
        logger.error("Document search failed", error=str(e), query=query)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag")
async def rag_search(
    messages: List[Dict[str, str]],
    search_query: Optional[str] = None,
    use_knowledge_graph: bool = True,
    r2r_service: R2RService = Depends(get_r2r_service)
):
    """
    Perform RAG search with context.

    Args:
        messages: Chat messages
        search_query: Optional search query
        use_knowledge_graph: Whether to use knowledge graph

    Returns:
        RAG completion with context
    """
    try:
        result = await r2r_service.rag_completion(
            messages=messages,
            search_query=search_query,
            use_knowledge_graph=use_knowledge_graph
        )

        return {
            "status": "success",
            "response": result
        }

    except Exception as e:
        logger.error("RAG search failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hybrid")
async def hybrid_search(
    query: str,
    limit: int = 10,
    include_graph: bool = True,
    include_documents: bool = True,
    entity_types: Optional[List[str]] = None,
    r2r_service: R2RService = Depends(get_r2r_service),
    neo4j_service: Neo4jService = Depends(get_neo4j_service)
):
    """
    Hybrid search across documents and graph.

    Args:
        query: Search query
        limit: Maximum results per source
        include_graph: Include graph search
        include_documents: Include document search
        entity_types: Filter entity types

    Returns:
        Combined search results
    """
    try:
        results = {
            "query": query,
            "sources": []
        }


        if include_documents:
            doc_results = await r2r_service.search(
                query=query,
                search_type="hybrid",
                limit=limit
            )
            results["sources"].append({
                "type": "documents",
                "count": len(doc_results),
                "results": doc_results
            })


        if include_graph:
            from ...models.entities import EntityFilter

            entity_filter = EntityFilter(
                types=entity_types if entity_types else None
            )

            graph_results = await neo4j_service.find_entities(
                filter=entity_filter,
                limit=limit
            )

            filtered_graph = [
                e for e in graph_results
                if query.lower() in e.get("name", "").lower()
                or query.lower() in e.get("description", "").lower()
            ]

            results["sources"].append({
                "type": "graph",
                "count": len(filtered_graph),
                "results": filtered_graph
            })

        results["total_count"] = sum(s["count"] for s in results["sources"])

        return results

    except Exception as e:
        logger.error("Hybrid search failed", error=str(e), query=query)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/semantic")
async def semantic_search(
    query_embedding: List[float],
    limit: int = 10,
    entity_types: Optional[List[str]] = None,
    threshold: float = 0.7,
    include_documents: bool = True,
    vector_service: VectorService = Depends(get_vector_service),
    r2r_service: R2RService = Depends(get_r2r_service),
    neo4j_service: Neo4jService = Depends(get_neo4j_service)
):
    """
    Perform semantic search using embeddings.

    Args:
        query_embedding: Query embedding vector
        limit: Maximum results
        entity_types: Filter by entity types
        threshold: Similarity threshold
        include_documents: Include document search

    Returns:
        Semantically similar results
    """
    try:
        results = {
            "embedding_dimension": len(query_embedding),
            "threshold": threshold,
            "sources": []
        }

        entity_results = await vector_service.similarity_search(
            query_embedding=query_embedding,
            limit=limit,
            entity_types=entity_types,
            threshold=threshold
        )

        enriched_entities = []
        for item in entity_results:
            entity = await neo4j_service.get_entity(item["entity_id"])
            if entity:
                enriched_entities.append({
                    **item,
                    "entity": entity
                })

        results["sources"].append({
            "type": "entities",
            "count": len(enriched_entities),
            "results": enriched_entities
        })

        if include_documents:
            doc_results = await r2r_service.search(
                query="", 
                search_type="vector",
                limit=limit
            )

            results["sources"].append({
                "type": "documents",
                "count": len(doc_results),
                "results": doc_results
            })

        results["total_count"] = sum(s["count"] for s in results["sources"])

        return results

    except Exception as e:
        logger.error("Semantic search failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/contextual")
async def contextual_search(
    query: str,
    context_entity_ids: List[str],
    max_depth: int = 2,
    limit: int = 20,
    neo4j_service: Neo4jService = Depends(get_neo4j_service),
    r2r_service: R2RService = Depends(get_r2r_service)
):
    """
    Search with graph context from specific entities.

    Args:
        query: Search query
        context_entity_ids: Entity IDs for context
        max_depth: max. graph traversal depth
        limit: max. results

    Returns:
        Contextual search results
    """
    try:
        related_entities = []
        for entity_id in context_entity_ids:
            from ...models.relationships import GraphTraversalRequest

            traversal = GraphTraversalRequest(
                start_entity_id=entity_id,
                max_depth=max_depth,
                limit=limit // len(context_entity_ids)
            )

            traversal_result = await neo4j_service.traverse_graph(traversal)
            related_entities.extend(traversal_result["nodes"])

        entity_names = list(set(
            e.get("name", "") for e in related_entities
            if e.get("name")
        ))

        contextual_query = f"{query} {' '.join(entity_names[:10])}"

        doc_results = await r2r_service.search(
            query=contextual_query,
            search_type="hybrid",
            limit=limit
        )

        return {
            "query": query,
            "context_entities": len(context_entity_ids),
            "related_entities": len(related_entities),
            "document_results": doc_results,
            "graph_context": related_entities[:10]
        }

    except Exception as e:
        logger.error("Contextual search failed", error=str(e), query=query)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions")
async def get_search_suggestions(
    partial_query: str,
    limit: int = 5,
    neo4j_service: Neo4jService = Depends(get_neo4j_service)
):
    """
    Get search suggestions based on partial query.

    Args:
        partial_query: Partial search query
        limit: Max. suggestions

    Returns:
        List of search suggestions
    """
    try:
        from ...models.entities import EntityFilter

        entities = await neo4j_service.find_entities(limit=100)

        suggestions = []
        for entity in entities:
            name = entity.get("name", "")
            if partial_query.lower() in name.lower():
                suggestions.append({
                    "text": name,
                    "type": entity.get("type", "unknown"),
                    "entity_id": entity.get("id")
                })

                if len(suggestions) >= limit:
                    break

        return {
            "query": partial_query,
            "suggestions": suggestions
        }

    except Exception as e:
        logger.error(
            "Failed to get search suggestions",
            error=str(e),
            query=partial_query
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters")
async def get_entity_clusters(
    min_similarity: float = 0.8,
    min_cluster_size: int = 2,
    vector_service: VectorService = Depends(get_vector_service),
    neo4j_service: Neo4jService = Depends(get_neo4j_service)
):
    """
    Get clusters of similar entities.

    Args:
        min_similarity: min. similarity for clustering
        min_cluster_size: min. cluster size

    Returns:
        Entity clusters
    """
    try:
        clusters = await vector_service.find_clusters(
            min_similarity=min_similarity,
            min_cluster_size=min_cluster_size
        )

        enriched_clusters = []
        for cluster in clusters:
            cluster_entities = []
            for entity_id in cluster:
                entity = await neo4j_service.get_entity(entity_id)
                if entity:
                    cluster_entities.append(entity)

            if cluster_entities:
                enriched_clusters.append({
                    "size": len(cluster_entities),
                    "entities": cluster_entities
                })

        return {
            "cluster_count": len(enriched_clusters),
            "min_similarity": min_similarity,
            "min_cluster_size": min_cluster_size,
            "clusters": enriched_clusters
        }

    except Exception as e:
        logger.error("Failed to get entity clusters", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
