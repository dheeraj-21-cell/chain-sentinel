import React, { useState, useRef } from 'react';
import { uploadDataset, DatasetIngestionResponse } from '../services/api';
import { useI18n } from '../services/i18n';

interface UploadDatasetModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (datasetId: string, runPipelines?: boolean) => void;
}

export const UploadDatasetModal: React.FC<UploadDatasetModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const { t } = useI18n();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<DatasetIngestionResponse | null>(null);

  if (!isOpen) return null;

  const handleReset = () => {
    setSelectedFile(null);
    setUploadError(null);
    setUploadProgress(null);
    setUploadResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleClose = () => {
    if (isUploading) return;
    handleReset();
    onClose();
  };

  const validateFile = (file: File): boolean => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !['csv', 'json', 'xml'].includes(ext)) {
      setUploadError(`Unsupported format '.${ext}'. Please upload a CSV, JSON, or XML dataset file.`);
      return false;
    }
    if (file.size === 0) {
      setUploadError('The selected file is empty (0 bytes).');
      return false;
    }
    // Limit to 50MB
    if (file.size > 50 * 1024 * 1024) {
      setUploadError('File size exceeds 50MB limit.');
      return false;
    }
    return true;
  };

  const handleFileSelect = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    setUploadError(null);
    setUploadResult(null);
    if (validateFile(file)) {
      setSelectedFile(file);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const getFileBadgeColor = (filename: string): { bg: string; color: string } => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (ext === 'csv') return { bg: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' };
    if (ext === 'json') return { bg: 'rgba(251, 191, 36, 0.15)', color: '#fbbf24' };
    if (ext === 'xml') return { bg: 'rgba(168, 85, 247, 0.15)', color: '#c084fc' };
    return { bg: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8' };
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError('Please select a file to upload.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadProgress('Uploading raw file to storage...');

    try {
      setUploadProgress('Validating schema and parsing transaction records...');
      const res = await uploadDataset(selectedFile);

      setUploadProgress('Normalizing records into columnar Parquet table...');
      await new Promise((r) => setTimeout(r, 400));

      setUploadResult(res);
      setUploadProgress(null);
    } catch (err: unknown) {
      setUploadProgress(null);
      if (err instanceof Error) {
        setUploadError(err.message);
      } else {
        setUploadError('Dataset ingestion failed due to an unexpected error.');
      }
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={handleClose}>
      <div
        className="modal-dialog"
        onClick={(e) => e.stopPropagation()}
        style={{
          maxWidth: '560px',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-medium)',
          borderRadius: '12px',
          boxShadow: '0 20px 40px -15px rgba(0,0,0,0.5)',
        }}
      >
        {/* Modal Header */}
        <div
          className="modal-header"
          style={{
            borderBottom: '1px solid var(--border-subtle)',
            padding: '1rem 1.25rem',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'rgba(56, 189, 248, 0.12)',
                color: 'var(--cyber-blue)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {t('upload_modal_title')}
              </h3>
              <p style={{ margin: 0, fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                {t('upload_modal_desc')}
              </p>
            </div>
          </div>

          <button
            className="btn-ghost"
            onClick={handleClose}
            disabled={isUploading}
            style={{ padding: '0.3rem 0.55rem', fontSize: '1.1rem', cursor: isUploading ? 'not-allowed' : 'pointer' }}
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body" style={{ padding: '1.25rem' }}>
          {/* SUCCESS STATE */}
          {uploadResult ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div
                style={{
                  background: 'rgba(52, 211, 153, 0.08)',
                  border: '1px solid rgba(52, 211, 153, 0.3)',
                  borderRadius: '8px',
                  padding: '1rem',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.75rem',
                }}
              >
                <div
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '50%',
                    background: '#34d399',
                    color: '#064e3b',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    fontWeight: 700,
                  }}
                >
                  ✓
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: '0.92rem', color: 'var(--cyber-emerald)' }}>
                    {t('upload_success_title')}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                    Dataset <strong style={{ color: 'var(--text-primary)' }}>{uploadResult.filename}</strong> has been validated and registered.
                  </div>
                </div>
              </div>

              {/* Ingestion Metrics Card */}
              <div
                style={{
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-medium)',
                  borderRadius: '8px',
                  padding: '0.85rem 1rem',
                }}
              >
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', textAlign: 'center' }}>
                  <div>
                    <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Status</div>
                    <div style={{ marginTop: '0.2rem' }}>
                      <span className={`badge ${uploadResult.status === 'SUCCESS' ? 'badge-low' : 'badge-moderate'}`}>
                        {uploadResult.status}
                      </span>
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Valid Records</div>
                    <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.1rem' }}>
                      {uploadResult.records_valid.toLocaleString()}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', color: 'var(--text-muted)' }}>Rejected</div>
                    <div style={{ fontSize: '1.05rem', fontWeight: 700, color: uploadResult.records_rejected > 0 ? '#f87171' : 'var(--text-muted)', marginTop: '0.1rem' }}>
                      {uploadResult.records_rejected.toLocaleString()}
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)', fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Dataset ID:</span>
                  <span className="mono" style={{ color: 'var(--cyber-blue)' }}>{uploadResult.dataset_id}</span>
                </div>
              </div>

              <p style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', margin: 0 }}>
                The new dataset is ready for inspection. The existing <strong style={{ color: 'var(--text-primary)' }}>sih_showcase.csv</strong> dataset remains safe and selectable at any time.
              </p>

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.5rem', justifyContent: 'flex-end' }}>
                <button
                  className="btn-secondary"
                  onClick={() => {
                    onUploadSuccess(uploadResult.dataset_id, false);
                    handleClose();
                  }}
                >
                  {t('switch_to_dataset')}
                </button>
                <button
                  className="btn-primary"
                  onClick={() => {
                    onUploadSuccess(uploadResult.dataset_id, true);
                    handleClose();
                  }}
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                  </svg>
                  {t('run_pipelines')}
                </button>
              </div>
            </div>
          ) : (
            /* UPLOAD FORM STATE */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Hidden native input */}
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.json,.xml,text/csv,application/json,application/xml,text/xml"
                style={{ display: 'none' }}
                onChange={(e) => handleFileSelect(e.target.files)}
                disabled={isUploading}
              />

              {/* Drag & Drop Area */}
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  handleFileSelect(e.dataTransfer.files);
                }}
                onClick={() => !isUploading && fileInputRef.current?.click()}
                style={{
                  border: `2px dashed ${isDragging ? 'var(--cyber-blue)' : selectedFile ? 'var(--cyber-emerald)' : 'var(--border-medium)'}`,
                  borderRadius: '10px',
                  padding: '1.75rem 1rem',
                  textAlign: 'center',
                  background: isDragging ? 'rgba(56, 189, 248, 0.05)' : 'var(--bg-elevated)',
                  cursor: isUploading ? 'not-allowed' : 'pointer',
                  transition: 'all 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '0.75rem' }}>
                  <div
                    style={{
                      width: '44px',
                      height: '44px',
                      borderRadius: '50%',
                      background: selectedFile ? 'rgba(52, 211, 153, 0.15)' : 'rgba(56, 189, 248, 0.1)',
                      color: selectedFile ? 'var(--cyber-emerald)' : 'var(--cyber-blue)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"></path>
                      <path d="M12 12v9"></path>
                      <path d="m16 16-4-4-4 4"></path>
                    </svg>
                  </div>
                </div>

                <div style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--text-primary)' }}>
                  {selectedFile ? selectedFile.name : t('drag_drop_file')}
                </div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                  {t('supported_formats')}
                </div>

                {/* Badges */}
                <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'center', marginTop: '0.75rem' }}>
                  <span className="badge" style={{ background: 'rgba(56, 189, 248, 0.1)', color: '#38bdf8', fontSize: '0.66rem' }}>CSV</span>
                  <span className="badge" style={{ background: 'rgba(251, 191, 36, 0.1)', color: '#fbbf24', fontSize: '0.66rem' }}>JSON</span>
                  <span className="badge" style={{ background: 'rgba(168, 85, 247, 0.1)', color: '#c084fc', fontSize: '0.66rem' }}>XML</span>
                </div>
              </div>

              {/* Selected File Details Banner */}
              {selectedFile && (
                <div
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-medium)',
                    borderRadius: '8px',
                    padding: '0.75rem 1rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', minWidth: 0 }}>
                    <span
                      className="badge mono"
                      style={{
                        ...getFileBadgeColor(selectedFile.name),
                        fontSize: '0.68rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                      }}
                    >
                      {selectedFile.name.split('.').pop()}
                    </span>
                    <div style={{ minWidth: 0 }}>
                      <div
                        style={{
                          fontWeight: 600,
                          fontSize: '0.82rem',
                          color: 'var(--text-primary)',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {selectedFile.name}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {formatFileSize(selectedFile.size)}
                      </div>
                    </div>
                  </div>

                  <button
                    className="btn-ghost"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleReset();
                    }}
                    disabled={isUploading}
                    style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', color: 'var(--text-muted)' }}
                    title="Remove file"
                  >
                    Remove
                  </button>
                </div>
              )}

              {/* Progress Indicator */}
              {isUploading && (
                <div
                  style={{
                    background: 'rgba(56, 189, 248, 0.08)',
                    border: '1px solid rgba(56, 189, 248, 0.25)',
                    borderRadius: '8px',
                    padding: '0.75rem 1rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <div
                      style={{
                        width: '14px',
                        height: '14px',
                        border: '2px solid var(--cyber-blue)',
                        borderTopColor: 'transparent',
                        borderRadius: '50%',
                        animation: 'spin 1s linear infinite',
                      }}
                    />
                    <span style={{ fontSize: '0.78rem', color: 'var(--cyber-blue)', fontWeight: 600 }}>
                      {uploadProgress || t('uploading')}
                    </span>
                  </div>
                  <div
                    style={{
                      height: '3px',
                      background: 'rgba(56, 189, 248, 0.2)',
                      borderRadius: '2px',
                      marginTop: '0.5rem',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        background: 'var(--cyber-blue)',
                        width: '70%',
                        animation: 'pulse 1.5s ease-in-out infinite',
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Error Message */}
              {uploadError && (
                <div
                  style={{
                    background: 'rgba(248, 113, 113, 0.1)',
                    border: '1px solid rgba(248, 113, 113, 0.3)',
                    borderRadius: '8px',
                    padding: '0.75rem 1rem',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.6rem',
                  }}
                >
                  <span style={{ color: '#f87171', fontWeight: 700, fontSize: '0.9rem' }}>⚠</span>
                  <div style={{ fontSize: '0.76rem', color: '#f87171', flex: 1 }}>
                    {uploadError}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div style={{ display: 'flex', gap: '0.6rem', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
                <button
                  className="btn-secondary"
                  onClick={handleClose}
                  disabled={isUploading}
                >
                  {t('cancel')}
                </button>
                <button
                  className="btn-primary"
                  onClick={handleUpload}
                  disabled={!selectedFile || isUploading}
                  style={{ minWidth: '130px' }}
                >
                  {isUploading ? (
                    t('uploading')
                  ) : (
                    <>
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="17 8 12 3 7 8"></polyline>
                        <line x1="12" y1="3" x2="12" y2="15"></line>
                      </svg>
                      {t('upload_and_validate')}
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
