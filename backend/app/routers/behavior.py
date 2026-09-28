from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.behavior import (
    BehaviorSummary,
    BehavioralDetectionRequest,
    BehavioralDetectionResult,
    BehavioralFinding,
    BehavioralMetadata,
)
from app.services import behavioral_detection

router = APIRouter(prefix="/api/v1/behavior", tags=["Behavioral Detection"])


@router.post("/{dataset_id}/detect", response_model=BehavioralDetectionResult)
def run_detection(
    dataset_id: str,
    request: Optional[BehavioralDetectionRequest] = None,
) -> BehavioralDetectionResult:
    """Execute the deterministic behavioral detection pipeline on the active dataset."""
    try:
        return behavioral_detection.run_behavioral_detection(dataset_id, request)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Behavioral detection failed: {str(e)}")


@router.get("/{dataset_id}/summary", response_model=BehaviorSummary)
def get_summary(dataset_id: str) -> BehaviorSummary:
    """Retrieve summary counts and detector status for the dataset."""
    try:
        return behavioral_detection.get_behavior_summary(dataset_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch behavior summary: {str(e)}")


@router.get("/{dataset_id}/findings", response_model=List[BehavioralFinding])
def get_findings(
    dataset_id: str,
    detection_type: Optional[str] = Query(None, description="Filter by detection type (fan_in, fan_out, etc.)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (wallet, transaction, ip)"),
    minimum_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    limit: int = Query(50, ge=1, le=500, description="Max findings to return"),
) -> List[BehavioralFinding]:
    """Retrieve structured behavioral findings with optional filtering."""
    try:
        return behavioral_detection.get_behavior_findings(
            dataset_id,
            detection_type=detection_type,
            entity_type=entity_type,
            minimum_confidence=minimum_confidence,
            limit=limit,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch behavior findings: {str(e)}")


@router.get("/{dataset_id}/metadata", response_model=BehavioralMetadata)
def get_metadata(dataset_id: str) -> BehavioralMetadata:
    """Retrieve detector version, enabled algorithms, thresholds, and methodological limitations."""
    try:
        return behavioral_detection.get_behavior_metadata(dataset_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch behavior metadata: {str(e)}")
