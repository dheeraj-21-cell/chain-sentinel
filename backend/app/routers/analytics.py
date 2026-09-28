from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.models.analytics import (
    CorrelationRecord,
    DatasetAnalyticsSummary,
    TimeSeriesBucket,
    WalletActivity,
)
from app.services import analytics

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/{dataset_id}/summary", response_model=DatasetAnalyticsSummary)
async def get_dataset_summary_endpoint(dataset_id: str) -> DatasetAnalyticsSummary:
    """Retrieve comprehensive dataset-level analytical aggregations via DuckDB."""
    try:
        return analytics.get_dataset_summary(dataset_id)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DuckDB analytics query failed: {str(err)}",
        )


@router.get("/{dataset_id}/wallets", response_model=List[WalletActivity])
async def get_wallet_analytics_endpoint(
    dataset_id: str,
    limit: int = Query(50, ge=1, le=500),
) -> List[WalletActivity]:
    """Retrieve wallet addresses observed in dataset with sent/received volume and net flow."""
    try:
        return analytics.get_wallet_analytics(dataset_id, limit=limit)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DuckDB wallet analytics failed: {str(err)}",
        )


@router.get("/{dataset_id}/time-series", response_model=List[TimeSeriesBucket])
async def get_time_series_endpoint(dataset_id: str) -> List[TimeSeriesBucket]:
    """Retrieve time-window activity buckets (transaction counts and volume)."""
    try:
        return analytics.get_time_series_analytics(dataset_id)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DuckDB time-series analysis failed: {str(err)}",
        )


@router.get("/{dataset_id}/network", response_model=Dict[str, Any])
async def get_network_analytics_endpoint(dataset_id: str) -> Dict[str, Any]:
    """Retrieve network telemetry observations, communicating IP pairs, and ASN/Country breakdowns."""
    try:
        return analytics.get_network_analytics(dataset_id)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DuckDB network analytics failed: {str(err)}",
        )


@router.get("/{dataset_id}/correlations", response_model=List[CorrelationRecord])
async def get_correlation_records_endpoint(
    dataset_id: str,
    limit: int = Query(100, ge=1, le=1000),
) -> List[CorrelationRecord]:
    """Retrieve correlation-ready records joining on-chain transactions with network peer metadata."""
    try:
        return analytics.get_correlation_records(dataset_id, limit=limit)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DuckDB correlation analysis failed: {str(err)}",
        )
