import React, { useState, useEffect } from 'react';
import {
  buildGraph,
  getGraphMetrics,
  trainIsolationForest,
  runClustering,
  runBehavioralDetection,
  runRiskScoring,
} from '../services/api';

interface PipelineRunnerModalProps {
  isOpen: boolean;
  onClose: () => void;
  datasetId: string;
  onComplete: () => void;
}

interface StepStatus {
  name: string;
  description: string;
  status: 'pending' | 'running' | 'success' | 'error';
  message?: string;
}

export const PipelineRunnerModal: React.FC<PipelineRunnerModalProps> = ({
  isOpen,
  onClose,
  datasetId,
  onComplete,
}) => {
  const [steps, setSteps] = useState<StepStatus[]>([
    { name: 'Neo4j Graph Construction', description: 'Project transactions, wallets, and IPs into persistent graph', status: 'pending' },
    { name: 'NetworkX Graph Analysis', description: 'Extract in-memory topological features, degrees, and components', status: 'pending' },
    { name: 'Isolation Forest Anomaly ML', description: 'Train scikit-learn model over 18 tx and 14 wallet features', status: 'pending' },
    { name: 'DBSCAN Behavioral Clustering', description: 'Discover entity clusters and isolate statistical noise points', status: 'pending' },
    { name: 'Deterministic Behavioral Detectors', description: 'Detect fan-in, fan-out, dispersion, bursts, and peeling chains', status: 'pending' },
    { name: 'Multi-Evidence Risk Scoring', description: 'Aggregate multi-pipeline findings into transparent 0-100 scores', status: 'pending' },
  ]);

  const [isRunning, setIsRunning] = useState(false);
  const [isFinished, setIsFinished] = useState(false);

  const runAllPipelines = async () => {
    setIsRunning(true);
    setIsFinished(false);

    // Step 1: Neo4j
    setSteps((prev) => prev.map((s, i) => (i === 0 ? { ...s, status: 'running' } : s)));
    try {
      const res = await buildGraph(datasetId);
      setSteps((prev) => prev.map((s, i) => (i === 0 ? { ...s, status: 'success', message: res.message } : s)));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed';
      setSteps((prev) => prev.map((s, i) => (i === 0 ? { ...s, status: 'error', message: msg } : s)));
    }

    // Step 2: NetworkX
    setSteps((prev) => prev.map((s, i) => (i === 1 ? { ...s, status: 'running' } : s)));
    try {
      const res = await getGraphMetrics(datasetId);
      setSteps((prev) => prev.map((s, i) => (i === 1 ? { ...s, status: 'success', message: `${res.node_count} nodes, ${res.edge_count} edges` } : s)));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed';
      setSteps((prev) => prev.map((s, i) => (i === 1 ? { ...s, status: 'error', message: msg } : s)));
    }

    // Step 3: Isolation Forest
    setSteps((prev) => prev.map((s, i) => (i === 2 ? { ...s, status: 'running' } : s)));
    try {
      const res = await trainIsolationForest(datasetId, 'transaction', 0.1);
      setSteps((prev) => prev.map((s, i) => (i === 2 ? { ...s, status: 'success', message: `${res.anomaly_count} anomalies flagged` } : s)));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed';
      setSteps((prev) => prev.map((s, i) => (i === 2 ? { ...s, status: 'error', message: msg } : s)));
    }

    // Step 4: DBSCAN
    setSteps((prev) => prev.map((s, i) => (i === 3 ? { ...s, status: 'running' } : s)));
    try {
      const res = await runClustering(datasetId, 0.5, 2);
      setSteps((prev) => prev.map((s, i) => (i === 3 ? { ...s, status: 'success', message: `${res.cluster_count} clusters, ${res.noise_count} noise outliers` } : s)));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed';
      setSteps((prev) => prev.map((s, i) => (i === 3 ? { ...s, status: 'error', message: msg } : s)));
    }

    // Step 5: Behavioral Detection
    setSteps((prev) => prev.map((s, i) => (i === 4 ? { ...s, status: 'running' } : s)));
    try {
      const res = await runBehavioralDetection(datasetId);
      setSteps((prev) => prev.map((s, i) => (i === 4 ? { ...s, status: 'success', message: `${res.summary.total_findings} findings detected` } : s)));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed';
      setSteps((prev) => prev.map((s, i) => (i === 4 ? { ...s, status: 'error', message: msg } : s)));
    }

    // Step 6: Risk Scoring
    setSteps((prev) => prev.map((s, i) => (i === 5 ? { ...s, status: 'running' } : s)));
    try {
      const res = await runRiskScoring(datasetId);
      setSteps((prev) => prev.map((s, i) => (i === 5 ? { ...s, status: 'success', message: `${res.summary.total_scored_entities} scored entities` } : s)));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed';
      setSteps((prev) => prev.map((s, i) => (i === 5 ? { ...s, status: 'error', message: msg } : s)));
    }

    setIsRunning(false);
    setIsFinished(true);
    onComplete();
  };

  useEffect(() => {
    if (isOpen) {
      setIsFinished(false);
      setSteps([
        { name: 'Neo4j Graph Construction', description: 'Project transactions, wallets, and IPs into persistent graph', status: 'pending' },
        { name: 'NetworkX Graph Analysis', description: 'Extract in-memory topological features, degrees, and components', status: 'pending' },
        { name: 'Isolation Forest Anomaly ML', description: 'Train scikit-learn model over 18 tx and 14 wallet features', status: 'pending' },
        { name: 'DBSCAN Behavioral Clustering', description: 'Discover entity clusters and isolate statistical noise points', status: 'pending' },
        { name: 'Deterministic Behavioral Detectors', description: 'Detect fan-in, fan-out, dispersion, bursts, and peeling chains', status: 'pending' },
        { name: 'Multi-Evidence Risk Scoring', description: 'Aggregate multi-pipeline findings into transparent 0-100 scores', status: 'pending' },
      ]);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={() => !isRunning && onClose()}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px' }}>
        <div className="modal-header">
          <h3 className="modal-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2.5">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
            Intelligence Pipelines Orchestrator
          </h3>
          <button className="btn-ghost" onClick={onClose} disabled={isRunning}>
            ✕
          </button>
        </div>

        <div className="modal-body">
          <p style={{ color: '#94a3b8', fontSize: '0.82rem', marginTop: 0, marginBottom: '1.25rem' }}>
            Execute the full offline intelligence pipeline sequence for active dataset{' '}
            <span className="mono" style={{ color: '#38bdf8' }}>{datasetId.slice(0, 8)}...</span>
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {steps.map((step, idx) => (
              <div
                key={idx}
                style={{
                  background: '#0b111e',
                  border: '1px solid #1e293b',
                  borderRadius: '6px',
                  padding: '0.7rem 0.9rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.82rem', color: '#f8fafc' }}>
                    {idx + 1}. {step.name}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b' }}>
                    {step.description}
                  </div>
                  {step.message && (
                    <div style={{ fontSize: '0.7rem', color: step.status === 'success' ? '#34d399' : '#f87171', marginTop: '2px' }}>
                      {step.message}
                    </div>
                  )}
                </div>

                <div>
                  {step.status === 'pending' && (
                    <span className="badge badge-neutral">Pending</span>
                  )}
                  {step.status === 'running' && (
                    <span className="badge badge-cyan" style={{ animation: 'pulse-dot 1s infinite' }}>
                      Running...
                    </span>
                  )}
                  {step.status === 'success' && (
                    <span className="badge badge-low">Done</span>
                  )}
                  {step.status === 'error' && (
                    <span className="badge badge-high">Failed</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose} disabled={isRunning}>
            {isFinished ? 'Close' : 'Cancel'}
          </button>
          <button
            className="btn-primary"
            onClick={runAllPipelines}
            disabled={isRunning}
          >
            {isRunning ? 'Running Pipelines...' : isFinished ? 'Re-run Pipelines' : 'Execute Full Pipeline'}
          </button>
        </div>
      </div>
    </div>
  );
};
