"""Relationship models for GraphAura knowledge graph."""

from datetime import datetime
from typing import Optional, Any, Dict, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
import uuid


class RelationType(str, Enum):
    """Types of relationships between entities."""
    # Personal relationships
    KNOWS = "knows"
    FAMILY_OF = "family_of"
    FRIEND_OF = "friend_of"
    COLLEAGUE_OF = "colleague_of"
    MENTOR_OF = "mentor_of"

    # Professional relationships
    WORKS_FOR = "works_for"
    EMPLOYED_BY = "employed_by"
    MANAGES = "manages"
    COLLABORATES_WITH = "collaborates_with"
    FOUNDED = "founded"
    OWNS = "owns"

    # Event relationships
    ATTENDED = "attended"
    ORGANIZED = "organized"
    PARTICIPATED_IN = "participated_in"
    SPOKE_AT = "spoke_at"
    HOSTED = "hosted"

    # Location relationships
    LOCATED_IN = "located_in"
    LIVED_IN = "lived_in"
    VISITED = "visited"
    BORN_IN = "born_in"
    DIED_IN = "died_in"

    # Document relationships
    AUTHORED = "authored"
    CITED = "cited"
    MENTIONED_IN = "mentioned_in"
    REFERENCES = "references"

    # Hierarchical relationships
    PARENT_OF = "parent_of"
    CHILD_OF = "child_of"
    PART_OF = "part_of"
    CONTAINS = "contains"

    # Temporal relationships
    PRECEDED_BY = "preceded_by"
    FOLLOWED_BY = "followed_by"
    CONCURRENT_WITH = "concurrent_with"

    # Conceptual relationships
    RELATED_TO = "related_to"
    SIMILAR_TO = "similar_to"
    OPPOSITE_OF = "opposite_of"
    CAUSED_BY = "caused_by"
    RESULTED_IN = "resulted_in"


class Relationship(BaseModel):
    """Relationship between two entities."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = Field(..., description="Source entity ID")
    target_id: str = Field(..., description="Target entity ID")
    type: RelationType

    # Relationship properties
    properties: Dict[str, Any] = Field(default_factory=dict)
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Relationship strength")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)

    # Temporal information
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Source tracking
    source_documents: List[str] = Field(default_factory=list, description="Document IDs")
    evidence: List[str] = Field(default_factory=list, description="Text evidence")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_neo4j(self) -> Dict[str, Any]:
        """Convert to Neo4j relationship properties."""
        props = {
            "id": self.id,
            "type": self.type.value,
            "weight": self.weight,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

        if self.start_date:
            props["start_date"] = self.start_date.isoformat()
        if self.end_date:
            props["end_date"] = self.end_date.isoformat()

        props.update(self.properties)
        return props


class RelationshipFilter(BaseModel):
    """Filter criteria for relationship searches."""
    types: Optional[List[RelationType]] = None
    source_ids: Optional[List[str]] = None
    target_ids: Optional[List[str]] = None
    min_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    active_on: Optional[datetime] = None
    source_documents: Optional[List[str]] = None


class GraphTraversalRequest(BaseModel):
    """Request for graph traversal queries."""
    start_entity_id: str = Field(..., description="Starting entity ID")
    relationship_types: Optional[List[RelationType]] = None
    max_depth: int = Field(default=2, ge=1, le=5)
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    limit: int = Field(default=100, ge=1, le=1000)

    # Traversal options
    include_properties: bool = Field(default=True)
    bidirectional: bool = Field(default=True)

    # Path finding
    target_entity_id: Optional[str] = None
    find_shortest_path: bool = Field(default=False)


class GraphPattern(BaseModel):
    """Pattern matching for graph queries."""
    entity_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    relationship_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    return_fields: List[str] = Field(default_factory=list)

    # Query options
    limit: int = Field(default=50, ge=1, le=500)
    skip: int = Field(default=0, ge=0)
    order_by: Optional[str] = None
    descending: bool = Field(default=False)


class GraphAnalytics(BaseModel):
    """Graph analytics request."""
    metric: str = Field(..., description="centrality, clustering, community, etc.")
    entity_ids: Optional[List[str]] = None
    relationship_types: Optional[List[RelationType]] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class GraphVisualization(BaseModel):
    """Graph visualization configuration."""
    layout: str = Field(default="force", description="force, hierarchical, circular, etc.")
    node_size_attribute: Optional[str] = None
    node_color_attribute: Optional[str] = None
    edge_weight_attribute: Optional[str] = None

    # Display options
    show_labels: bool = Field(default=True)
    show_properties: bool = Field(default=False)
    highlight_paths: List[List[str]] = Field(default_factory=list)

    # Filtering
    entity_filter: Optional["EntityFilter"] = None
    relationship_filter: Optional[RelationshipFilter] = None

    # Performance
    max_nodes: int = Field(default=100, ge=1, le=1000)
    max_edges: int = Field(default=200, ge=1, le=2000)


# Import EntityFilter for type hints
from .entities import EntityFilter

GraphVisualization.model_rebuild()