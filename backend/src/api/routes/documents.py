from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from typing import Optional, Dict, Any, List
import structlog
import json

from ...services import R2RService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


async def get_r2r_service():
    async with R2RService() as service:
        yield service


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
    extract_entities: bool = Form(True),
    r2r_service: R2RService = Depends(get_r2r_service)
):
    """
    Upload and process a document.

    Args:
        file: Document file to upload
        metadata: Optional JSON metadata
        extract_entities: Whether to extract entities

    Returns:
        Document processing result
    """
    try:
        doc_metadata = json.loads(metadata) if metadata else {}

        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            document_id = await r2r_service.ingest_document(
                file_path=tmp_file_path,
                metadata=doc_metadata
            )

            entities = []
            if extract_entities:
                entities = await r2r_service.extract_entities(document_id)

            return {
                "status": "success",
                "document_id": document_id,
                "filename": file.filename,
                "size": len(content),
                "entities_extracted": len(entities),
                "entities": entities[:10]  # Return first 10 entities
            }

        finally:
            # Clean up temp file
            os.unlink(tmp_file_path)

    except Exception as e:
        logger.error("Document upload failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    include_chunks: bool = False,
    r2r_service: R2RService = Depends(get_r2r_service)
):
    """
    Get document details.

    Args:
        document_id: R2R document ID
        include_chunks: Whether to include document chunks

    Returns:
        Document metadata and optionally chunks
    """
    try:
        metadata = await r2r_service.get_document_metadata(document_id)

        response = {
            "document_id": document_id,
            "metadata": metadata
        }

        if include_chunks:
            chunks = await r2r_service.get_document_chunks(document_id)
            response["chunks"] = chunks
            response["chunk_count"] = len(chunks)

        return response

    except Exception as e:
        logger.error("Failed to get document", error=str(e), document_id=document_id)
        raise HTTPException(status_code=404, detail="Document not found")


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    r2r_service: R2RService = Depends(get_r2r_service)
):
    """
    Delete a document.

    Args:
        document_id: R2R document ID

    Returns:
        Deletion confirmation
    """
    try:
        success = await r2r_service.delete_document(document_id)

        if success:
            return {
                "status": "success",
                "message": f"Document {document_id} deleted"
            }
        else:
            raise HTTPException(status_code=404, detail="Document not found")

    except Exception as e:
        logger.error("Document deletion failed", error=str(e), document_id=document_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/upload")
async def batch_upload(
    files: List[UploadFile] = File(...),
    r2r_service: R2RService = Depends(get_r2r_service)
):
    """
    Upload multiple documents.

    Args:
        files: List of document files

    Returns:
        Batch upload results
    """
    results = []

    for file in files:
        try:
            # Save uploaded file temporarily
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_file_path = tmp_file.name

            try:
                # Ingest document
                document_id = await r2r_service.ingest_document(
                    file_path=tmp_file_path,
                    metadata={"filename": file.filename}
                )

                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "document_id": document_id
                })

            finally:
                os.unlink(tmp_file_path)

        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "failed",
                "error": str(e)
            })

    successful = sum(1 for r in results if r["status"] == "success")

    return {
        "total": len(files),
        "successful": successful,
        "failed": len(files) - successful,
        "results": results
    }


@router.get("/{document_id}/entities")
async def get_document_entities(
    document_id: str,
    entity_types: Optional[List[str]] = None,
    r2r_service: R2RService = Depends(get_r2r_service)
):
    """
    Get entities extracted from a document.

    Args:
        document_id: R2R document ID
        entity_types: Optional filter by entity types

    Returns:
        List of extracted entities
    """
    try:
        entities = await r2r_service.extract_entities(
            document_id,
            entity_types=entity_types
        )

        return {
            "document_id": document_id,
            "entity_count": len(entities),
            "entities": entities
        }

    except Exception as e:
        logger.error(
            "Failed to get document entities",
            error=str(e),
            document_id=document_id
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create-graph")
async def create_graph_from_documents(
    document_ids: List[str],
    extraction_config: Optional[Dict[str, Any]] = None,
    r2r_service: R2RService = Depends(get_r2r_service)
):
    """
    Create knowledge graph from documents.

    Args:
        document_ids: List of document IDs
        extraction_config: Optional extraction configuration

    Returns:
        Graph creation result
    """
    try:
        result = await r2r_service.create_graph_from_documents(
            document_ids,
            extraction_config=extraction_config
        )

        return {
            "status": "success",
            "documents_processed": len(document_ids),
            "graph_data": result
        }

    except Exception as e:
        logger.error("Graph creation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))