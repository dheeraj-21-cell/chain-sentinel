from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.models.graph import (
    GraphBuildResponse,
    GraphElementsResponse,
    GraphSummaryResponse,
)
from app.services import graph

router = APIRouter(prefix="/api/v1/graph", tags=["Graph"])


@router.post("/{dataset_id}/build", response_model=GraphBuildResponse, status_code=status.HTTP_201_CREATED)
async def build_dataset_graph(dataset_id: str) -> GraphBuildResponse:
    """Build or update persistent Neo4j investigation graph strictly for a specific dataset."""
    try:
        return graph.build_graph_for_dataset(dataset_id)
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Neo4j graph construction failed: {str(err)}",
        )


@router.get("/{dataset_id}/summary", response_model=GraphSummaryResponse)
async def get_graph_summary_endpoint(dataset_id: str) -> GraphSummaryResponse:
    """Retrieve live node and relationship counts from Neo4j for a specific dataset."""
    try:
        return graph.get_graph_summary(dataset_id)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query Neo4j graph summary: {str(err)}",
        )


@router.delete("/{dataset_id}", status_code=status.HTTP_200_OK)
async def delete_graph_endpoint(dataset_id: str) -> dict:
    """Clean up and delete all graph nodes and relationships associated with a dataset."""
    try:
        deleted_count = graph.delete_dataset_graph(dataset_id)
        return {"dataset_id": dataset_id, "deleted_nodes": deleted_count, "status": "CLEARED"}
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete Neo4j dataset graph: {str(err)}",
        )


@router.get("/{dataset_id}/elements", response_model=GraphElementsResponse)
async def get_graph_elements_endpoint(
    dataset_id: str,
    limit: int = Query(100, ge=1, le=500, description="Max transaction subgraphs to load"),
    center_node: Optional[str] = Query(None, description="Center entity identifier for focused view"),
    hops: int = Query(1, ge=1, le=3, description="Neighborhood radius if center_node is provided"),
) -> GraphElementsResponse:
    """Retrieve bounded graph nodes and edges for Cytoscape.js with multi-pipeline enrichment."""
    try:
        return graph.get_graph_elements(
            dataset_id=dataset_id,
            limit=limit,
            center_node=center_node,
            hops=hops,
        )
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query graph elements: {str(err)}",
        )


@router.get("/{dataset_id}/neighborhood", response_model=GraphElementsResponse)
async def get_neighborhood_endpoint(
    dataset_id: str,
    node_id: str = Query(..., description="Target entity identifier (address, txid, or ip)"),
    hops: int = Query(1, ge=1, le=3, description="Expansion distance: 1, 2, or 3 hops"),
    limit: int = Query(50, ge=1, le=200, description="Max neighbor records to expand"),
) -> GraphElementsResponse:
    """Expand graph neighborhood 1-3 hops from a specific entity with duplicate prevention."""
    try:
        return graph.get_neighborhood(
            dataset_id=dataset_id,
            node_id=node_id,
            hops=hops,
            limit=limit,
        )
    except FileNotFoundError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Neighborhood expansion failed: {str(err)}",
        )
