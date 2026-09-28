from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RejectedRecord(BaseModel):
    record_index: int = Field(..., description="Index of the row or record in the source file (0-indexed)")
    raw_data: Dict[str, Any] = Field(..., description="Raw input data for the malformed record")
    errors: List[str] = Field(..., description="List of specific validation errors")


class IngestionMetadata(BaseModel):
    dataset_id: str
    original_filename: str
    file_type: str
    ingestion_timestamp: str
    records_total: int
    records_valid: int
    records_rejected: int
    validation_status: str  # SUCCESS, PARTIAL, FAILED
    raw_file_path: str
    normalized_output_path: Optional[str] = None
    error_report_path: Optional[str] = None
    content_sha256: Optional[str] = None


class DatasetIngestionResponse(BaseModel):
    dataset_id: str
    filename: str
    status: str
    records_total: int
    records_valid: int
    records_rejected: int
    normalized_output_path: Optional[str] = None
    error_report_path: Optional[str] = None
    content_sha256: Optional[str] = None
