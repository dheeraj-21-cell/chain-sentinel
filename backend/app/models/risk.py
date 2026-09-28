from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceContribution(BaseModel):
    """Structured record of a single evidence source's contribution to the risk score."""
    source: str = Field(..., description="Evidence category: behavioral, ml_anomaly, clustering, graph_topology, activity_volume")
    points: float = Field(..., description="Points awarded by this category toward total score")
    max_points: float = Field(..., description="Configured maximum possible points for this category")
    status: str = Field(..., description="Status: present, not_observed, data_unavailable")
    observed_facts: Dict[str, Any] = Field(default_factory=dict, description="Observed factual metrics for this evidence source")
    rationale: str = Field(..., description="Objective explanation of how points were calculated")


class RiskFinding(BaseModel):
    """Complete investigative risk prioritization result for a single entity."""
    risk_id: str = Field(..., description="Deterministic unique identifier for this risk finding")
    dataset_id: str = Field(..., description="Unique dataset identifier to preserve strict dataset scoping")
    entity_type: str = Field(..., description="Target entity type (wallet or transaction)")
    entity_id: str = Field(..., description="Primary identifier of scored entity (address or txid)")
    score: float = Field(..., ge=0.0, le=100.0, description="Normalized investigative priority score in [0.0, 100.0]")
    priority: str = Field(..., description="Investigative priority band: LOW, MODERATE, HIGH, CRITICAL")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Evidence completeness and multi-pipeline coverage score")
    evidence_contributions: Dict[str, EvidenceContribution] = Field(default_factory=dict, description="Detailed breakdown by evidence category")
    supporting_behavior_findings: List[str] = Field(default_factory=list, description="IDs of linked behavioral findings from Phase 8")
    ml_evidence: Optional[Dict[str, Any]] = Field(None, description="Isolation Forest anomaly signals if available")
    graph_evidence: Optional[Dict[str, Any]] = Field(None, description="NetworkX topological degree and centralities if available")
    clustering_evidence: Optional[Dict[str, Any]] = Field(None, description="DBSCAN cluster assignment and noise status if available")
    activity_evidence: Optional[Dict[str, Any]] = Field(None, description="Transaction throughput and network telemetry if available")
    explanation: str = Field(..., description="Human-readable forensic rationale explaining priority and facts observed")
    limitations: List[str] = Field(default_factory=list, description="Methodological caveats, unobserved data, and non-attribution statements")
    scoring_version: str = Field("1.0.0", description="Risk scoring engine version")


class RiskSummary(BaseModel):
    """Dataset-level overview of risk scoring distributions and pipeline coverage."""
    dataset_id: str = Field(..., description="Target dataset ID")
    total_scored_entities: int = Field(..., description="Total count of entities evaluated")
    counts_by_priority: Dict[str, int] = Field(default_factory=dict, description="Entity counts keyed by priority band")
    average_score: float = Field(..., description="Mean investigative priority score across dataset")
    highest_score: float = Field(..., description="Maximum investigative priority score observed")
    evidence_coverage: Dict[str, int] = Field(default_factory=dict, description="Count of entities with data present per evidence category")
    scoring_version: str = Field("1.0.0", description="Risk scoring engine version")


class RiskMetadata(BaseModel):
    """Engine configuration, weights, priority thresholds, and forensic limitations."""
    dataset_id: str = Field(..., description="Target dataset ID")
    scoring_version: str = Field("1.0.0", description="Engine version")
    weights: Dict[str, float] = Field(default_factory=dict, description="Maximum weights for each evidence category")
    thresholds: Dict[str, Any] = Field(default_factory=dict, description="Threshold parameters applied during evaluation")
    score_range: Dict[str, float] = Field(default_factory=lambda: {"min": 0.0, "max": 100.0}, description="Score range bounds")
    priority_bands: Dict[str, str] = Field(default_factory=dict, description="Score intervals corresponding to priority bands")
    evidence_sources: List[str] = Field(default_factory=list, description="Catalog of integrated evidence sources")
    limitations: List[str] = Field(default_factory=list, description="Forensic and legal disclaimers")
    created_at: str = Field(..., description="UTC ISO-8601 execution timestamp")


class RiskScoringRequest(BaseModel):
    """Configurable weights for running risk scoring."""
    behavioral_weight: float = Field(35.0, ge=0.0, le=100.0, description="Max points for behavioral indicators")
    ml_weight: float = Field(25.0, ge=0.0, le=100.0, description="Max points for ML anomaly signals")
    clustering_weight: float = Field(15.0, ge=0.0, le=100.0, description="Max points for clustering noise status")
    graph_weight: float = Field(15.0, ge=0.0, le=100.0, description="Max points for graph topological metrics")
    activity_weight: float = Field(10.0, ge=0.0, le=100.0, description="Max points for volume and telemetry")


class RiskScoringResult(BaseModel):
    """Complete response containing summary and ranked findings."""
    dataset_id: str = Field(..., description="Target dataset ID")
    summary: RiskSummary = Field(..., description="Summary statistics")
    findings: List[RiskFinding] = Field(default_factory=list, description="List of scored entity findings ordered by score descending")
