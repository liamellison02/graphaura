"""Entity models for GraphAura knowledge graph."""

from datetime import datetime
from typing import Optional, Any, Dict, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
import uuid


class EntityType(str, Enum):
    """Types of entities in the knowledge graph."""
    PERSON = "person"
    EVENT = "event"
    LOCATION = "location"
    ORGANIZATION = "organization"
    CONCEPT = "concept"
    DOCUMENT = "document"
    ARTIFACT = "artifact"


class Entity(BaseModel):
    """Base entity model."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EntityType
    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    properties: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    source_documents: List[str] = Field(default_factory=list, description="Document IDs")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_neo4j(self) -> Dict[str, Any]:
        """Convert to Neo4j node properties."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "tags": self.tags,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            **self.properties
        }


class Person(Entity):
    """Person entity with specific attributes."""
    type: EntityType = Field(default=EntityType.PERSON, frozen=True)

    # Person-specific fields
    birth_date: Optional[datetime] = None
    death_date: Optional[datetime] = None
    nationality: Optional[str] = None
    occupation: Optional[str] = None
    affiliations: List[str] = Field(default_factory=list)
    aliases: List[str] = Field(default_factory=list)

    # Social/contact information
    email: Optional[str] = None
    phone: Optional[str] = None
    social_profiles: Dict[str, str] = Field(default_factory=dict)

    # Additional metadata
    gender: Optional[str] = None
    biography: Optional[str] = None
    achievements: List[str] = Field(default_factory=list)


class Event(Entity):
    """Event entity with temporal information."""
    type: EntityType = Field(default=EntityType.EVENT, frozen=True)

    # Event-specific fields
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    location_id: Optional[str] = None
    participants: List[str] = Field(default_factory=list, description="Person IDs")
    organizers: List[str] = Field(default_factory=list, description="Organization IDs")

    # Event details
    event_type: Optional[str] = None
    status: Optional[str] = Field(None, description="planned, ongoing, completed, cancelled")
    attendance: Optional[int] = None
    impact_score: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Related events
    parent_event_id: Optional[str] = None
    sub_events: List[str] = Field(default_factory=list)


class Location(Entity):
    """Location entity with geographic information."""
    type: EntityType = Field(default=EntityType.LOCATION, frozen=True)

    # Geographic coordinates
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    altitude: Optional[float] = None

    # Address information
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None

    # Location details
    location_type: Optional[str] = Field(None, description="city, building, landmark, etc.")
    area: Optional[float] = Field(None, description="Area in square meters")
    population: Optional[int] = None
    timezone: Optional[str] = None

    # Related locations
    parent_location_id: Optional[str] = None
    nearby_locations: List[str] = Field(default_factory=list)


class Organization(Entity):
    """Organization entity."""
    type: EntityType = Field(default=EntityType.ORGANIZATION, frozen=True)

    # Organization details
    founded_date: Optional[datetime] = None
    dissolved_date: Optional[datetime] = None
    organization_type: Optional[str] = None
    industry: Optional[str] = None
    headquarters_location_id: Optional[str] = None

    # People associations
    founders: List[str] = Field(default_factory=list, description="Person IDs")
    executives: List[str] = Field(default_factory=list, description="Person IDs")
    employees: List[str] = Field(default_factory=list, description="Person IDs")

    # Additional info
    website: Optional[str] = None
    revenue: Optional[float] = None
    employee_count: Optional[int] = None
    parent_organization_id: Optional[str] = None
    subsidiaries: List[str] = Field(default_factory=list)


class Document(Entity):
    """Document entity for source materials."""
    type: EntityType = Field(default=EntityType.DOCUMENT, frozen=True)

    # Document metadata
    document_type: Optional[str] = None
    authors: List[str] = Field(default_factory=list, description="Person IDs")
    publication_date: Optional[datetime] = None
    publisher: Optional[str] = None

    # Content information
    url: Optional[str] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    language: Optional[str] = None

    # Indexing metadata
    r2r_document_id: Optional[str] = None
    chunk_ids: List[str] = Field(default_factory=list)
    extracted_entities: List[str] = Field(default_factory=list)


# Search and filter models
class EntityFilter(BaseModel):
    """Filter criteria for entity searches."""
    types: Optional[List[EntityType]] = None
    tags: Optional[List[str]] = None
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    source_documents: Optional[List[str]] = None


class EntitySearchRequest(BaseModel):
    """Entity search request."""
    query: str = Field(..., min_length=1)
    filter: Optional[EntityFilter] = None
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    include_embeddings: bool = Field(default=False)