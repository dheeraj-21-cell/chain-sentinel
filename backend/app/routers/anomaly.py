from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.models.anomaly import (
    AnomalyDetectionResult,
    FeatureGenerationResponse,
    ModelMetadata,
)
from app.services import anomaly_detection, ml_features

router = APIRouter(prefix="/api/v1/ml", tags=["Machine Learning Anomaly Detection"])


@router.post(
    "/{dataset_id}/features/generate",
    response_model=FeatureGenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_features_endpoint(
    dataset_id: str,
    entity_type: str = Query("transaction", description="Entity level: 'transaction' or 'wallet'"),
) -> FeatureGenerationResponse:
    """Extract and persist dataset-isolated numerical features for machine learning."""
    try:
        return ml_features.generate_and_persist_features(dataset_id=dataset_id, entity_type=entity_type)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feature generation failed: {str(err)}",
        )


@router.post(
    "/{dataset_id}/train",
    response_model=AnomalyDetectionResult,
    status_code=status.HTTP_200_OK,
)
async def train_model_endpoint(
    dataset_id: str,
    entity_type: str = Query("transaction", description="Target entity: 'transaction' or 'wallet'"),
    contamination: float = Query(0.1, ge=0.001, le=0.5, description="Expected proportion of anomalies"),
    n_estimators: int = Query(100, ge=10, le=500, description="Number of Isolation Trees"),
    random_state: int = Query(42, description="Random seed for deterministic reproducibility"),
) -> AnomalyDetectionResult:
    """Train scikit-learn IsolationForest model and generate anomaly scores for the dataset."""
    try:
        return anomaly_detection.train_isolation_forest(
            dataset_id=dataset_id,
            entity_type=entity_type,
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
        )
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Isolation Forest training failed: {str(err)}",
        )


@router.get(
    "/{dataset_id}/anomalies",
    response_model=AnomalyDetectionResult,
)
async def get_anomalies_endpoint(
    dataset_id: str,
    entity_type: str = Query("transaction", description="Entity level: 'transaction' or 'wallet'"),
    limit: int = Query(100, ge=1, le=1000, description="Max entities to return"),
    anomalies_only: bool = Query(False, description="Filter for only flagged investigative leads"),
) -> AnomalyDetectionResult:
    """Retrieve anomaly scores and explanations for a dataset."""
    try:
        return anomaly_detection.get_anomalies(
            dataset_id=dataset_id,
            entity_type=entity_type,
            limit=limit,
            anomalies_only=anomalies_only,
        )
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve anomalies: {str(err)}",
        )


@router.get(
    "/{dataset_id}/metadata",
    response_model=ModelMetadata,
)
async def get_model_metadata_endpoint(
    dataset_id: str,
    entity_type: str = Query("transaction", description="Entity level: 'transaction' or 'wallet'"),
) -> ModelMetadata:
    """Retrieve Isolation Forest model hyperparameters and feature catalog."""
    try:
        return anomaly_detection.get_model_metadata(dataset_id=dataset_id, entity_type=entity_type)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve model metadata: {str(err)}",
        )
