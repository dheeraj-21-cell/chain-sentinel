import React, { useState } from 'react';
import {
  IngestionMetadata,
  RejectedRecord,
  uploadDataset,
  getDatasetErrors,
  DatasetIngestionResponse,
} from '../services/api';
import { CopyButton } from '../components/CopyButton';

interface DatasetsViewProps {
  datasets: IngestionMetadata[];
  activeDatasetId: string | null;
  onSelectDataset: (datasetId: string) => void;
  onRefreshDatasets: () => Promise<void>;
}

export const DatasetsView: React.FC<DatasetsViewProps> = ({
  datasets,
  activeDatasetId,
  onSelectDataset,
  onRefreshDatasets,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [lastUploadResult, setLastUploadResult] = useState<DatasetIngestionResponse | null>(null);

  // Rejection Inspector State
  const [inspectingDatasetId, setInspectingDatasetId] = useState<string | null>(null);
  const [rejectedRecords, setRejectedRecords] = useState<RejectedRecord[]>([]);
  const [loadingErrors, setLoadingErrors] = useState(false);
  const [showErrorModal, setShowErrorModal] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      setUploadError(null);
      setLastUploadResult(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError('Please choose a file before uploading.');
      return;
    }
    setIsUploading(true);
    setUploadError(null);
    try {
      const result = await uploadDataset(selectedFile);
      setLastUploadResult(result);
      setSelectedFile(null);
      await onRefreshDatasets();
      onSelectDataset(result.dataset_id);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setUploadError(err.message);
      } else {
        setUploadError('Ingestion failed due to an unexpected error.');
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleInspectErrors = async (datasetId: string) => {
    setInspectingDatasetId(datasetId);
    setLoadingErrors(true);
    try {
      const errors = await getDatasetErrors(datasetId);
      setRejectedRecords(errors);
      setShowErrorModal(true);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setUploadError(`Failed to load errors: ${err.message}`);
      }
    } finally {
      setLoadingErrors(false);
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="view-header">
        <div>
          <h1 className="view-title">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2">
              <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
            </svg>
            Dataset Ingestion & Provenance
          </h1>
          <p className="view-subtitle">
            Ingest, validate, and normalize raw Bitcoin transaction and P2P network metadata into columnar Parquet tables.
          </p>
        </div>
      </div>

      {/* Upload & Ingestion Dropzone Card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h3 className="card-title">Upload & Ingest Raw Metadata File</h3>
        <p style={{ color: '#94a3b8', fontSize: '0.82rem', marginTop: 0 }}>
          Accepts raw <strong>CSV</strong>, <strong>JSON</strong>, and <strong>XML</strong> files. Strict validation preserves missing values without fabrication, records schema anomalies into rejection logs, and stores normalized outputs under isolated dataset UUID directories.
        </p>

        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap', marginTop: '1rem' }}>
          <label
            style={{
              background: '#0b111e',
              border: '1px dashed #334155',
              borderRadius: '6px',
              padding: '0.65rem 1.25rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              fontSize: '0.82rem',
              color: '#cbd5e1',
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <span>{selectedFile ? selectedFile.name : 'Choose CSV, JSON, or XML file...'}</span>
            <input
              type="file"
              accept=".csv,.json,.xml"
              onChange={handleFileChange}
              disabled={isUploading}
              style={{ display: 'none' }}
            />
          </label>

          {selectedFile && (
            <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
              ({(selectedFile.size / 1024).toFixed(1)} KB)
            </span>
          )}

          <button
            className="btn-primary"
            onClick={handleUpload}
            disabled={isUploading || !selectedFile}
          >
            {isUploading ? 'Validating & Ingesting...' : 'Ingest & Normalize'}
          </button>
        </div>

        {uploadError && (
          <div style={{ marginTop: '1rem', background: '#3b1010', border: '1px solid #991b1b', color: '#fca5a5', padding: '0.75rem', borderRadius: '6px', fontSize: '0.82rem' }}>
            {uploadError}
          </div>
        )}

        {lastUploadResult && (
          <div style={{ marginTop: '1rem', background: '#091c15', border: '1px solid #059669', padding: '1rem', borderRadius: '6px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <strong style={{ color: '#34d399', fontSize: '0.9rem' }}>
                Ingestion Complete: {lastUploadResult.filename}
              </strong>
              <span className={`badge ${lastUploadResult.status === 'SUCCESS' ? 'badge-low' : lastUploadResult.status === 'PARTIAL' ? 'badge-moderate' : 'badge-high'}`}>
                {lastUploadResult.status}
              </span>
            </div>
            <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.82rem', color: '#cbd5e1', flexWrap: 'wrap' }}>
              <div>Total Parsed: <strong className="mono">{lastUploadResult.records_total}</strong></div>
              <div>Valid Normalized: <strong className="mono" style={{ color: '#34d399' }}>{lastUploadResult.records_valid}</strong></div>
              <div>Rejected: <strong className="mono" style={{ color: lastUploadResult.records_rejected > 0 ? '#f87171' : '#94a3b8' }}>{lastUploadResult.records_rejected}</strong></div>
              <div className="mono" style={{ fontSize: '0.75rem', color: '#94a3b8' }}>UUID: {lastUploadResult.dataset_id}</div>
            </div>
          </div>
        )}
      </div>

      {/* Ingested Datasets Registry */}
      <div className="card">
        <div className="card-title">
          <span>Ingested Datasets Registry ({datasets.length})</span>
          <button className="btn-secondary" onClick={onRefreshDatasets} style={{ fontSize: '0.75rem' }}>
            Refresh Registry
          </button>
        </div>

        {datasets.length === 0 ? (
          <div className="empty-state">
            <div className="empty-title">No Datasets Ingested</div>
            <p className="empty-desc">Upload a raw data file above to register your first Bitcoin intelligence dataset.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="cyber-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Dataset UUID</th>
                  <th>Filename</th>
                  <th>Format</th>
                  <th>Valid Records</th>
                  <th>Rejected</th>
                  <th>Ingested At</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((d) => {
                  const isActive = d.dataset_id === activeDatasetId;
                  return (
                    <tr key={d.dataset_id} style={{ background: isActive ? '#131c2d' : undefined }}>
                      <td>
                        <span className={`badge ${
                          d.validation_status === 'SUCCESS' ? 'badge-low' : d.validation_status === 'PARTIAL' ? 'badge-moderate' : 'badge-high'
                        }`}>
                          {d.validation_status}
                        </span>
                      </td>
                      <td className="mono" style={{ fontSize: '0.78rem' }}>
                        <span style={{ color: isActive ? '#38bdf8' : '#cbd5e1' }}>
                          {d.dataset_id.slice(0, 10)}...
                        </span>
                        <CopyButton text={d.dataset_id} />
                      </td>
                      <td style={{ fontWeight: 600 }}>{d.original_filename}</td>
                      <td>
                        <span className="badge badge-neutral">{d.file_type.toUpperCase()}</span>
                      </td>
                      <td className="mono" style={{ color: '#34d399', fontWeight: 600 }}>
                        {d.records_valid}
                      </td>
                      <td className="mono" style={{ color: d.records_rejected > 0 ? '#f87171' : '#94a3b8' }}>
                        {d.records_rejected}
                      </td>
                      <td style={{ fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                        {d.ingestion_timestamp ? d.ingestion_timestamp.slice(0, 19).replace('T', ' ') : 'N/A'}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.4rem' }}>
                          {isActive ? (
                            <span className="badge badge-low">ACTIVE</span>
                          ) : (
                            <button
                              className="btn-secondary"
                              style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem' }}
                              onClick={() => onSelectDataset(d.dataset_id)}
                            >
                              Set Active
                            </button>
                          )}
                          {d.records_rejected > 0 && (
                            <button
                              className="btn-ghost"
                              style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem', color: '#f87171' }}
                              onClick={() => handleInspectErrors(d.dataset_id)}
                              disabled={loadingErrors}
                            >
                              Inspect Errors
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Rejection Inspector Modal */}
      {showErrorModal && (
        <div className="modal-backdrop" onClick={() => setShowErrorModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '850px' }}>
            <div className="modal-header">
              <h3 className="modal-title" style={{ color: '#f87171' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="8" x2="12" y2="12"></line>
                  <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                Rejected Records Inspector {inspectingDatasetId ? `(${inspectingDatasetId.slice(0, 8)}...)` : ''} ({rejectedRecords.length} Malformed Entries)
              </h3>
              <button className="btn-ghost" onClick={() => setShowErrorModal(false)}>✕</button>
            </div>
            <div className="modal-body">
              <p style={{ color: '#94a3b8', fontSize: '0.82rem', marginTop: 0 }}>
                The following records failed strict schema validation (e.g. invalid IPv4/IPv6, out-of-range port, inconsistent input/output array lengths). Raw payloads are preserved without corruption.
              </p>
              <div className="table-wrapper">
                <table className="cyber-table">
                  <thead>
                    <tr>
                      <th style={{ width: '80px' }}>Record #</th>
                      <th>Validation Errors</th>
                      <th>Raw Record Payload</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rejectedRecords.map((rec) => (
                      <tr key={rec.record_index}>
                        <td className="mono" style={{ fontWeight: 600 }}>#{rec.record_index + 1}</td>
                        <td>
                          <ul style={{ margin: 0, paddingLeft: '1.1rem', color: '#f87171', fontSize: '0.78rem' }}>
                            {rec.errors.map((err, i) => (
                              <li key={i}>{err}</li>
                            ))}
                          </ul>
                        </td>
                        <td>
                          <pre style={{ margin: 0, fontSize: '0.72rem', background: '#0b111e', padding: '0.5rem', borderRadius: '4px', maxHeight: '120px', overflowY: 'auto' }}>
                            {JSON.stringify(rec.raw_data, null, 2)}
                          </pre>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setShowErrorModal(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
