from typing import List
from fastapi import APIRouter, HTTPException, Query, status

from app.models.graph_analysis import (
    ConnectedComponentInfo,
    GraphMetricsSummary,
    PathResult,
    WalletGraphMetrics,
)
from app.services import graph_analysis

router = APIRouter(prefix="/api/v1/networkx", tags=["NetworkX Graph Analysis"])


@router.get("/{dataset_id}/metrics", response_model=GraphMetricsSummary)
async def get_graph_metrics_endpoint(dataset_id: str) -> GraphMetricsSummary:
    """Retrieve NetworkX topological metrics, degree averages, and components for a dataset graph."""
    try:
        return graph_analysis.get_graph_metrics(dataset_id)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"NetworkX graph analysis failed: {str(err)}",
        )


@router.get("/{dataset_id}/wallets", response_model=List[WalletGraphMetrics])
async def get_wallet_features_endpoint(
    dataset_id: str,
    limit: int = Query(50, ge=1, le=500),
) -> List[WalletGraphMetrics]:
    """Retrieve wallet fan-in, fan-out, total degree, and centralities."""
    try:
        return graph_analysis.get_wallet_features(dataset_id, limit=limit)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate wallet features: {str(err)}",
        )


@router.get("/{dataset_id}/components", response_model=List[ConnectedComponentInfo])
async def get_connected_components_endpoint(dataset_id: str) -> List[ConnectedComponentInfo]:
    """Segment dataset investigation graph into weakly connected components."""
    try:
        return graph_analysis.get_connected_components(dataset_id)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate connected components: {str(err)}",
        )


@router.get("/{dataset_id}/paths", response_model=PathResult)
async def get_shortest_path_endpoint(
    dataset_id: str,
    source: str = Query(..., description="Source node address, txid, or identifier"),
    target: str = Query(..., description="Target node address, txid, or identifier"),
) -> PathResult:
    """Find multi-hop shortest path between two nodes in the dataset graph."""
    try:
        return graph_analysis.get_shortest_path(dataset_id, source=source, target=target)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Path search failed: {str(err)}",
        )
