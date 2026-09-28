from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.risk import (
    RiskFinding,
    RiskMetadata,
    RiskScoringRequest,
    RiskScoringResult,
    RiskSummary,
)
from app.services import risk_scoring

router = APIRouter(prefix="/api/v1/risk", tags=["Risk Scoring & Explainability"])


@router.post("/{dataset_id}/score", response_model=RiskScoringResult)
def run_score(
    dataset_id: str,
    request: Optional[RiskScoringRequest] = None,
) -> RiskScoringResult:
    """Run deterministic, multi-pipeline risk scoring and explainability for a dataset."""
    try:
        return risk_scoring.run_risk_scoring(dataset_id, request)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk scoring failed: {str(e)}")


@router.get("/{dataset_id}/summary", response_model=RiskSummary)
def get_summary(dataset_id: str) -> RiskSummary:
    """Retrieve dataset-level risk distributions, priority band counts, and pipeline coverage."""
    try:
        return risk_scoring.get_risk_summary(dataset_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch risk summary: {str(e)}")


@router.get("/{dataset_id}/findings", response_model=List[RiskFinding])
def get_findings(
    dataset_id: str,
    priority: Optional[str] = Query(None, description="Filter by priority band (LOW, MODERATE, HIGH, CRITICAL)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (wallet, transaction)"),
    minimum_score: Optional[float] = Query(None, ge=0.0, le=100.0, description="Minimum risk score threshold"),
    limit: int = Query(50, ge=1, le=500, description="Maximum findings to return"),
) -> List[RiskFinding]:
    """Retrieve ranked, explainable risk findings for the dataset with optional filtering."""
    try:
        return risk_scoring.get_risk_findings(
            dataset_id,
            priority=priority,
            entity_type=entity_type,
            minimum_score=minimum_score,
            limit=limit,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch risk findings: {str(e)}")


@router.get("/{dataset_id}/metadata", response_model=RiskMetadata)
def get_metadata(dataset_id: str) -> RiskMetadata:
    """Retrieve risk engine configuration, weights, priority bands, and forensic limitations."""
    try:
        return risk_scoring.get_risk_metadata(dataset_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch risk metadata: {str(e)}")
