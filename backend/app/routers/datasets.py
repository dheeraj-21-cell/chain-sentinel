from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.models.dataset import (
    DatasetIngestionResponse,
    IngestionMetadata,
    RejectedRecord,
)
from app.models.transaction import NormalizedTransaction
from app.services.graph import delete_graph_for_dataset
from app.services.normalizer import normalize_and_validate_record
from app.services.parsers import parse_csv, parse_json, parse_xml
from app.services.storage import (
    delete_dataset_storage,
    find_dataset_by_content_hash,
    list_all_metadata,
    load_metadata,
    load_rejected_records,
    save_metadata,
    save_normalized_parquet,
    save_raw_file,
    save_rejected_records,
)

router = APIRouter(prefix="/api/v1/datasets", tags=["Datasets"])


@router.post("/ingest", response_model=DatasetIngestionResponse, status_code=status.HTTP_201_CREATED)
async def ingest_dataset(
    file: UploadFile = File(...),
    force: bool = Query(False, description="Force re-ingestion even if identical content was previously ingested"),
) -> DatasetIngestionResponse:
    """Accept multipart file upload (CSV, JSON, XML) and ingest/normalize records."""
    filename = file.filename or "unknown_dataset"
    ext = Path(filename).suffix.lower()

    if ext == ".csv":
        file_type = "csv"
    elif ext == ".json":
        file_type = "json"
    elif ext == ".xml":
        file_type = "xml"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported formats are: .csv, .json, .xml",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    content_sha256 = hashlib.sha256(content).hexdigest()

    # Prevent duplicate dataset registration if identical content already exists
    if not force:
        existing = find_dataset_by_content_hash(content_sha256)
        if existing:
            return DatasetIngestionResponse(
                dataset_id=existing.dataset_id,
                filename=existing.original_filename,
                status=existing.validation_status,
                records_total=existing.records_total,
                records_valid=existing.records_valid,
                records_rejected=existing.records_rejected,
                normalized_output_path=existing.normalized_output_path,
                error_report_path=existing.error_report_path,
                content_sha256=existing.content_sha256,
            )

    dataset_id = str(uuid.uuid4())
    raw_path = save_raw_file(dataset_id, filename, content)
    ingest_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Parse records based on type
    try:
        if file_type == "csv":
            raw_records = parse_csv(content)
        elif file_type == "json":
            raw_records = parse_json(content)
        elif file_type == "xml":
            raw_records = parse_xml(content)
        else:
            raw_records = []
    except ValueError as err:
        # File syntax itself was invalid
        metadata = IngestionMetadata(
            dataset_id=dataset_id,
            original_filename=filename,
            file_type=file_type,
            ingestion_timestamp=ingest_time,
            records_total=0,
            records_valid=0,
            records_rejected=0,
            validation_status="FAILED",
            raw_file_path=raw_path,
            normalized_output_path=None,
            error_report_path=None,
        )
        save_metadata(metadata)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse {file_type.upper()} file structure: {str(err)}",
        )

    valid_records: List[NormalizedTransaction] = []
    rejected_records: List[RejectedRecord] = []

    for idx, raw_record in enumerate(raw_records):
        norm_tx, rejected = normalize_and_validate_record(idx, raw_record, dataset_id)
        if norm_tx is not None:
            valid_records.append(norm_tx)
        elif rejected is not None:
            rejected_records.append(rejected)

    total_count = len(raw_records)
    valid_count = len(valid_records)
    rejected_count = len(rejected_records)

    # Determine validation status
    if total_count == 0:
        val_status = "FAILED"
    elif rejected_count == 0:
        val_status = "SUCCESS"
    elif valid_count > 0:
        val_status = "PARTIAL"
    else:
        val_status = "FAILED"

    parquet_path = save_normalized_parquet(dataset_id, valid_records)
    error_path = save_rejected_records(dataset_id, rejected_records)

    metadata = IngestionMetadata(
        dataset_id=dataset_id,
        original_filename=filename,
        file_type=file_type,
        ingestion_timestamp=ingest_time,
        records_total=total_count,
        records_valid=valid_count,
        records_rejected=rejected_count,
        validation_status=val_status,
        raw_file_path=raw_path,
        normalized_output_path=parquet_path,
        error_report_path=error_path,
        content_sha256=content_sha256,
    )
    save_metadata(metadata)

    return DatasetIngestionResponse(
        dataset_id=dataset_id,
        filename=filename,
        status=val_status,
        records_total=total_count,
        records_valid=valid_count,
        records_rejected=rejected_count,
        normalized_output_path=parquet_path,
        error_report_path=error_path,
        content_sha256=content_sha256,
    )


@router.get("", response_model=List[IngestionMetadata])
async def list_datasets(
    include_invalid: bool = Query(False, description="Include failed / 0-valid-record datasets")
) -> List[IngestionMetadata]:
    """List all ingested datasets and their validation statuses."""
    return list_all_metadata(include_invalid=include_invalid)


@router.get("/{dataset_id}", response_model=IngestionMetadata)
async def get_dataset(dataset_id: str) -> IngestionMetadata:
    """Retrieve metadata for a specific dataset by its ID."""
    metadata = load_metadata(dataset_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID '{dataset_id}' not found.",
        )
    return metadata


@router.delete("/{dataset_id}", status_code=status.HTTP_200_OK)
async def delete_dataset(dataset_id: str) -> Dict[str, Any]:
    """Delete a dataset and cleanly remove all associated storage and Neo4j graph elements."""
    metadata = load_metadata(dataset_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID '{dataset_id}' not found.",
        )

    # Clean Neo4j graph
    graph_cleanup = delete_graph_for_dataset(dataset_id)

    # Clean filesystem storage
    storage_deleted = delete_dataset_storage(dataset_id)

    return {
        "dataset_id": dataset_id,
        "status": "SUCCESS",
        "message": f"Dataset '{metadata.original_filename}' ({dataset_id}) deleted successfully.",
        "graph_cleanup": graph_cleanup,
        "storage_deleted": storage_deleted,
    }


@router.get("/{dataset_id}/errors", response_model=List[RejectedRecord])
async def get_dataset_errors(dataset_id: str) -> List[RejectedRecord]:
    """Retrieve rejected records and specific validation errors for a dataset."""
    metadata = load_metadata(dataset_id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID '{dataset_id}' not found.",
        )
    return load_rejected_records(dataset_id)
