from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnomalyScoreItem(BaseModel):
    entity_id: str = Field(..., description="Canonical entity identifier (e.g. txid or wallet address)")
    entity_type: str = Field(..., description="Entity category: 'transaction' or 'wallet'")
    anomaly_label: int = Field(..., description="Isolation Forest classification label: -1 for anomalous lead, 1 for normal")
    is_anomaly: bool = Field(..., description="True if marked as an anomalous investigative lead")
    raw_score: float = Field(..., description="Raw decision_function score from Isolation Forest (lower is more anomalous)")
    anomaly_score: float = Field(..., description="Normalized anomaly score in [0.0, 1.0], where higher indicates more anomalous")
    features: Dict[str, Any] = Field(default_factory=dict, description="Observed feature snapshot for this entity")
    explanation: List[str] = Field(default_factory=list, description="Neutral forensic explanations of feature deviations")


class AnomalyDetectionResult(BaseModel):
    dataset_id: str = Field(..., description="UUID of the isolated dataset")
    entity_type: str = Field(..., description="Target entity type analyzed ('transaction' or 'wallet')")
    model_name: str = Field(..., description="Algorithm identifier (e.g. 'scikit-learn IsolationForest')")
    model_version: str = Field(..., description="Model version tag")
    timestamp: str = Field(..., description="Execution timestamp (ISO 8601)")
    total_entities: int = Field(..., description="Total number of entities evaluated")
    anomaly_count: int = Field(..., description="Total number of entities flagged as anomalous leads")
    contamination: float = Field(..., description="Contamination parameter configured for the model")
    random_state: int = Field(..., description="Deterministic random state seed")
    anomalies: List[AnomalyScoreItem] = Field(default_factory=list, description="List of scored entity items")


class ModelMetadata(BaseModel):
    dataset_id: str = Field(..., description="UUID of the isolated dataset")
    entity_type: str = Field(..., description="Entity type: 'transaction' or 'wallet'")
    model_name: str = Field(..., description="Model name")
    model_version: str = Field(..., description="Model version")
    n_estimators: int = Field(..., description="Number of isolation trees")
    contamination: float = Field(..., description="Contamination parameter")
    random_state: int = Field(..., description="Deterministic random state seed")
    feature_names: List[str] = Field(default_factory=list, description="List of feature column names used for training")
    imputed_fields: Dict[str, str] = Field(default_factory=dict, description="Record of fields that underwent deterministic imputation")
    training_samples: int = Field(..., description="Count of training feature rows")
    anomaly_samples: int = Field(..., description="Count of identified anomalous instances")
    model_path: str = Field(..., description="Filesystem location of serialized model artifact")
    created_at: str = Field(..., description="Training timestamp (ISO 8601)")


class FeatureGenerationResponse(BaseModel):
    dataset_id: str = Field(..., description="UUID of the isolated dataset")
    entity_type: str = Field(..., description="Entity type: 'transaction' or 'wallet'")
    feature_count: int = Field(..., description="Number of numerical feature columns generated")
    feature_names: List[str] = Field(default_factory=list, description="Names of extracted features")
    record_count: int = Field(..., description="Number of records extracted")
    imputed_fields: Dict[str, str] = Field(default_factory=dict, description="Documentation of missing-field imputation rules applied")
    feature_file_path: str = Field(..., description="Location of persisted Parquet feature table")
