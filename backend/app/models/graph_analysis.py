from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class GraphMetricsSummary(BaseModel):
    dataset_id: str
    node_count: int
    edge_count: int
    density: float
    is_directed: bool = True
    connected_components_count: int
    largest_component_size: int
    nodes_by_type: Dict[str, int] = Field(default_factory=dict)
    edges_by_type: Dict[str, int] = Field(default_factory=dict)
    average_degree: float


class WalletGraphMetrics(BaseModel):
    address: str
    degree: int
    fan_in: int = Field(..., description="Count of transactions funding this wallet (received)")
    fan_out: int = Field(..., description="Count of transactions funded by this wallet (spent)")
    in_degree_centrality: float
    out_degree_centrality: float


class ConnectedComponentInfo(BaseModel):
    component_id: int
    node_count: int
    edge_count: int
    node_types: Dict[str, int] = Field(default_factory=dict)
    sample_nodes: List[str] = Field(default_factory=list)


class PathResult(BaseModel):
    source: str
    target: str
    path_exists: bool
    length: Optional[int] = None
    node_path: List[str] = Field(default_factory=list)
    edge_types: List[str] = Field(default_factory=list)
