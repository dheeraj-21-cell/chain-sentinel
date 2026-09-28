import React, { useState } from 'react';
import {
  RiskSummary,
  RiskFinding,
  runRiskScoring,
  RiskScoringRequest,
} from '../services/api';
import { CopyButton } from '../components/CopyButton';

interface RiskAlertsViewProps {
  datasetId: string;
  riskSummary: RiskSummary | null;
  riskFindings: RiskFinding[];
  onRefreshRisk: () => Promise<void>;
  onSelectEntity: (type: 'wallet' | 'transaction' | 'ip', id: string) => void;
}

export const RiskAlertsView: React.FC<RiskAlertsViewProps> = ({
  datasetId,
  riskSummary,
  riskFindings,
  onRefreshRisk,
  onSelectEntity,
}) => {
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [isScoring, setIsScoring] = useState(false);
  const [scoreError, setScoreError] = useState<string | null>(null);
  const [scoreSuccess, setScoreSuccess] = useState<string | null>(null);

  // Weight Tuning State
  const [weights, setWeights] = useState<RiskScoringRequest>({
    behavioral_weight: 35,
    ml_weight: 25,
    clustering_weight: 15,
    graph_weight: 15,
    activity_weight: 10,
  });
  const [showWeightTuning, setShowWeightTuning] = useState(false);

  const handleRunScoring = async () => {
    setIsScoring(true);
    setScoreError(null);
    setScoreSuccess(null);
    try {
      const res = await runRiskScoring(datasetId, weights);
      setScoreSuccess(`Risk scoring complete: ${res.summary.total_scored_entities} entities prioritized across 5 pipelines.`);
      await onRefreshRisk();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setScoreError(err.message);
      } else {
        setScoreError('Risk scoring failed.');
      }
    } finally {
      setIsScoring(false);
    }
  };

  const filteredFindings = riskFindings.filter((rf) => {
    if (priorityFilter !== 'ALL' && rf.priority !== priorityFilter) {
      return false;
    }
    return true;
  });

  return (
    <div>
      {/* Header */}
      <div className="view-header">
        <div>
          <h1 className="view-title">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
            </svg>
            Investigative Risk Scoring & Explainability
          </h1>
          <p className="view-subtitle">
            Deterministic, dataset-scoped prioritization combining behavioral detection, Isolation Forest ML, DBSCAN clustering, and graph topologies.
          </p>
        </div>
        <div className="header-actions">
          <button
            className="btn-secondary"
            onClick={() => setShowWeightTuning(!showWeightTuning)}
          >
            {showWeightTuning ? 'Hide Weight Tuning' : 'Tune Category Weights'}
          </button>
          <button
            className="btn-primary"
            onClick={handleRunScoring}
            disabled={isScoring}
          >
            {isScoring ? 'Calculating Scores...' : 'Recalculate Risk Scores'}
          </button>
        </div>
      </div>

      {scoreError && (
        <div style={{ marginBottom: '1.25rem', background: '#3b1010', border: '1px solid #991b1b', color: '#fca5a5', padding: '0.75rem', borderRadius: '6px', fontSize: '0.82rem' }}>
          {scoreError}
        </div>
      )}
      {scoreSuccess && (
        <div style={{ marginBottom: '1.25rem', background: '#091c15', border: '1px solid #059669', color: '#6ee7b7', padding: '0.75rem', borderRadius: '6px', fontSize: '0.82rem' }}>
          {scoreSuccess}
        </div>
      )}

      {/* Weight Tuning Drawer */}
      {showWeightTuning && (
        <div className="card" style={{ marginBottom: '1.5rem', background: '#0f172a' }}>
          <h3 className="card-title">Evidence Source Weight Allocation (Sum = 100)</h3>
          <p style={{ color: '#94a3b8', fontSize: '0.78rem', marginTop: 0 }}>
            Adjust relative points awarded across the 5 analytical pipelines to calibrate prioritization for specific investigative scenarios.
          </p>
          <div className="grid-cols-4" style={{ marginBottom: '1rem' }}>
            <div>
              <div className="flex-row-between" style={{ fontSize: '0.75rem', marginBottom: '0.2rem' }}>
                <span>Behavioral Detection:</span>
                <strong className="mono">{weights.behavioral_weight} pts</strong>
              </div>
              <input
                type="range"
                className="input-range"
                min="0"
                max="50"
                value={weights.behavioral_weight}
                onChange={(e) => setWeights({ ...weights, behavioral_weight: parseFloat(e.target.value) })}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <div className="flex-row-between" style={{ fontSize: '0.75rem', marginBottom: '0.2rem' }}>
                <span>ML Isolation Forest:</span>
                <strong className="mono">{weights.ml_weight} pts</strong>
              </div>
              <input
                type="range"
                className="input-range"
                min="0"
                max="50"
                value={weights.ml_weight}
                onChange={(e) => setWeights({ ...weights, ml_weight: parseFloat(e.target.value) })}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <div className="flex-row-between" style={{ fontSize: '0.75rem', marginBottom: '0.2rem' }}>
                <span>DBSCAN Clustering:</span>
                <strong className="mono">{weights.clustering_weight} pts</strong>
              </div>
              <input
                type="range"
                className="input-range"
                min="0"
                max="30"
                value={weights.clustering_weight}
                onChange={(e) => setWeights({ ...weights, clustering_weight: parseFloat(e.target.value) })}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <div className="flex-row-between" style={{ fontSize: '0.75rem', marginBottom: '0.2rem' }}>
                <span>Graph Topology:</span>
                <strong className="mono">{weights.graph_weight} pts</strong>
              </div>
              <input
                type="range"
                className="input-range"
                min="0"
                max="30"
                value={weights.graph_weight}
                onChange={(e) => setWeights({ ...weights, graph_weight: parseFloat(e.target.value) })}
                style={{ width: '100%' }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Summary KPI Cards */}
      {riskSummary && (
        <div className="grid-cols-4" style={{ marginBottom: '1.5rem' }}>
          <div className="kpi-card">
            <div className="kpi-label">Total Scored Entities</div>
            <div className="kpi-value">{riskSummary.total_scored_entities}</div>
            <div className="kpi-subtext">Active dataset scope</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Average Risk Score</div>
            <div className="kpi-value">{riskSummary.average_score.toFixed(1)}</div>
            <div className="kpi-subtext">Across all evaluated nodes</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Highest Score</div>
            <div className="kpi-value" style={{ color: riskSummary.highest_score >= 50 ? '#ef4444' : '#10b981' }}>
              {riskSummary.highest_score.toFixed(1)}
            </div>
            <div className="kpi-subtext">Maximum priority node</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Priority Distribution</div>
            <div style={{ display: 'flex', gap: '0.35rem', marginTop: '0.3rem', flexWrap: 'wrap' }}>
              <span className="badge badge-critical">{riskSummary.counts_by_priority.CRITICAL || 0} Crit</span>
              <span className="badge badge-high">{riskSummary.counts_by_priority.HIGH || 0} High</span>
              <span className="badge badge-moderate">{riskSummary.counts_by_priority.MODERATE || 0} Mod</span>
              <span className="badge badge-low">{riskSummary.counts_by_priority.LOW || 0} Low</span>
            </div>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="tabs-header">
        {['ALL', 'CRITICAL', 'HIGH', 'MODERATE', 'LOW'].map((p) => (
          <button
            key={p}
            className={`tab-btn ${priorityFilter === p ? 'active' : ''}`}
            onClick={() => setPriorityFilter(p)}
          >
            {p} ({p === 'ALL' ? riskFindings.length : riskSummary?.counts_by_priority[p] || 0})
          </button>
        ))}
      </div>

      {/* Scored Findings List */}
      {!riskSummary ? (
        <div className="empty-state">
          <div className="empty-title">Risk Scoring Not Calculated</div>
          <p className="empty-desc">Click "Recalculate Risk Scores" above to score entities against all pipelines.</p>
        </div>
      ) : filteredFindings.length === 0 ? (
        <div className="empty-state">
          <div className="empty-title">No Entities in {priorityFilter} Priority Band</div>
          <p className="empty-desc">No entities matched this priority threshold in the active dataset.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          {filteredFindings.map((rf) => (
            <div
              key={rf.risk_id}
              className="card"
              style={{
                borderLeft: `4px solid ${
                  rf.priority === 'CRITICAL' ? '#ef4444' : rf.priority === 'HIGH' ? '#f87171' : rf.priority === 'MODERATE' ? '#f59e0b' : '#10b981'
                }`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.75rem' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                    <span className="badge badge-neutral">{rf.entity_type}</span>
                    <span className={`badge badge-${rf.priority.toLowerCase()}`}>
                      {rf.priority} PRIORITY
                    </span>
                    <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                      Evidence Confidence: {(rf.confidence * 100).toFixed(0)}%
                    </span>
                  </div>

                  <div className="mono" style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span
                      className="clickable-entity"
                      onClick={() => onSelectEntity(rf.entity_type as any, rf.entity_id)}
                    >
                      {rf.entity_id}
                    </span>
                    <CopyButton text={rf.entity_id} />
                  </div>
                </div>

                {/* Score Dial / Bar */}
                <div style={{ textAlign: 'right' }}>
                  <div className="mono" style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc' }}>
                    {rf.score.toFixed(1)} <span style={{ fontSize: '0.8rem', color: '#64748b' }}>/ 100</span>
                  </div>
                  <div style={{ width: '120px', height: '6px', background: '#1e293b', borderRadius: '3px', overflow: 'hidden', marginTop: '4px' }}>
                    <div
                      style={{
                        height: '100%',
                        width: `${rf.score}%`,
                        background: rf.priority === 'CRITICAL' ? '#ef4444' : rf.priority === 'HIGH' ? '#f87171' : rf.priority === 'MODERATE' ? '#f59e0b' : '#10b981',
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Neutral Plain-English Forensic Summary */}
              <p style={{ fontSize: '0.82rem', color: '#cbd5e1', lineHeight: '1.5', margin: '0 0 0.75rem 0' }}>
                {rf.explanation}
              </p>

              {/* Evidence Pills */}
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                {Object.entries(rf.evidence_contributions).map(([src, contrib]) => (
                  <div
                    key={src}
                    style={{
                      background: '#0b111e',
                      border: '1px solid #1e293b',
                      borderRadius: '4px',
                      padding: '0.25rem 0.5rem',
                      fontSize: '0.72rem',
                    }}
                  >
                    <span style={{ color: '#94a3b8', textTransform: 'capitalize' }}>{src.replace(/_/g, ' ')}: </span>
                    <strong style={{ color: contrib.points > 0 ? '#38bdf8' : '#64748b' }}>
                      {contrib.points.toFixed(1)}/{contrib.max_points}
                    </strong>
                  </div>
                ))}

                <button
                  className="btn-secondary"
                  style={{ marginLeft: 'auto', padding: '0.25rem 0.65rem', fontSize: '0.72rem' }}
                  onClick={() => onSelectEntity(rf.entity_type as any, rf.entity_id)}
                >
                  Open Full Dossier →
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
