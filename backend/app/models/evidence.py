from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

EvidenceArtifactType = Literal['evidence_package', 'forensic_report_pdf']
EvidenceVerificationStatus = Literal['verified', 'tampered', 'missing']


class EvidenceArtifactInfo(BaseModel):
    artifact_id: str
    dataset_id: str
    filename: str
    artifact_type: EvidenceArtifactType
    created_at: str
    file_size_bytes: int
    sha256_hash: str
    case_reference: Optional[str] = None
    investigator_name: Optional[str] = None
    description: Optional[str] = None


class EvidenceVerificationResult(BaseModel):
    artifact_id: str
    filename: str
    dataset_id: str
    is_valid: bool
    status: EvidenceVerificationStatus
    expected_sha256: str
    computed_sha256: Optional[str] = None
    verified_at: str
    message: str


class EvidencePackageRequest(BaseModel):
    case_reference: Optional[str] = Field(None, description='Optional internal law-enforcement/case identifier')
    investigator_name: Optional[str] = Field(None, description='Name or badge of the examining investigator')
    notes: Optional[str] = Field(None, description='Investigator case observations or notes')
    hypothesis: Optional[str] = Field(None, description='Investigative working hypothesis')
    include_transactions_limit: int = Field(100, ge=10, le=1000, description='Limit of transaction records to include in sample')


class ForensicReportRequest(BaseModel):
    case_reference: Optional[str] = Field(None, description='Optional case reference number')
    investigator_name: Optional[str] = Field(None, description='Investigator name or badge')
    organization: Optional[str] = Field(None, description='Investigating agency or forensic laboratory name')
    notes: Optional[str] = Field(None, description='Investigative notes to include in the report')
    hypothesis: Optional[str] = Field(None, description='Working hypothesis statement')


class EvidenceManifest(BaseModel):
    dataset_id: str
    updated_at: str
    artifacts: List[EvidenceArtifactInfo] = []


class EvidencePackage(BaseModel):
    artifact_id: str
    dataset_id: str
    artifact_type: str = 'evidence_package'
    generated_at: str
    provenance: Dict[str, Any]
    forensic_classification: Dict[str, str]
    investigator_context: Dict[str, Optional[str]]
    observed_facts: Dict[str, Any]
    algorithmic_findings: Dict[str, Any]
    limitations_and_methodology: List[str]
