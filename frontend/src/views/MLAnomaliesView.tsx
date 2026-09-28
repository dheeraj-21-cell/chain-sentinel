import React, { useState } from 'react';
import {
  AnomalyDetectionResult,
  trainIsolationForest,
} from '../services/api';
import { CopyButton } from '../components/CopyButton';

interface MLAnomaliesViewProps {
  datasetId: string;
  anomalyResult: AnomalyDetectionResult | null;
  onRefreshAnomalies: () => Promise<void>;
  onSelectEntity: (type: 'wallet' | 'transaction' | 'ip', id: string) => void;
}

export const MLAnomaliesView: React.FC<MLAnomaliesViewProps> = ({
  datasetId,
  anomalyResult,
  onRefreshAnomalies,
  onSelectEntity,
}) => {
  const [entityType, setEntityType] = useState<'transaction' | 'wallet'>('transaction');
  const [contamination, setContamination] = useState<number>(0.1);
  const [isTraining, setIsTraining] = useState(false);
  const [trainError, setTrainError] = useState<string | null>(null);
  const [trainSuccess, setTrainSuccess] = useState<string | null>(null);
  const [filterAnomaliesOnly, setFilterAnomaliesOnly] = useState(true);

  const handleTrain = async () => {
    setIsTraining(true);
    setTrainError(null);
    setTrainSuccess(null);
    try {
      const res = await trainIsolationForest(datasetId, entityType, contamination);
      setTrainSuccess(`Isolation Forest trained successfully: ${res.anomaly_count} of ${res.total_entities} entities flagged as anomalies.`);
      await onRefreshAnomalies();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setTrainError(err.message);
      } else {
        setTrainError('Model training failed.');
      }
    } finally {
      setIsTraining(false);
    }
  };

  const anomaliesList = anomalyResult?.anomalies || [];
  const displayedAnomalies = filterAnomaliesOnly
    ? anomaliesList.filter((a) => a.is_anomaly)
    : anomaliesList;

  return (
    <div>
      {/* Header */}
      <div className="view-header">
        <div>
          <h1 className="view-title">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
              <line x1="12" y1="9" x2="12" y2="13"></line>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            Machine Learning Anomaly Detection (Isolation Forest)
          </h1>
          <p className="view-subtitle">
            Unsupervised statistical outlier detection using scikit-learn Isolation Forest over 18 transaction and 14 wallet feature dimensions.
          </p>
        </div>
      </div>

      {trainError && (
        <div style={{ marginBottom: '1.25rem', background: '#3b1010', border: '1px solid #991b1b', color: '#fca5a5', padding: '0.75rem', borderRadius: '6px', fontSize: '0.82rem' }}>
          {trainError}
        </div>
      )}
      {trainSuccess && (
        <div style={{ marginBottom: '1.25rem', background: '#091c15', border: '1px solid #059669', color: '#6ee7b7', padding: '0.75rem', borderRadius: '6px', fontSize: '0.82rem' }}>
          {trainSuccess}
        </div>
      )}

      {/* Model Controls Card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h3 className="card-title">Isolation Forest Hyperparameters & Controls</h3>
        <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Entity Type */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
              Target Entity:
            </label>
            <select
              value={entityType}
              onChange={(e) => setEntityType(e.target.value as any)}
              style={{ padding: '0.45rem 0.75rem' }}
            >
              <option value="transaction">Transactions (18 Features)</option>
              <option value="wallet">Wallets (14 Features)</option>
            </select>
          </div>

          {/* Contamination Slider */}
          <div style={{ minWidth: '200px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
              <span>Contamination Rate:</span>
              <strong className="mono" style={{ color: '#38bdf8' }}>{contamination.toFixed(2)}</strong>
            </div>
            <input
              type="range"
              className="input-range"
              min="0.01"
              max="0.25"
              step="0.01"
              value={contamination}
              onChange={(e) => setContamination(parseFloat(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>

          {/* Train Button */}
          <div style={{ alignSelf: 'flex-end' }}>
            <button
              className="btn-primary"
              onClick={handleTrain}
              disabled={isTraining}
            >
              {isTraining ? 'Training Isolation Forest...' : 'Train / Retrain Model'}
            </button>
          </div>
        </div>

        {/* Forensic limitations note */}
        <div style={{ marginTop: '0.85rem', fontSize: '0.75rem', color: '#64748b' }}>
          <strong>Neutral Model Notice:</strong> Anomaly detection scores indicate statistical distance from normal distribution only. No subjective criminality, culpability, or maliciousness is implied.
        </div>
      </div>

      {/* Summary KPI Cards */}
      {anomalyResult && (
        <div className="grid-cols-4" style={{ marginBottom: '1.5rem' }}>
          <div className="kpi-card">
            <div className="kpi-label">Evaluated Entities</div>
            <div className="kpi-value">{anomalyResult.total_entities}</div>
            <div className="kpi-subtext">Dataset {entityType} records</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Flagged Anomalies</div>
            <div className="kpi-value" style={{ color: anomalyResult.anomaly_count > 0 ? '#f87171' : '#10b981' }}>
              {anomalyResult.anomaly_count}
            </div>
            <div className="kpi-subtext">Statistically unusual</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Active Contamination</div>
            <div className="kpi-value">{(anomalyResult.contamination * 100).toFixed(0)}%</div>
            <div className="kpi-subtext">Expected outlier ratio</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Model Engine</div>
            <div className="kpi-value" style={{ fontSize: '1.1rem', color: '#38bdf8' }}>
              scikit-learn
            </div>
            <div className="kpi-subtext">Offline deterministic</div>
          </div>
        </div>
      )}

      {/* Anomalies Table */}
      <div className="card">
        <div className="card-title">
          <span>
            Flagged Anomalies & Explainability ({displayedAnomalies.length})
          </span>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <label style={{ fontSize: '0.78rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '0.35rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={filterAnomaliesOnly}
                onChange={(e) => setFilterAnomaliesOnly(e.target.checked)}
              />
              Anomalies only
            </label>
          </div>
        </div>

        {!anomalyResult ? (
          <div className="empty-state">
            <div className="empty-title">Model Not Yet Trained</div>
            <p className="empty-desc">
              Click "Train / Retrain Model" above to execute Isolation Forest outlier detection on this dataset.
            </p>
          </div>
        ) : displayedAnomalies.length === 0 ? (
          <div className="empty-state">
            <div className="empty-title">No Anomalies Found</div>
            <p className="empty-desc">No entities were classified as outliers under current contamination threshold.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="cyber-table">
              <thead>
                <tr>
                  <th>Entity Identifier</th>
                  <th>Type</th>
                  <th>Anomaly Score</th>
                  <th>Decision Score</th>
                  <th>Status</th>
                  <th>Forensic Feature Explainability</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {displayedAnomalies.map((anom) => (
                  <tr key={anom.entity_id}>
                    <td className="mono" style={{ fontSize: '0.78rem' }}>
                      <span
                        className="clickable-entity"
                        onClick={() => onSelectEntity(anom.entity_type as any, anom.entity_id)}
                      >
                        {anom.entity_id.length > 18 ? `${anom.entity_id.slice(0, 18)}...` : anom.entity_id}
                      </span>
                      <CopyButton text={anom.entity_id} />
                    </td>

                    <td>
                      <span className="badge badge-neutral">{anom.entity_type}</span>
                    </td>

                    <td className="mono" style={{ fontWeight: 600, color: anom.is_anomaly ? '#f87171' : '#cbd5e1' }}>
                      {anom.anomaly_score.toFixed(4)}
                    </td>

                    <td className="mono" style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                      {anom.raw_score.toFixed(4)}
                    </td>

                    <td>
                      <span className={`badge ${anom.is_anomaly ? 'badge-high' : 'badge-low'}`}>
                        {anom.is_anomaly ? 'ANOMALOUS' : 'NORMAL'}
                      </span>
                    </td>

                    <td style={{ fontSize: '0.78rem' }}>
                      <ul style={{ margin: 0, paddingLeft: '1rem', color: '#cbd5e1' }}>
                        {anom.explanation.map((exp, i) => (
                          <li key={i}>{exp}</li>
                        ))}
                      </ul>
                    </td>

                    <td>
                      <button
                        className="btn-secondary"
                        style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem' }}
                        onClick={() => onSelectEntity(anom.entity_type as any, anom.entity_id)}
                      >
                        Dossier
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
