from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models.evidence import (
    EvidenceArtifactInfo,
    EvidencePackageRequest,
    EvidenceVerificationResult,
    ForensicReportRequest,
)
from app.services import evidence

router = APIRouter(prefix="/api/v1/evidence", tags=["Evidence & Forensic Reporting"])


@router.post("/{dataset_id}/package", response_model=EvidenceArtifactInfo)
def create_package(
    dataset_id: str,
    request: Optional[EvidencePackageRequest] = None,
) -> EvidenceArtifactInfo:
    """Generate a structured, dataset-scoped JSON Evidence Package with SHA-256 fingerprint."""
    try:
        return evidence.generate_evidence_package(dataset_id, request)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evidence package generation failed: {str(e)}")


@router.post("/{dataset_id}/report", response_model=EvidenceArtifactInfo)
def create_report(
    dataset_id: str,
    request: Optional[ForensicReportRequest] = None,
) -> EvidenceArtifactInfo:
    """Generate a publication-grade PDF Forensic Investigation Report using ReportLab."""
    try:
        return evidence.generate_forensic_report_pdf(dataset_id, request)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forensic report generation failed: {str(e)}")


@router.get("/{dataset_id}/artifacts", response_model=List[EvidenceArtifactInfo])
def list_artifacts(dataset_id: str) -> List[EvidenceArtifactInfo]:
    """Retrieve all generated evidence artifacts and forensic reports for a dataset."""
    try:
        return evidence.list_dataset_artifacts(dataset_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list evidence artifacts: {str(e)}")


@router.get("/{dataset_id}/artifacts/{artifact_id}/verify", response_model=EvidenceVerificationResult)
def verify_artifact(dataset_id: str, artifact_id: str) -> EvidenceVerificationResult:
    """Recompute SHA-256 hash of an artifact on disk and verify cryptographic integrity."""
    try:
        return evidence.verify_artifact_integrity(dataset_id, artifact_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Integrity verification failed: {str(e)}")


@router.get("/{dataset_id}/artifacts/{artifact_id}/download")
def download_artifact(dataset_id: str, artifact_id: str) -> FileResponse:
    """Download an exported evidence artifact (JSON or PDF) with verified provenance headers."""
    try:
        file_path, filename, media_type = evidence.get_artifact_file(dataset_id, artifact_id)
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Forensic-Dataset-ID": dataset_id,
                "X-Forensic-Artifact-ID": artifact_id,
            },
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Artifact download failed: {str(e)}")
