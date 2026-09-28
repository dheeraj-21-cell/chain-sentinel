from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WalletClusterItem(BaseModel):
    address: str = Field(..., description="Canonical wallet address")
    cluster_id: int = Field(..., description="DBSCAN cluster identifier: -1 for noise/outlier, >= 0 for dense clusters")
    is_noise: bool = Field(..., description="True if marked as DBSCAN noise (-1)")
    features: Dict[str, float] = Field(default_factory=dict, description="Observed behavioral and topological feature snapshot")


class ClusterSummary(BaseModel):
    cluster_id: int = Field(..., description="Cluster identifier")
    member_count: int = Field(..., description="Number of wallets grouped into this behavioral cluster")
    sample_addresses: List[str] = Field(default_factory=list, description="Sample wallet addresses in this cluster")
    avg_sent_btc: float = Field(..., description="Mean cumulative sent BTC for wallets in this cluster")
    avg_received_btc: float = Field(..., description="Mean cumulative received BTC for wallets in this cluster")
    avg_degree: float = Field(..., description="Mean graph degree for wallets in this cluster")
    avg_fan_in: float = Field(..., description="Mean fan-in (incoming payments received) for wallets in this cluster")
    avg_fan_out: float = Field(..., description="Mean fan-out (spending transactions funded) for wallets in this cluster")
    description: str = Field(..., description="Neutral forensic description of the behavioral profile")


class DBSCANClusteringResult(BaseModel):
    dataset_id: str = Field(..., description="UUID of the isolated dataset")
    entity_type: str = Field("wallet", description="Entity category: 'wallet'")
    eps: float = Field(..., description="Maximum neighborhood distance for DBSCAN core points")
    min_samples: int = Field(..., description="Minimum samples required to form a dense cluster")
    total_entities: int = Field(..., description="Total number of wallets evaluated")
    cluster_count: int = Field(..., description="Number of dense clusters formed (excluding noise)")
    noise_count: int = Field(..., description="Number of unclustered noise entities (label -1)")
    clustered_count: int = Field(..., description="Number of entities assigned to valid clusters")
    clusters: List[ClusterSummary] = Field(default_factory=list, description="Summary profiles of all identified clusters")
    entities: List[WalletClusterItem] = Field(default_factory=list, description="List of scored entity cluster assignments")


class ClusteringMetadata(BaseModel):
    dataset_id: str = Field(..., description="UUID of the isolated dataset")
    entity_type: str = Field("wallet", description="Entity type: 'wallet'")
    model_name: str = Field("scikit-learn DBSCAN", description="Clustering algorithm name")
    eps: float = Field(..., description="Epsilon neighborhood distance")
    min_samples: int = Field(..., description="Minimum points threshold")
    metric: str = Field("euclidean", description="Distance metric")
    total_entities: int = Field(..., description="Total entities evaluated")
    cluster_count: int = Field(..., description="Dense clusters identified")
    noise_count: int = Field(..., description="Noise points identified")
    features_used: List[str] = Field(default_factory=list, description="Feature columns used for clustering")
    cluster_summaries: List[ClusterSummary] = Field(default_factory=list, description="Profiles of clusters")
    created_at: str = Field(..., description="Timestamp of execution (ISO 8601)")
