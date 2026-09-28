from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GraphBuildResponse(BaseModel):
    dataset_id: str
    status: str
    transactions_created_or_matched: int = 0
    wallets_created_or_matched: int = 0
    ips_created_or_matched: int = 0
    asns_created_or_matched: int = 0
    countries_created_or_matched: int = 0
    relationships_created_or_matched: int = 0
    message: str


class GraphSummaryResponse(BaseModel):
    dataset_id: str
    total_nodes: int = 0
    total_relationships: int = 0
    nodes_by_label: Dict[str, int] = Field(default_factory=dict)
    relationships_by_type: Dict[str, int] = Field(default_factory=dict)


class GraphElementNode(BaseModel):
    id: str
    label: str
    canonical_id: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    ml_anomaly: Optional[Dict[str, Any]] = None
    cluster_id: Optional[int] = None
    behavior_findings_count: int = 0
    behavior_finding_types: List[str] = Field(default_factory=list)
    risk_priority: Optional[str] = None
    risk_score: Optional[float] = None


class GraphElementEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphElementsResponse(BaseModel):
    dataset_id: str
    nodes: List[GraphElementNode] = Field(default_factory=list)
    edges: List[GraphElementEdge] = Field(default_factory=list)
    total_dataset_nodes: int = 0
    total_dataset_edges: int = 0
    is_bounded: bool = False
    message: Optional[str] = None
