"""
graph/schema.py — Pydantic models for all graph entities and relationships.
These models are used for API request/response validation and Neo4j mapping.
"""

from __future__ import annotations
from typing import Optional, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


# ── Entity Types ──────────────────────────────────────────────────────────────

class EntityType(str, Enum):
    PERSON       = "Person"
    ORGANIZATION = "Organization"
    LOCATION     = "Location"
    PHONE        = "PhoneNumber"
    VEHICLE      = "Vehicle"
    ACCOUNT      = "BankAccount"
    EVENT        = "Event"
    DEVICE       = "Device"


# ── Relationship Types ────────────────────────────────────────────────────────

class RelationType(str, Enum):
    CALLED           = "CALLED"
    ASSOCIATED_WITH  = "ASSOCIATED_WITH"
    PRESENT_AT       = "PRESENT_AT"
    TRANSFERRED_TO   = "TRANSFERRED_TO"
    OWNS             = "OWNS"
    MEMBER_OF        = "MEMBER_OF"
    CO_ACCUSED_IN    = "CO_ACCUSED_IN"
    USES             = "USES"
    LOCATED_AT       = "LOCATED_AT"
    REPORTED_IN      = "REPORTED_IN"
    MET_WITH         = "MET_WITH"
    TRAVELED_TO      = "TRAVELED_TO"


# ── Risk Levels ───────────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


# ── Base Entity ───────────────────────────────────────────────────────────────

class EntityBase(BaseModel):
    id: Optional[str] = None
    name: str
    entity_type: EntityType
    aliases: List[str] = Field(default_factory=list)
    source_documents: List[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Analytics (populated by analytics engine)
    degree_centrality: Optional[float] = None
    betweenness_centrality: Optional[float] = None
    pagerank: Optional[float] = None
    risk_score: Optional[float] = None
    risk_level: Optional[RiskLevel] = None
    community_id: Optional[int] = None


class PersonEntity(EntityBase):
    entity_type: EntityType = EntityType.PERSON
    age: Optional[int] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    address: Optional[str] = None
    phone_numbers: List[str] = Field(default_factory=list)
    criminal_history: List[str] = Field(default_factory=list)
    occupation: Optional[str] = None


class OrganizationEntity(EntityBase):
    entity_type: EntityType = EntityType.ORGANIZATION
    org_type: Optional[str] = None        # gang, shell_company, cartel, etc.
    registered_address: Optional[str] = None
    known_activities: List[str] = Field(default_factory=list)


class LocationEntity(EntityBase):
    entity_type: EntityType = EntityType.LOCATION
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_type: Optional[str] = None  # residence, meeting_point, crime_scene


class PhoneEntity(EntityBase):
    entity_type: EntityType = EntityType.PHONE
    number: str = ""
    carrier: Optional[str] = None
    imei: Optional[str] = None
    last_known_tower: Optional[str] = None


class VehicleEntity(EntityBase):
    entity_type: EntityType = EntityType.VEHICLE
    plate_number: str = ""
    vehicle_type: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    registered_to: Optional[str] = None


class BankAccountEntity(EntityBase):
    entity_type: EntityType = EntityType.ACCOUNT
    account_number: str = ""
    bank_name: Optional[str] = None
    account_holder: Optional[str] = None
    total_credits: Optional[float] = None
    total_debits: Optional[float] = None
    suspicious_transactions: int = 0


class EventEntity(EntityBase):
    entity_type: EntityType = EntityType.EVENT
    event_type: str = ""          # crime, meeting, transaction, arrest
    event_date: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None
    fir_number: Optional[str] = None


# ── Relationship ──────────────────────────────────────────────────────────────

class RelationshipModel(BaseModel):
    id: Optional[str] = None
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0
    properties: dict = Field(default_factory=dict)   # timestamp, amount, duration…
    source_document: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


# ── Graph Response ────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    label: str
    entity_type: EntityType
    properties: dict = Field(default_factory=dict)
    risk_level: Optional[RiskLevel] = None
    community_id: Optional[int] = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relation_type: RelationType
    weight: float = 1.0
    properties: dict = Field(default_factory=dict)


class GraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_nodes: int
    total_edges: int


# ── Anomaly Alert ─────────────────────────────────────────────────────────────

class AnomalyAlert(BaseModel):
    id: str
    entity_id: str
    entity_name: str
    alert_type: str           # call_burst, night_activity, geo_velocity, etc.
    severity: RiskLevel
    description: str
    anomaly_score: float
    detected_at: datetime
    evidence: dict = Field(default_factory=dict)


# ── Intelligence Report ───────────────────────────────────────────────────────

class IntelligenceReport(BaseModel):
    entity_id: str
    entity_name: str
    entity_type: EntityType
    risk_score: float
    risk_level: RiskLevel
    summary: str
    known_associates: List[str]
    timeline_highlights: List[dict]
    community_membership: Optional[str]
    centrality_rank: Optional[int]
    recommendations: List[str]
    generated_at: datetime
    source_documents: List[str]


# ── Case Management ──────────────────────────────────────────────────────────

class CaseStatus(str, Enum):
    OPEN       = "OPEN"
    ACTIVE     = "ACTIVE"
    CLOSED     = "CLOSED"
    ARCHIVED   = "ARCHIVED"


class CaseCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    priority: str = "MEDIUM"      # LOW, MEDIUM, HIGH, CRITICAL
    assigned_to: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class CaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CaseStatus] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None


class CaseEntityAdd(BaseModel):
    entity_id: str
