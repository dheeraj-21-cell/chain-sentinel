import React, { useState } from 'react';
import { CopyButton } from './CopyButton';
import {
  WalletActivity,
  CorrelationRecord,
  RiskFinding,
  BehavioralFinding,
  AnomalyScoreItem,
  WalletGraphMetrics,
  WalletClusterItem,
} from '../services/api';
import { EntityInvestigationSummary } from './EntityInvestigationSummary';
import { useI18n } from '../services/i18n';

interface EntityDetailModalProps {
  entityType: 'wallet' | 'transaction' | 'ip';
  entityId: string;
  datasetId: string;
  onClose: () => void;
  wallets: WalletActivity[];
  correlations: CorrelationRecord[];
  riskFindings: RiskFinding[];
  behaviorFindings: BehavioralFinding[];
  anomalies: AnomalyScoreItem[];
  graphMetrics: WalletGraphMetrics[];
  clusters: WalletClusterItem[];
  onNavigateToGraph?: (entityId: string) => void;
}

export const EntityDetailModal: React.FC<EntityDetailModalProps> = ({
  entityType,
  entityId,
  datasetId,
  onClose,
  wallets,
  correlations,
  riskFindings,
  behaviorFindings,
  anomalies,
  graphMetrics,
  clusters,
  onNavigateToGraph,
}) => {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<'overview' | 'transactions' | 'graph' | 'ml' | 'behavior' | 'network' | 'evidence'>('overview');

  // Match existing dataset records
  const riskData = riskFindings.find((r) => r.entity_id === entityId);
  const entityBehaviors = behaviorFindings.filter(
    (b) => b.entity_id === entityId || b.supporting_transaction_ids.includes(entityId)
  );
  const anomalyData = anomalies.find((a) => a.entity_id === entityId);
  const graphData = graphMetrics.find((g) => g.address === entityId);
  const clusterData = clusters.find((c) => c.address === entityId);

  // Filter associated transactions
  const associatedTxs = correlations.filter((c) => {
    if (entityType === 'wallet') {
      return c.input_addresses.includes(entityId) || c.output_addresses.includes(entityId);
    }
    if (entityType === 'ip') {
      return c.src_ip === entityId || c.dst_ip === entityId;
    }
    return c.txid === entityId;
  });

  // Extract unique observed IPs
  const observedIPs = Array.from(
    new Set(
      associatedTxs
        .flatMap((tx) => [tx.src_ip, tx.dst_ip])
        .filter((ip): ip is string => Boolean(ip) && ip !== 'unknown')
    )
  );



  const titlePrefix = entityType === 'wallet' ? t('investigation_dossier') : t('entity_investigation');

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '860px' }}>
        {/* Header */}
        <div className="modal-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <span className="badge badge-cyan">{titlePrefix}</span>
              {riskData && (
                <span className={`badge badge-${riskData.priority.toLowerCase()}`}>
                  {riskData.priority} ({riskData.score.toFixed(0)})
                </span>
              )}
              {anomalyData?.is_anomaly && <span className="badge badge-high">ML ANOMALY</span>}
              {clusterData && (
                <span className={clusterData.is_noise ? 'badge badge-moderate' : 'badge badge-purple'}>
                  {clusterData.is_noise ? 'DBSCAN NOISE' : `CLUSTER #${clusterData.cluster_id}`}
                </span>
              )}
            </div>
            <h2 className="modal-title" style={{ marginTop: '0.35rem', fontSize: '1rem' }}>
              <span className="mono" style={{ wordBreak: 'break-all', color: 'var(--text-primary)' }}>
                {entityId}
              </span>
              <CopyButton text={entityId} />
            </h2>
          </div>
          <button className="btn-ghost" onClick={onClose} style={{ fontSize: '1.2rem', padding: '0.2rem 0.5rem' }}>
            ✕
          </button>
        </div>

        {/* 7 Structured Tabs */}
        <div style={{ padding: '0 1.25rem', background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border-subtle)' }}>
          <div className="tabs-header" style={{ marginBottom: 0, borderBottom: 'none' }}>
            <button className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>
              {t('tab_overview')}
            </button>
            <button className={`tab-btn ${activeTab === 'transactions' ? 'active' : ''}`} onClick={() => setActiveTab('transactions')}>
              {t('tab_transactions')} ({associatedTxs.length})
            </button>
            <button className={`tab-btn ${activeTab === 'graph' ? 'active' : ''}`} onClick={() => setActiveTab('graph')}>
              {t('tab_graph')}
            </button>
            <button className={`tab-btn ${activeTab === 'ml' ? 'active' : ''}`} onClick={() => setActiveTab('ml')}>
              {t('tab_ml')}
            </button>
            <button className={`tab-btn ${activeTab === 'behavior' ? 'active' : ''}`} onClick={() => setActiveTab('behavior')}>
              {t('tab_behavior')} ({entityBehaviors.length})
            </button>
            <button className={`tab-btn ${activeTab === 'network' ? 'active' : ''}`} onClick={() => setActiveTab('network')}>
              {t('tab_network')} ({observedIPs.length})
            </button>
            <button className={`tab-btn ${activeTab === 'evidence' ? 'active' : ''}`} onClick={() => setActiveTab('evidence')}>
              {t('tab_evidence')}
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          {/* TAB 1: OVERVIEW */}
          {activeTab === 'overview' && (
            <div>
              <EntityInvestigationSummary
                entityType={entityType}
                entityId={entityId}
                datasetId={datasetId}
                wallets={wallets}
                correlations={correlations}
                riskFindings={riskFindings}
                behaviorFindings={behaviorFindings}
                anomalies={anomalies}
                graphMetrics={graphMetrics}
                clusters={clusters}
                compact={false}
                onNavigateToGraph={onNavigateToGraph}
              />

              {/* Quick Actions Bar */}
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.25rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border-subtle)' }}>
                <button className="btn-secondary" onClick={() => setActiveTab('transactions')} style={{ fontSize: '0.76rem' }}>
                  {t('btn_view_txs')} ({associatedTxs.length}) →
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => {
                    if (onNavigateToGraph) {
                      onClose();
                      onNavigateToGraph(entityId);
                    } else {
                      setActiveTab('graph');
                    }
                  }}
                  style={{ fontSize: '0.76rem' }}
                >
                  {t('btn_view_graph')} →
                </button>
                <button className="btn-secondary" onClick={() => setActiveTab('evidence')} style={{ fontSize: '0.76rem' }}>
                  {t('btn_view_evidence')} →
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: TRANSACTIONS */}
          {activeTab === 'transactions' && (
            <div>
              <div style={{ marginBottom: '0.75rem', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                Transactions involving this entity in the active dataset ({associatedTxs.length} confirmed records):
              </div>
              {associatedTxs.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No transaction records found for this entity.
                </div>
              ) : (
                <div className="table-wrapper">
                  <table className="cyber-table">
                    <thead>
                      <tr>
                        <th>TXID</th>
                        <th>Observed Peer</th>
                        <th>Inputs</th>
                        <th>Outputs</th>
                        <th>Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {associatedTxs.map((tx, idx) => (
                        <tr key={tx.txid || idx}>
                          <td>
                            <span className="mono" style={{ color: 'var(--cyber-cyan)' }}>
                              {tx.txid ? `${tx.txid.slice(0, 10)}...${tx.txid.slice(-8)}` : '—'}
                            </span>
                          </td>
                          <td className="mono" style={{ fontSize: '0.74rem' }}>
                            {tx.src_ip || tx.dst_ip || '—'}
                          </td>
                          <td className="mono">{tx.input_addresses.length}</td>
                          <td className="mono">{tx.output_addresses.length}</td>
                          <td style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                            {tx.timestamp || '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: GRAPH TOPOLOGY */}
          {activeTab === 'graph' && (
            <div>
              <div className="grid-cols-3" style={{ marginBottom: '1rem' }}>
                <div className="kpi-card">
                  <div className="kpi-label">Total Degree</div>
                  <div className="kpi-value">{graphData ? graphData.degree : '—'}</div>
                  <div className="kpi-subtext">Connected nodes in Neo4j</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Fan-In / Fan-Out</div>
                  <div className="kpi-value" style={{ fontSize: '1.1rem' }}>
                    {graphData ? `${graphData.fan_in} In / ${graphData.fan_out} Out` : '—'}
                  </div>
                  <div className="kpi-subtext">Directed transaction flow</div>
                </div>
                <div className="kpi-card">
                  <div className="kpi-label">Centrality (In / Out)</div>
                  <div className="kpi-value" style={{ fontSize: '1.1rem' }}>
                    {graphData ? `${graphData.in_degree_centrality.toFixed(3)} / ${graphData.out_degree_centrality.toFixed(3)}` : '—'}
                  </div>
                  <div className="kpi-subtext">Network graph centrality</div>
                </div>
              </div>

              <div className="card">
                <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem' }}>DBSCAN Behavioral Grouping</h4>
                {clusterData ? (
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    <div>
                      <strong>Status:</strong>{' '}
                      <span className={clusterData.is_noise ? 'badge badge-moderate' : 'badge badge-purple'}>
                        {clusterData.is_noise ? 'DBSCAN Noise (-1)' : `Cluster #${clusterData.cluster_id}`}
                      </span>
                    </div>
                    <div style={{ marginTop: '0.4rem' }}>
                      {clusterData.is_noise
                        ? 'This entity exhibits unique behavioral attributes that do not correlate with standard peer clusters.'
                        : `This entity shares behavioral clustering features with cluster group #${clusterData.cluster_id}.`}
                    </div>
                  </div>
                ) : (
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    No DBSCAN clustering assignment calculated for this entity.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: ML ANALYSIS */}
          {activeTab === 'ml' && (
            <div>
              <div className="card" style={{ marginBottom: '1rem' }}>
                <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.88rem', color: 'var(--cyber-amber)' }}>
                  Isolation Forest Anomaly Detection
                </h4>
                {anomalyData ? (
                  <div>
                    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '0.75rem' }}>
                      <span className={anomalyData.is_anomaly ? 'badge badge-critical' : 'badge badge-low'}>
                        {anomalyData.is_anomaly ? 'FLAGGED OUTLIER' : 'NORMAL INLIER'}
                      </span>
                      <span style={{ fontSize: '0.82rem' }}>
                        Anomaly Score: <strong className="mono">{anomalyData.anomaly_score.toFixed(4)}</strong>
                      </span>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                      The unsupervised Isolation Forest model evaluated multidimensional transaction flow, fee ratios, and connectivity distributions. Scores above the decision threshold indicate statistical divergence from standard peer behavior.
                    </div>
                  </div>
                ) : (
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                    ML anomaly scoring has not been executed for this entity.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 5: BEHAVIORAL INDICATORS */}
          {activeTab === 'behavior' && (
            <div>
              {entityBehaviors.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  No deterministic behavioral patterns detected for this entity.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {entityBehaviors.map((b) => (
                    <div key={b.detection_id} className="card" style={{ padding: '0.9rem 1rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                        <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--cyber-blue)' }}>
                          {b.detection_type.replace(/_/g, ' ').toUpperCase()}
                        </span>
                        <span className={`badge badge-${b.severity_indicator.toLowerCase()}`}>
                          {b.severity_indicator}
                        </span>
                      </div>
                      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', margin: '0 0 0.4rem 0' }}>
                        {b.explanation}
                      </p>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        Confidence: {Math.round(b.confidence * 100)}% • Supporting Transactions: {b.supporting_transaction_ids.length}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 6: NETWORK TELEMETRY */}
          {activeTab === 'network' && (
            <div>
              <div
                style={{
                  background: 'rgba(2, 132, 199, 0.08)',
                  border: '1px solid rgba(2, 132, 199, 0.25)',
                  borderRadius: '6px',
                  padding: '0.65rem 0.85rem',
                  fontSize: '0.75rem',
                  color: 'var(--text-secondary)',
                  marginBottom: '1rem',
                }}
              >
                {t('network_disclaimer')}
              </div>

              <div className="card">
                <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem' }}>
                  Observed Network Endpoints ({observedIPs.length})
                </h4>
                {observedIPs.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    No network layer IP metadata was recorded for this entity in the dataset.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                    {observedIPs.map((ip) => (
                      <span
                        key={ip}
                        className="mono"
                        style={{
                          fontSize: '0.75rem',
                          background: 'var(--bg-elevated)',
                          border: '1px solid var(--border-medium)',
                          padding: '0.2rem 0.5rem',
                          borderRadius: '4px',
                          color: 'var(--cyber-cyan)',
                        }}
                      >
                        {ip}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 7: EVIDENCE & METHODOLOGY */}
          {activeTab === 'evidence' && (
            <div>
              <div className="card" style={{ marginBottom: '1rem' }}>
                <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem', color: 'var(--cyber-blue)' }}>
                  Multi-Pipeline Evidence Contributions
                </h4>
                {riskData ? (
                  <div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {Object.entries(riskData.evidence_contributions).map(([source, contrib]) => (
                        <div
                          key={source}
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            background: 'var(--bg-elevated)',
                            padding: '0.45rem 0.75rem',
                            borderRadius: '4px',
                            border: '1px solid var(--border-subtle)',
                            fontSize: '0.78rem',
                          }}
                        >
                          <span style={{ textTransform: 'capitalize' }}>{source.replace(/_/g, ' ')}</span>
                          <span className="mono" style={{ color: contrib.points > 0 ? 'var(--cyber-blue)' : 'var(--text-muted)' }}>
                            {contrib.points.toFixed(1)} / {contrib.max_points} pts
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    Risk evidence has not yet been computed for this entity.
                  </div>
                )}
              </div>

              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Forensic standard: All risk indicators represent investigative prioritization hypotheses. They do not constitute legal proof of culpability.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
