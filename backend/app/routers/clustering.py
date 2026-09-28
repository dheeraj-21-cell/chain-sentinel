from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.models.clustering import (
    ClusteringMetadata,
    DBSCANClusteringResult,
    WalletClusterItem,
)
from app.services import clustering

router = APIRouter(prefix="/api/v1/clustering", tags=["DBSCAN Behavioral Clustering"])


@router.post(
    "/{dataset_id}/run",
    response_model=DBSCANClusteringResult,
    status_code=status.HTTP_200_OK,
)
async def run_clustering_endpoint(
    dataset_id: str,
    eps: float = Query(0.5, gt=0.0, description="DBSCAN maximum neighborhood distance"),
    min_samples: int = Query(2, ge=1, description="Minimum samples to form a dense cluster"),
) -> DBSCANClusteringResult:
    """Execute DBSCAN behavioral clustering over wallet entities for an isolated dataset."""
    try:
        return clustering.run_dbscan_clustering(dataset_id=dataset_id, eps=eps, min_samples=min_samples)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DBSCAN clustering execution failed: {str(err)}",
        )


@router.get(
    "/{dataset_id}/summary",
    response_model=DBSCANClusteringResult,
)
async def get_clustering_summary_endpoint(dataset_id: str) -> DBSCANClusteringResult:
    """Retrieve high-level clustering summary and cluster profiles for the dataset."""
    try:
        return clustering.get_clustering_summary(dataset_id=dataset_id)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve clustering summary: {str(err)}",
        )


@router.get(
    "/{dataset_id}/entities",
    response_model=List[WalletClusterItem],
)
async def get_clustered_entities_endpoint(
    dataset_id: str,
    cluster_id: Optional[int] = Query(None, description="Filter by specific cluster ID"),
    noise_only: bool = Query(False, description="Filter for only unclustered noise points (label -1)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of entities to return"),
) -> List[WalletClusterItem]:
    """Retrieve clustered wallet entities with optional filtering by cluster ID or noise status."""
    try:
        return clustering.get_clustered_entities(
            dataset_id=dataset_id,
            cluster_id=cluster_id,
            noise_only=noise_only,
            limit=limit,
        )
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve clustered entities: {str(err)}",
        )


@router.get(
    "/{dataset_id}/metadata",
    response_model=ClusteringMetadata,
)
async def get_clustering_metadata_endpoint(dataset_id: str) -> ClusteringMetadata:
    """Retrieve DBSCAN clustering hyperparameter configuration and cluster profiles."""
    try:
        return clustering.get_clustering_metadata(dataset_id=dataset_id)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve clustering metadata: {str(err)}",
        )
