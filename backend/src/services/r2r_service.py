"""R2R service for document processing and RAG operations."""

import os
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import httpx
import structlog
from fastapi import UploadFile
from r2r import R2RClient
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import settings

logger = structlog.get_logger(__name__)


class R2RServiceError(Exception):
    """Base exception for R2R service errors."""

    pass


class R2RConnectionError(R2RServiceError):
    """Exception raised when connection to R2R fails."""

    pass


class R2RIngestionError(R2RServiceError):
    """Exception raised when document ingestion fails."""

    pass


class R2RService:
    """Service for R2R document processing and RAG operations."""

    SUPPORTED_FORMATS = {"pdf", "docx", "txt", "html", "md", "csv", "json"}
    ENTITY_TYPES = ["Person", "Event", "Location"]

    def __init__(self, base_url: str = "http://localhost:7272"):
        """Initialize R2R service client."""
        self.base_url = base_url or settings.r2r_base_url
        self.client = R2RClient(self.base_url)
        self._httpx = httpx.AsyncClient(
            timeout=httpx.Timeout(5.0, connect=2.0),
            headers={"Accept": "application/json"},
        )
        self._temp_dir = tempfile.gettempdir()

        logger.info("R2R service initialized", base_url=self.base_url)

    async def health_check(self) -> dict[str, Any]:
        """Check R2R service health."""
        try:
            response = await self._httpx.get(f"{self.base_url}/v3/health")
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "connected": True,
                    "details": response.json(),
                }
            else:
                return {
                    "status": "unhealthy",
                    "connected": False,
                    "error": f"Health check returned {response.status_code}",
                }
        except Exception as e:
            logger.warning("R2R health check failed", error=str(e))
            return {
                "status": "unavailable",
                "connected": False,
                "error": str(e),
                "fallback_mode": True,
            }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    async def ingest_document(
        self, file: UploadFile, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Ingest document with entity extraction.

        Args:
            file: The uploaded file to ingest
            metadata: Optional metadata to attach to the document

        Returns:
            Document information including ID and status
        """
        # Validate file format
        file_extension = file.filename.split(".")[-1].lower() if file.filename else ""
        if file_extension not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported file format: {file_extension}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        temp_path = None
        try:
            # Save file temporarily
            temp_path = Path(self._temp_dir) / f"upload_{file.filename}"
            content = await file.read()
            await file.seek(0)  # Reset for potential reuse

            with open(temp_path, "wb") as f:
                f.write(content)

            logger.info(
                "Ingesting document",
                filename=file.filename,
                size=len(content),
                temp_path=str(temp_path),
            )

            # Ingest with R2R
            response = self.client.documents.create(
                file_path=str(temp_path),
                metadata={
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "source": "web_upload",
                    **(metadata or {}),
                },
                ingestion_mode="fast",  # Use "hi-res" for better quality
            )

            # Response contains document_id and task_id
            result = {
                "document_id": response["results"]["document_id"],
                "status": "processing",
                "task_id": response["results"].get("task_id"),
                "filename": file.filename,
            }

            logger.info(
                "Document ingestion initiated",
                document_id=result["document_id"],
                task_id=result.get("task_id"),
            )

            return result

        except Exception as e:
            logger.error(f"Ingestion failed: {e}", filename=file.filename)
            if isinstance(e, ValueError):
                raise
            raise R2RIngestionError(f"Document ingestion failed: {str(e)}") from e
        finally:
            # Clean up temp file
            if temp_path and temp_path.exists():
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to remove temp file: {e}")

    async def hybrid_search(
        self, query: str, filters: dict[str, Any] | None = None, limit: int = 20
    ) -> dict[str, Any]:
        """
        Perform hybrid vector + keyword search.

        Args:
            query: The search query
            filters: Optional filters to apply
            limit: Maximum number of results

        Returns:
            Search results with relevance scores
        """
        try:
            logger.info(
                "Performing hybrid search",
                query=query[:100],
                has_filters=bool(filters),
                limit=limit,
            )

            response = self.client.retrieval.search(
                query=query,
                search_settings={
                    "use_hybrid_search": True,
                    "use_semantic_search": True,
                    "filters": filters or {},
                    "limit": limit,
                    "search_mode": "advanced",
                },
            )

            results = response.get("results", [])

            logger.info(
                "Hybrid search completed",
                query=query[:50],
                results_count=len(results),
            )

            return {"results": results, "total": len(results), "query": query}

        except Exception as e:
            logger.error("Hybrid search failed", error=str(e), query=query[:100])
            raise R2RServiceError(f"Search failed: {str(e)}") from e

    async def rag_query(
        self,
        query: str,
        use_graph: bool = True,
        filters: dict[str, Any] | None = None,
    ) -> str:
        """
        Perform RAG query without streaming.

        Args:
            query: The query to answer
            use_graph: Whether to use graph search
            filters: Optional document filters

        Returns:
            Generated response
        """
        try:
            logger.info(
                "Executing RAG query",
                query=query[:100],
                use_graph=use_graph,
            )

            response = self.client.retrieval.rag(
                query=query,
                search_settings={
                    "use_hybrid_search": True,
                    "filters": filters or {},
                    "graph_search_settings": {
                        "enabled": use_graph,
                        "include_communities": True,
                    } if use_graph else None,
                },
                rag_generation_config={
                    "model": "anthropic/claude-3-haiku-20240307",
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
            )

            answer = response.get("results", {}).get("completion", {}).get("choices", [{}])[0].get("message", {}).get("content", "")

            logger.info(
                "RAG query completed",
                query=query[:50],
                answer_length=len(answer),
            )

            return answer

        except Exception as e:
            logger.error("RAG query failed", error=str(e), query=query[:100])
            raise R2RServiceError(f"RAG query failed: {str(e)}") from e

    async def rag_query_stream(
        self, query: str, use_graph: bool = True, filters: dict[str, Any] | None = None
    ) -> AsyncGenerator[str]:
        """
        Stream RAG responses.

        Args:
            query: The query to answer
            use_graph: Whether to use graph search
            filters: Optional document filters

        Yields:
            Response chunks as they arrive
        """
        try:
            logger.info(
                "Starting RAG stream",
                query=query[:100],
                use_graph=use_graph,
            )

            response = self.client.retrieval.rag(
                query=query,
                search_settings={
                    "use_hybrid_search": True,
                    "filters": filters or {},
                    "graph_search_settings": {
                        "enabled": use_graph,
                        "include_communities": True,
                    } if use_graph else None,
                },
                rag_generation_config={
                    "model": "anthropic/claude-3-haiku-20240307",
                    "stream": True,
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
            )

            # Stream processing
            for chunk in response:
                if chunk and isinstance(chunk, dict):
                    # Extract content from chunk
                    if "choices" in chunk:
                        for choice in chunk["choices"]:
                            delta = choice.get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                    elif "content" in chunk:
                        yield chunk["content"]

            logger.info("RAG stream completed")

        except Exception as e:
            logger.error("RAG stream failed", error=str(e))
            raise R2RServiceError(f"Stream failed: {str(e)}") from e

    async def get_document_entities(self, document_id: str) -> dict[str, Any]:
        """
        Get entities extracted from document.

        Args:
            document_id: The document ID

        Returns:
            Extracted entities grouped by type
        """
        try:
            # R2R auto-extracts during ingestion
            entities = self.client.documents.list_entities(document_id)

            # Group entities by type
            grouped = {entity_type: [] for entity_type in self.ENTITY_TYPES}

            for entity in entities.get("results", []):
                entity_type = entity.get("type", "Unknown")
                if entity_type in grouped:
                    grouped[entity_type].append({
                        "name": entity.get("name"),
                        "confidence": entity.get("confidence", 0.0),
                        "metadata": entity.get("metadata", {})
                    })

            return {
                "document_id": document_id,
                "entities": grouped,
                "total_count": len(entities.get("results", []))
            }

        except Exception as e:
            logger.error(
                "Failed to get document entities",
                error=str(e),
                document_id=document_id,
            )
            raise R2RServiceError(f"Failed to get entities: {str(e)}") from e

    async def get_document_status(self, document_id: str) -> dict[str, Any]:
        """
        Get the processing status of a document.

        Args:
            document_id: The document ID to check

        Returns:
            Status information including processing state
        """
        try:
            response = self.client.documents.retrieve(document_id)

            return {
                "document_id": document_id,
                "status": response.get("results", {}).get("status", "unknown"),
                "metadata": response.get("results", {}).get("metadata", {}),
                "created_at": response.get("results", {}).get("created_at"),
                "updated_at": response.get("results", {}).get("updated_at"),
            }

        except Exception as e:
            logger.error(
                "Failed to get document status",
                error=str(e),
                document_id=document_id,
            )
            raise R2RServiceError(f"Status check failed: {str(e)}") from e

    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from R2R.

        Args:
            document_id: The document ID to delete

        Returns:
            True if deletion was successful
        """
        try:
            self.client.documents.delete(document_id)
            logger.info("Document deleted", document_id=document_id)
            return True

        except Exception as e:
            logger.error(
                "Failed to delete document",
                error=str(e),
                document_id=document_id,
            )
            return False

    async def list_documents(
        self, filters: dict[str, Any] | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        List documents in the R2R system.

        Args:
            filters: Optional filters
            limit: Maximum number of documents to return

        Returns:
            List of document metadata
        """
        try:
            response = self.client.documents.list(
                filters=filters or {},
                limit=limit
            )

            documents = []
            for doc in response.get("results", []):
                documents.append({
                    "document_id": doc.get("id"),
                    "filename": doc.get("metadata", {}).get("filename", "Unknown"),
                    "status": doc.get("status"),
                    "created_at": doc.get("created_at"),
                    "metadata": doc.get("metadata", {})
                })

            return documents

        except Exception as e:
            logger.error("Failed to list documents", error=str(e))
            raise R2RServiceError(f"Failed to list documents: {str(e)}") from e

    async def get_task_status(self, task_id: str) -> dict[str, Any]:
        """
        Get the status of an ingestion task.

        Args:
            task_id: The task ID to check

        Returns:
            Task status information
        """
        try:
            response = await self._httpx.get(f"{self.base_url}/tasks/{task_id}")

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "task_id": task_id,
                    "status": "unknown",
                    "error": f"Status check returned {response.status_code}"
                }

        except Exception as e:
            logger.error("Failed to get task status", error=str(e), task_id=task_id)
            return {
                "task_id": task_id,
                "status": "error",
                "error": str(e)
            }

    async def cleanup(self):
        """Clean up resources."""
        if self._httpx:
            await self._httpx.aclose()
        logger.info("R2R service cleaned up")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
