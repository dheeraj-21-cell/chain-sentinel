import React, { useState, useEffect, useCallback } from 'react';
import {
  EvidenceArtifactInfo,
  EvidenceVerificationResult,
  EvidencePackageRequest,
  ForensicReportRequest,
  IngestionMetadata,
  listEvidenceArtifacts,
  generateEvidencePackage,
  generateForensicReport,
  verifyEvidenceArtifact,
  getEvidenceArtifactDownloadUrl,
  fetchEvidencePackageContent,
} from '../services/api';
import { CopyButton } from '../components/CopyButton';

interface EvidenceReportsViewProps {
  datasetId: string;
  datasetMeta: IngestionMetadata | null;
}

export const EvidenceReportsView: React.FC<EvidenceReportsViewProps> = ({
  datasetId,
  datasetMeta,
}) => {
  const [artifacts, setArtifacts] = useState<EvidenceArtifactInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState<'package' | 'report' | null>(null);
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [verificationMap, setVerificationMap] = useState<Record<string, EvidenceVerificationResult>>({});
  
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<'ALL' | 'evidence_package' | 'forensic_report_pdf'>('ALL');

  // Custom Context Modal / Form State
  const [showContextModal, setShowContextModal] = useState(false);
  const [modalMode, setModalMode] = useState<'package' | 'report'>('report');
  const [caseRef, setCaseRef] = useState('');
  const [investigator, setInvestigator] = useState('');
  const [organization, setOrganization] = useState('');
  const [caseNotes, setCaseNotes] = useState('');
  const [caseHypothesis, setCaseHypothesis] = useState('');
  const [txLimit, setTxLimit] = useState(50);

  // Inspect JSON Modal State
  const [inspectArtifact, setInspectArtifact] = useState<EvidenceArtifactInfo | null>(null);
  const [inspectData, setInspectData] = useState<Record<string, unknown> | null>(null);
  const [isLoadingInspect, setIsLoadingInspect] = useState(false);
  const [inspectTab, setInspectTab] = useState<'overview' | 'observed' | 'algorithmic' | 'raw'>('overview');

  const fetchArtifacts = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await listEvidenceArtifacts(datasetId);
      setArtifacts(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to load evidence artifacts.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [datasetId]);

  useEffect(() => {
    fetchArtifacts();
  }, [fetchArtifacts]);

  const handleQuickGenerateReport = async () => {
    setIsGenerating('report');
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const req: ForensicReportRequest = {
        case_reference: caseRef || `CASE-${datasetId.slice(0, 8).toUpperCase()}`,
        investigator_name: investigator || 'Digital Forensics Analyst',
        organization: organization || 'Blockchain Financial Intelligence Lab',
        notes: caseNotes || undefined,
        hypothesis: caseHypothesis || undefined,
      };
      const res = await generateForensicReport(datasetId, req);
      setSuccessMessage(`Forensic PDF report generated: ${res.filename} (SHA-256: ${res.sha256_hash.slice(0, 16)}...)`);
      await fetchArtifacts();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Forensic report generation failed.');
      }
    } finally {
      setIsGenerating(null);
    }
  };

  const handleQuickGeneratePackage = async () => {
    setIsGenerating('package');
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const req: EvidencePackageRequest = {
        case_reference: caseRef || `CASE-${datasetId.slice(0, 8).toUpperCase()}`,
        investigator_name: investigator || 'Digital Forensics Analyst',
        notes: caseNotes || undefined,
        hypothesis: caseHypothesis || undefined,
        include_transactions_limit: txLimit,
      };
      const res = await generateEvidencePackage(datasetId, req);
      setSuccessMessage(`Evidence JSON package generated: ${res.filename} (SHA-256: ${res.sha256_hash.slice(0, 16)}...)`);
      await fetchArtifacts();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Evidence package generation failed.');
      }
    } finally {
      setIsGenerating(null);
    }
  };

  const handleCustomSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setShowContextModal(false);
    if (modalMode === 'report') {
      await handleQuickGenerateReport();
    } else {
      await handleQuickGeneratePackage();
    }
  };

  const handleVerify = async (artifactId: string) => {
    setVerifyingId(artifactId);
    setErrorMessage(null);
    try {
      const result = await verifyEvidenceArtifact(datasetId, artifactId);
      setVerificationMap((prev) => ({ ...prev, [artifactId]: result }));
      setArtifacts((prev) =>
        prev.map((a) => (a.artifact_id === artifactId ? { ...a, verification_status: result.status } : a))
      );
      if (result.status === 'verified') {
        setSuccessMessage(`Artifact ${result.filename} integrity confirmed: SHA-256 match.`);
      } else if (result.status === 'tampered') {
        setErrorMessage(`CRITICAL INTEGRITY ALERT: ${result.filename} has been modified on disk!`);
      } else {
        setErrorMessage(`INTEGRITY WARNING: ${result.filename} was not found on disk.`);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Integrity verification failed.');
      }
    } finally {
      setVerifyingId(null);
    }
  };

  const handleOpenInspect = async (art: EvidenceArtifactInfo) => {
    setInspectArtifact(art);
    setInspectTab('overview');
    setIsLoadingInspect(true);
    setInspectData(null);
    try {
      const data = await fetchEvidencePackageContent(datasetId, art.artifact_id);
      setInspectData(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to load evidence JSON.');
      }
    } finally {
      setIsLoadingInspect(false);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const filteredArtifacts = artifacts.filter((a) => {
    if (filterType === 'ALL') return true;
    return a.artifact_type === filterType;
  });

  return (
    <div>
      {/* Header */}
      <div className="view-header">
        <div>
          <h1 className="view-title">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <path d="m9 15 2 2 4-4"></path>
            </svg>
            Evidence Integrity & Forensic Reporting
          </h1>
          <p className="view-subtitle">
            Tamper-evident forensic intelligence packaging and publication-grade PDF reporting with SHA-256 cryptographic provenance.
          </p>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            className="btn-primary"
            onClick={handleQuickGenerateReport}
            disabled={isGenerating !== null}
            title="Generate a multi-section PDF investigation report"
            style={{
              background: 'linear-gradient(135deg, #1d4ed8, #0284c7)',
              border: '1px solid #38bdf888',
            }}
          >
            {isGenerating === 'report' ? (
              <>
                <span className="status-dot online pulse" style={{ width: 8, height: 8 }} />
                Compiling PDF...
              </>
            ) : (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
                Generate Forensic Report (PDF)
              </>
            )}
          </button>

          <button
            className="btn-secondary"
            onClick={handleQuickGeneratePackage}
            disabled={isGenerating !== null}
            title="Generate a dataset-scoped JSON evidence package with SHA-256 fingerprint"
          >
            {isGenerating === 'package' ? (
              <>
                <span className="status-dot online pulse" style={{ width: 8, height: 8 }} />
                Packaging JSON...
              </>
            ) : (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="16 16 12 12 8 16"></polyline>
                  <line x1="12" y1="12" x2="12" y2="21"></line>
                  <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"></path>
                  <polyline points="16 16 12 12 8 16"></polyline>
                </svg>
                Generate Evidence Package (JSON)
              </>
            )}
          </button>

          <button
            className="btn-secondary"
            onClick={() => setShowContextModal(true)}
            title="Add case reference, investigator details, or hypothesis"
            style={{ fontSize: '0.75rem', padding: '0.45rem 0.65rem' }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
            Case Metadata...
          </button>
        </div>
      </div>

      {/* Case Provenance & System Posture Banner */}
      <div
        className="card"
        style={{
          marginBottom: '1.25rem',
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(14, 116, 144, 0.15))',
          border: '1px solid rgba(56, 189, 248, 0.3)',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          padding: '1rem 1.25rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '8px',
              background: 'rgba(56, 189, 248, 0.12)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid rgba(56, 189, 248, 0.3)',
            }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
            </svg>
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#f8fafc' }}>
                Active Case: {caseRef || `CASE-${datasetId.slice(0, 8).toUpperCase()}`}
              </span>
              <span className="badge badge-cyan" style={{ fontSize: '0.65rem' }}>
                Dataset: {datasetId.slice(0, 8)}
              </span>
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              <span>Source: <strong style={{ color: '#e2e8f0' }}>{datasetMeta?.original_filename || 'dataset.csv'}</strong></span>
              <span>Total Ingested: <strong style={{ color: '#e2e8f0' }}>{datasetMeta?.records_total?.toLocaleString() ?? '—'}</strong></span>
              <span>Valid Records: <strong style={{ color: '#34d399' }}>{datasetMeta?.records_valid?.toLocaleString() ?? '—'}</strong></span>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              background: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              padding: '0.35rem 0.65rem',
              borderRadius: '6px',
              fontSize: '0.72rem',
              color: '#34d399',
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
            </svg>
            <span>Air-Gapped SHA-256 Engine</span>
          </div>
          <button
            className="btn-secondary"
            onClick={fetchArtifacts}
            disabled={isLoading}
            style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}
            title="Refresh artifacts list"
          >
            <svg
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className={isLoading ? 'pulse' : ''}
            >
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Notifications */}
      {errorMessage && (
        <div
          style={{
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid #ef4444',
            color: '#fca5a5',
            padding: '0.75rem 1rem',
            borderRadius: '6px',
            marginBottom: '1rem',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <span>{errorMessage}</span>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            style={{ background: 'transparent', border: 'none', color: '#fca5a5', cursor: 'pointer' }}
          >
            &times;
          </button>
        </div>
      )}

      {successMessage && (
        <div
          style={{
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid #10b981',
            color: '#6ee7b7',
            padding: '0.75rem 1rem',
            borderRadius: '6px',
            marginBottom: '1rem',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span>{successMessage}</span>
          </div>
          <button
            onClick={() => setSuccessMessage(null)}
            style={{ background: 'transparent', border: 'none', color: '#6ee7b7', cursor: 'pointer' }}
          >
            &times;
          </button>
        </div>
      )}

      {/* Artifacts Filter Bar & Count */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8', marginRight: '0.3rem' }}>Filter Type:</span>
          {(['ALL', 'forensic_report_pdf', 'evidence_package'] as const).map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={filterType === type ? 'btn-primary' : 'btn-secondary'}
              style={{ fontSize: '0.72rem', padding: '0.3rem 0.6rem' }}
            >
              {type === 'ALL' ? 'All Artifacts' : type === 'forensic_report_pdf' ? 'PDF Reports' : 'JSON Packages'}
            </button>
          ))}
        </div>
        <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
          Showing <strong>{filteredArtifacts.length}</strong> of <strong>{artifacts.length}</strong> recorded artifacts
        </span>
      </div>

      {/* Artifacts Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: '1.5rem' }}>
        <div style={{ overflowX: 'auto' }}>
          <table className="table" style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'rgba(15, 23, 42, 0.8)', borderBottom: '1px solid #1e293b' }}>
                <th style={{ textAlign: 'left', padding: '0.75rem 1rem', fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>
                  Artifact / Filename
                </th>
                <th style={{ textAlign: 'left', padding: '0.75rem 0.75rem', fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>
                  Type
                </th>
                <th style={{ textAlign: 'left', padding: '0.75rem 0.75rem', fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>
                  Generated (UTC)
                </th>
                <th style={{ textAlign: 'left', padding: '0.75rem 0.75rem', fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>
                  Size
                </th>
                <th style={{ textAlign: 'left', padding: '0.75rem 0.75rem', fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>
                  SHA-256 Fingerprint
                </th>
                <th style={{ textAlign: 'left', padding: '0.75rem 0.75rem', fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>
                  Integrity Status
                </th>
                <th style={{ textAlign: 'right', padding: '0.75rem 1rem', fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredArtifacts.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '3rem 1rem', color: '#64748b' }}>
                    {isLoading ? (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
                        <span className="status-dot online pulse" />
                        <span>Loading evidence manifest...</span>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="1.5">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                          <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                        <span>No forensic artifacts generated for this dataset yet.</span>
                        <div style={{ display: 'flex', gap: '0.6rem' }}>
                          <button className="btn-primary" onClick={handleQuickGenerateReport} style={{ fontSize: '0.78rem' }}>
                            Generate First PDF Report
                          </button>
                          <button className="btn-secondary" onClick={handleQuickGeneratePackage} style={{ fontSize: '0.78rem' }}>
                            Generate Evidence Package
                          </button>
                        </div>
                      </div>
                    )}
                  </td>
                </tr>
              ) : (
                filteredArtifacts.map((art) => {
                  const isPdf = art.artifact_type === 'forensic_report_pdf';
                  const isVerifying = verifyingId === art.artifact_id;
                  const verResult = verificationMap[art.artifact_id];
                  const currentStatus = verResult?.status || art.verification_status;

                  return (
                    <tr key={art.artifact_id} style={{ borderBottom: '1px solid #1e293b' }}>
                      {/* Name & ID */}
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                          {isPdf ? (
                            <div
                              style={{
                                width: '28px',
                                height: '28px',
                                borderRadius: '4px',
                                background: 'rgba(239, 68, 68, 0.15)',
                                color: '#f87171',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                flexShrink: 0,
                              }}
                            >
                              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                <polyline points="14 2 14 8 20 8"></polyline>
                              </svg>
                            </div>
                          ) : (
                            <div
                              style={{
                                width: '28px',
                                height: '28px',
                                borderRadius: '4px',
                                background: 'rgba(56, 189, 248, 0.15)',
                                color: '#38bdf8',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                flexShrink: 0,
                              }}
                            >
                              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <polyline points="16 16 12 12 8 16"></polyline>
                                <line x1="12" y1="12" x2="12" y2="21"></line>
                                <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"></path>
                              </svg>
                            </div>
                          )}
                          <div>
                            <div style={{ fontWeight: 600, fontSize: '0.82rem', color: '#f1f5f9' }}>
                              {art.filename}
                            </div>
                            <div className="mono" style={{ fontSize: '0.68rem', color: '#64748b' }}>
                              {art.artifact_id}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Type */}
                      <td style={{ padding: '0.75rem 0.75rem' }}>
                        {isPdf ? (
                          <span className="badge badge-high" style={{ fontSize: '0.65rem' }}>
                            PDF REPORT
                          </span>
                        ) : (
                          <span className="badge badge-cyan" style={{ fontSize: '0.65rem' }}>
                            JSON PACKAGE
                          </span>
                        )}
                      </td>

                      {/* Generated UTC */}
                      <td style={{ padding: '0.75rem 0.75rem', fontSize: '0.75rem', color: '#94a3b8' }}>
                        {new Date(art.created_at).toLocaleString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                          timeZoneName: 'short',
                        })}
                      </td>

                      {/* Size */}
                      <td style={{ padding: '0.75rem 0.75rem', fontSize: '0.75rem', color: '#cbd5e1' }}>
                        {formatBytes(art.file_size_bytes)}
                      </td>

                      {/* Hash */}
                      <td style={{ padding: '0.75rem 0.75rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span
                            className="mono"
                            title={art.sha256_hash}
                            style={{
                              fontSize: '0.72rem',
                              color: '#38bdf8',
                              background: 'rgba(15, 23, 42, 0.8)',
                              padding: '0.15rem 0.4rem',
                              borderRadius: '4px',
                              border: '1px solid #1e293b',
                            }}
                          >
                            {art.sha256_hash.slice(0, 10)}...{art.sha256_hash.slice(-8)}
                          </span>
                          <CopyButton text={art.sha256_hash} title="Copy full SHA-256" />
                        </div>
                      </td>

                      {/* Integrity Status */}
                      <td style={{ padding: '0.75rem 0.75rem' }}>
                        {currentStatus === 'verified' && (
                          <span className="badge badge-low" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                            </svg>
                            VERIFIED
                          </span>
                        )}
                        {currentStatus === 'tampered' && (
                          <span className="badge badge-critical" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                              <circle cx="12" cy="12" r="10"></circle>
                              <line x1="12" y1="8" x2="12" y2="12"></line>
                              <line x1="12" y1="16" x2="12.01" y2="16"></line>
                            </svg>
                            TAMPERED
                          </span>
                        )}
                        {currentStatus === 'missing' && (
                          <span className="badge badge-moderate" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                              <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon>
                            </svg>
                            MISSING
                          </span>
                        )}
                        {(!currentStatus || currentStatus === 'unverified') && (
                          <span className="badge badge-neutral">UNVERIFIED</span>
                        )}
                      </td>

                      {/* Actions */}
                      <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: '0.35rem', alignItems: 'center' }}>
                          <button
                            className="btn-secondary"
                            onClick={() => handleVerify(art.artifact_id)}
                            disabled={isVerifying}
                            style={{ fontSize: '0.72rem', padding: '0.25rem 0.5rem' }}
                            title="Recompute SHA-256 hash on disk to confirm zero tampering"
                          >
                            {isVerifying ? (
                              'Hashing...'
                            ) : (
                              <>
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                                </svg>
                                Verify
                              </>
                            )}
                          </button>

                          <a
                            href={getEvidenceArtifactDownloadUrl(datasetId, art.artifact_id)}
                            download={art.filename}
                            className="btn-secondary"
                            style={{ fontSize: '0.72rem', padding: '0.25rem 0.5rem', textDecoration: 'none' }}
                            title="Download artifact directly"
                          >
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                              <polyline points="7 10 12 15 17 10"></polyline>
                              <line x1="12" y1="15" x2="12" y2="3"></line>
                            </svg>
                            Export
                          </a>

                          {!isPdf && (
                            <button
                              className="btn-secondary"
                              onClick={() => handleOpenInspect(art)}
                              style={{ fontSize: '0.72rem', padding: '0.25rem 0.5rem' }}
                              title="Inspect structured observed facts and algorithmic findings"
                            >
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="11" cy="11" r="8"></circle>
                                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                              </svg>
                              Inspect
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Forensic Standard & Neutrality Disclosure */}
      <div
        className="card"
        style={{
          border: '1px solid rgba(100, 116, 139, 0.25)',
          background: '#090d16',
          padding: '1.25rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="16" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12.01" y2="8"></line>
          </svg>
          <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#e2e8f0', letterSpacing: '0.04em' }}>
            FORENSIC METHODOLOGY & EVIDENTIARY STANDARDS
          </span>
        </div>
        <p style={{ fontSize: '0.78rem', color: '#94a3b8', lineHeight: 1.55, margin: 0 }}>
          All outputs generated by this platform strictly preserve the separation between <strong>Observed Blockchain Records</strong> (immutable facts from the active dataset), <strong>Algorithmic Indicators</strong> (Isolation Forest, DBSCAN, heuristic detection), and <strong>Investigator Hypotheses</strong>. Every exported PDF report and JSON package is cryptographically fingerprinted using SHA-256 at creation time. Hash verification performs live disk reading to guarantee tamper detection across offline archival environments without external network egress.
        </p>
      </div>

      {/* Custom Context / Metadata Modal */}
      {showContextModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '1rem',
          }}
        >
          <div
            className="card"
            style={{
              width: '100%',
              maxWidth: '540px',
              background: '#0f172a',
              border: '1px solid #334155',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
              padding: '1.5rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                  Forensic Report Metadata
                </h2>
              </div>
              <button
                onClick={() => setShowContextModal(false)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '1.2rem' }}
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleCustomSubmit}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', color: '#cbd5e1', marginBottom: '0.35rem', fontWeight: 600 }}>
                  Export Format
                </label>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    type="button"
                    onClick={() => setModalMode('report')}
                    className={modalMode === 'report' ? 'btn-primary' : 'btn-secondary'}
                    style={{ flex: 1, fontSize: '0.75rem', justifyContent: 'center' }}
                  >
                    Forensic PDF Report
                  </button>
                  <button
                    type="button"
                    onClick={() => setModalMode('package')}
                    className={modalMode === 'package' ? 'btn-primary' : 'btn-secondary'}
                    style={{ flex: 1, fontSize: '0.75rem', justifyContent: 'center' }}
                  >
                    Evidence Package (JSON)
                  </button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '0.85rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
                    Case Reference ID
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. CASE-2026-BTC-001"
                    value={caseRef}
                    onChange={(e) => setCaseRef(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.45rem 0.65rem',
                      background: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '4px',
                      color: '#f8fafc',
                      fontSize: '0.8rem',
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
                    Investigator Name / Badge
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Special Agent Smith"
                    value={investigator}
                    onChange={(e) => setInvestigator(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.45rem 0.65rem',
                      background: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '4px',
                      color: '#f8fafc',
                      fontSize: '0.8rem',
                    }}
                  />
                </div>
              </div>

              <div style={{ marginBottom: '0.85rem' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
                  Agency / Organization
                </label>
                <input
                  type="text"
                  placeholder="e.g. National Cyber Forensics Lab"
                  value={organization}
                  onChange={(e) => setOrganization(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.45rem 0.65rem',
                    background: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '4px',
                    color: '#f8fafc',
                    fontSize: '0.8rem',
                  }}
                />
              </div>

              <div style={{ marginBottom: '0.85rem' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
                  Investigator Case Notes
                </label>
                <textarea
                  placeholder="Observed transaction velocity, clustering observations, and investigative context..."
                  rows={2}
                  value={caseNotes}
                  onChange={(e) => setCaseNotes(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.45rem 0.65rem',
                    background: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '4px',
                    color: '#f8fafc',
                    fontSize: '0.8rem',
                    resize: 'vertical',
                  }}
                />
              </div>

              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
                  Working Hypothesis (Clearly Demarcated)
                </label>
                <textarea
                  placeholder="Working hypothesis regarding entity grouping and fund flow trajectory..."
                  rows={2}
                  value={caseHypothesis}
                  onChange={(e) => setCaseHypothesis(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.45rem 0.65rem',
                    background: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '4px',
                    color: '#f8fafc',
                    fontSize: '0.8rem',
                    resize: 'vertical',
                  }}
                />
              </div>

              {modalMode === 'package' && (
                <div style={{ marginBottom: '1.25rem' }}>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.25rem' }}>
                    Sample Transactions Included: <strong>{txLimit}</strong>
                  </label>
                  <input
                    type="range"
                    min={10}
                    max={200}
                    step={10}
                    value={txLimit}
                    onChange={(e) => setTxLimit(Number(e.target.value))}
                    style={{ width: '100%' }}
                  />
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.6rem' }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowContextModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                >
                  Generate {modalMode === 'report' ? 'PDF Report' : 'JSON Package'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Inspect JSON Package Modal */}
      {inspectArtifact && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(5px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
            padding: '1.5rem',
          }}
        >
          <div
            className="card"
            style={{
              width: '100%',
              maxWidth: '900px',
              height: '85vh',
              background: '#0a0f1d',
              border: '1px solid #38bdf844',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
              display: 'flex',
              flexDirection: 'column',
              padding: 0,
              overflow: 'hidden',
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                padding: '1rem 1.5rem',
                background: '#0f172a',
                borderBottom: '1px solid #1e293b',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <span className="badge badge-cyan" style={{ fontSize: '0.65rem' }}>EVIDENCE PACKAGE</span>
                  <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                    {inspectArtifact.filename}
                  </h2>
                </div>
                <div className="mono" style={{ fontSize: '0.72rem', color: '#38bdf8', marginTop: '3px' }}>
                  SHA-256: {inspectArtifact.sha256_hash}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
                <CopyButton text={inspectArtifact.sha256_hash} title="Copy SHA-256" />
                <a
                  href={getEvidenceArtifactDownloadUrl(datasetId, inspectArtifact.artifact_id)}
                  download={inspectArtifact.filename}
                  className="btn-primary"
                  style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem', textDecoration: 'none' }}
                >
                  Download JSON
                </a>
                <button
                  onClick={() => setInspectArtifact(null)}
                  style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '1.3rem' }}
                >
                  &times;
                </button>
              </div>
            </div>

            {/* Modal Tabs */}
            <div
              style={{
                display: 'flex',
                borderBottom: '1px solid #1e293b',
                background: '#0f172a',
                padding: '0 1rem',
              }}
            >
              {(['overview', 'observed', 'algorithmic', 'raw'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setInspectTab(tab)}
                  style={{
                    padding: '0.65rem 1rem',
                    background: 'transparent',
                    border: 'none',
                    borderBottom: inspectTab === tab ? '2px solid #38bdf8' : '2px solid transparent',
                    color: inspectTab === tab ? '#38bdf8' : '#94a3b8',
                    fontWeight: inspectTab === tab ? 600 : 400,
                    fontSize: '0.8rem',
                    cursor: 'pointer',
                    textTransform: 'capitalize',
                  }}
                >
                  {tab === 'raw' ? 'Raw JSON' : tab}
                </button>
              ))}
            </div>

            {/* Modal Content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem' }}>
              {isLoadingInspect ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
                  <span className="status-dot online pulse" />
                  <p style={{ marginTop: '0.5rem' }}>Loading and parsing evidence package...</p>
                </div>
              ) : !inspectData ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: '#ef4444' }}>
                  Unable to load package contents.
                </div>
              ) : (
                <>
                  {inspectTab === 'overview' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      <div className="card" style={{ background: '#111827', padding: '1rem' }}>
                        <h3 style={{ fontSize: '0.85rem', color: '#38bdf8', marginBottom: '0.5rem', fontWeight: 600 }}>
                          Cryptographic Provenance
                        </h3>
                        <pre className="mono" style={{ fontSize: '0.75rem', color: '#cbd5e1', whiteSpace: 'pre-wrap' }}>
                          {JSON.stringify(inspectData.provenance || {}, null, 2)}
                        </pre>
                      </div>

                      <div className="card" style={{ background: '#111827', padding: '1rem' }}>
                        <h3 style={{ fontSize: '0.85rem', color: '#f59e0b', marginBottom: '0.5rem', fontWeight: 600 }}>
                          Investigator Context & Hypotheses
                        </h3>
                        <pre className="mono" style={{ fontSize: '0.75rem', color: '#cbd5e1', whiteSpace: 'pre-wrap' }}>
                          {JSON.stringify(inspectData.investigator_context || {}, null, 2)}
                        </pre>
                      </div>

                      <div className="card" style={{ background: '#111827', padding: '1rem' }}>
                        <h3 style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '0.5rem', fontWeight: 600 }}>
                          Forensic Classification & Limitations
                        </h3>
                        <pre className="mono" style={{ fontSize: '0.75rem', color: '#cbd5e1', whiteSpace: 'pre-wrap' }}>
                          {JSON.stringify(inspectData.forensic_classification || {}, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}

                  {inspectTab === 'observed' && (
                    <div className="card" style={{ background: '#111827', padding: '1rem' }}>
                      <h3 style={{ fontSize: '0.85rem', color: '#34d399', marginBottom: '0.5rem', fontWeight: 600 }}>
                        Observed Blockchain Facts (Dataset Records)
                      </h3>
                      <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.75rem' }}>
                        Direct factual measurements recorded in the dataset without algorithmic interpolation.
                      </p>
                      <pre className="mono" style={{ fontSize: '0.75rem', color: '#cbd5e1', whiteSpace: 'pre-wrap', maxHeight: '500px', overflowY: 'auto' }}>
                        {JSON.stringify(inspectData.observed_facts || {}, null, 2)}
                      </pre>
                    </div>
                  )}

                  {inspectTab === 'algorithmic' && (
                    <div className="card" style={{ background: '#111827', padding: '1rem' }}>
                      <h3 style={{ fontSize: '0.85rem', color: '#a855f7', marginBottom: '0.5rem', fontWeight: 600 }}>
                        Algorithmic Model Findings
                      </h3>
                      <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.75rem' }}>
                        Multi-pipeline outputs: Neo4j/NetworkX topology, Isolation Forest anomalies, DBSCAN clusters, heuristic indicators, and prioritized risk scores.
                      </p>
                      <pre className="mono" style={{ fontSize: '0.75rem', color: '#cbd5e1', whiteSpace: 'pre-wrap', maxHeight: '500px', overflowY: 'auto' }}>
                        {JSON.stringify(inspectData.algorithmic_findings || {}, null, 2)}
                      </pre>
                    </div>
                  )}

                  {inspectTab === 'raw' && (
                    <pre
                      className="mono"
                      style={{
                        fontSize: '0.75rem',
                        color: '#38bdf8',
                        background: '#070b14',
                        padding: '1rem',
                        borderRadius: '6px',
                        border: '1px solid #1e293b',
                        whiteSpace: 'pre-wrap',
                        maxHeight: '600px',
                        overflowY: 'auto',
                      }}
                    >
                      {JSON.stringify(inspectData, null, 2)}
                    </pre>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
