import React, { useState } from 'react';
import {
  DBSCANClusteringResult,
  runClustering,
} from '../services/api';
import { CopyButton } from '../components/CopyButton';

interface BehavioralClustersViewProps {
  datasetId: string;
  clusterResult: DBSCANClusteringResult | null;
  onRefreshClusters: () => Promise<void>;
  onSelectEntity: (type: 'wallet' | 'transaction' | 'ip', id: string) => void;
}

export const BehavioralClustersView: React.FC<BehavioralClustersViewProps> = ({
  datasetId,
  clusterResult,
  onRefreshClusters,
  onSelectEntity,
}) => {
  const [eps, setEps] = useState<number>(0.5);
  const [minSamples, setMinSamples] = useState<number>(2);
  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [runSuccess, setRunSuccess] = useState<string | null>(null);

  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null);

  const handleRunClustering = async () => {
    setIsRunning(true);
    setRunError(null);
    setRunSuccess(null);
    try {
      const res = await runClustering(datasetId, eps, minSamples);
      setRunSuccess(`DBSCAN identified ${res.cluster_count} behavioral clusters and ${res.noise_count} noise outliers.`);
      await onRefreshClusters();
      if (res.clusters.length > 0) {
        setSelectedClusterId(res.clusters[0].cluster_id);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setRunError(err.message);
      } else {
        setRunError('DBSCAN execution failed.');
      }
    } finally {
      setIsRunning(false);
    }
  };

  const clusters = clusterResult?.clusters || [];
  const activeCluster = clusters.find((c) => c.cluster_id === selectedClusterId);

  // Entities matching selected cluster
  const memberEntities = clusterResult?.entities.filter((e) => {
    if (selectedClusterId === -1) {
      return e.is_noise;
    }
    return e.cluster_id === selectedClusterId;
  }) || [];

  return (
    <div>
      {/* Header */}
      <div className="view-header">
        <div>
          <h1 className="view-title">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2">
              <circle cx="12" cy="12" r="3"></circle>
              <circle cx="19" cy="5" r="2"></circle>
              <circle cx="5" cy="19" r="2"></circle>
              <circle cx="5" cy="5" r="2"></circle>
              <circle cx="19" cy="19" r="2"></circle>
            </svg>
            Behavioral Entity Clustering (DBSCAN)
          </h1>
          <p className="view-subtitle">
            Density-Based Spatial Clustering of Applications with Noise (DBSCAN) discovers behavioral cohorts across transaction velocity and graph connectivity while preserving statistical noise (-1).
          </p>
        </div>
      </div>

      {runError && (
        <div style={{ marginBottom: '1.25rem', background: '#3b1010', border: '1px solid #991b1b', color: '#fca5a5', padding: '0.75rem', borderRadius: '6px', fontSize: '0.82rem' }}>
          {runError}
        </div>
      )}
      {runSuccess && (
        <div style={{ marginBottom: '1.25rem', background: '#091c15', border: '1px solid #059669', color: '#6ee7b7', padding: '0.75rem', borderRadius: '6px', fontSize: '0.82rem' }}>
          {runSuccess}
        </div>
      )}

      {/* DBSCAN Configuration Controls */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h3 className="card-title">DBSCAN Hyperparameters</h3>
        <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Epsilon */}
          <div style={{ minWidth: '180px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
              <span>Epsilon (eps):</span>
              <strong className="mono" style={{ color: '#38bdf8' }}>{eps.toFixed(2)}</strong>
            </div>
            <input
              type="range"
              className="input-range"
              min="0.1"
              max="2.0"
              step="0.05"
              value={eps}
              onChange={(e) => setEps(parseFloat(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>

          {/* Min Samples */}
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.3rem' }}>
              Min Samples:
            </label>
            <input
              type="number"
              min="2"
              max="20"
              value={minSamples}
              onChange={(e) => setMinSamples(parseInt(e.target.value) || 2)}
              style={{ width: '80px' }}
            />
          </div>

          <div style={{ alignSelf: 'flex-end' }}>
            <button
              className="btn-primary"
              onClick={handleRunClustering}
              disabled={isRunning}
            >
              {isRunning ? 'Running DBSCAN...' : 'Run DBSCAN Clustering'}
            </button>
          </div>
        </div>

        <div style={{ marginTop: '0.85rem', fontSize: '0.75rem', color: '#64748b' }}>
          Features are scaled with <code className="mono">StandardScaler</code> across 7 normalized dimensions: transaction count, sent volume, received volume, net flow, degree, fan-in, and fan-out.
        </div>
      </div>

      {/* Cluster Overview KPIs */}
      {clusterResult && (
        <div className="grid-cols-4" style={{ marginBottom: '1.5rem' }}>
          <div className="kpi-card">
            <div className="kpi-label">Clusters Identified</div>
            <div className="kpi-value" style={{ color: '#a855f7' }}>{clusterResult.cluster_count}</div>
            <div className="kpi-subtext">Dense behavioral cohorts</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Clustered Wallets</div>
            <div className="kpi-value" style={{ color: '#34d399' }}>{clusterResult.clustered_count}</div>
            <div className="kpi-subtext">Assigned to cohorts</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Noise / Outliers (-1)</div>
            <div className="kpi-value" style={{ color: clusterResult.noise_count > 0 ? '#fbbf24' : '#94a3b8' }}>
              {clusterResult.noise_count}
            </div>
            <div className="kpi-subtext">Low-density isolated nodes</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-label">Total Evaluated</div>
            <div className="kpi-value">{clusterResult.total_entities}</div>
            <div className="kpi-subtext">Wallet addresses</div>
          </div>
        </div>
      )}

      {/* Cluster Explorer */}
      {!clusterResult ? (
        <div className="empty-state">
          <div className="empty-title">Clustering Not Yet Executed</div>
          <p className="empty-desc">Run DBSCAN above to group entities with similar topological and volume patterns.</p>
        </div>
      ) : (
        <div className="grid-cols-3">
          {/* Cluster Selector List */}
          <div className="card" style={{ height: 'fit-content' }}>
            <h3 className="card-title">Discovered Cohorts</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              {clusters.map((c) => (
                <button
                  key={c.cluster_id}
                  className={`nav-item ${selectedClusterId === c.cluster_id ? 'active' : ''}`}
                  onClick={() => setSelectedClusterId(c.cluster_id)}
                  style={{ justifyContent: 'space-between' }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span className="badge badge-purple">Cluster #{c.cluster_id}</span>
                  </span>
                  <span className="mono" style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                    {c.member_count} wallets
                  </span>
                </button>
              ))}

              {clusterResult.noise_count > 0 && (
                <button
                  className={`nav-item ${selectedClusterId === -1 ? 'active' : ''}`}
                  onClick={() => setSelectedClusterId(-1)}
                  style={{ justifyContent: 'space-between' }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span className="badge badge-moderate">Noise Outliers</span>
                  </span>
                  <span className="mono" style={{ fontSize: '0.78rem', color: '#fbbf24' }}>
                    {clusterResult.noise_count} wallets
                  </span>
                </button>
              )}
            </div>
          </div>

          {/* Member Details & Profile */}
          <div className="card" style={{ gridColumn: 'span 2' }}>
            <h3 className="card-title">
              {selectedClusterId === -1
                ? 'Statistical Noise Outliers (Cluster -1)'
                : activeCluster
                ? `Behavioral Profile: Cluster #${activeCluster.cluster_id}`
                : 'Select a Cluster'}
            </h3>

            {activeCluster && selectedClusterId !== -1 && (
              <div style={{ background: '#0b111e', padding: '0.85rem', borderRadius: '6px', border: '1px solid #1e293b', marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.82rem', color: '#cbd5e1', marginBottom: '0.65rem' }}>
                  {activeCluster.description}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.5rem', fontSize: '0.75rem' }}>
                  <div>
                    <span style={{ color: '#94a3b8' }}>Avg Sent: </span>
                    <strong className="mono">{activeCluster.avg_sent_btc.toFixed(4)} ₿</strong>
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8' }}>Avg Received: </span>
                    <strong className="mono">{activeCluster.avg_received_btc.toFixed(4)} ₿</strong>
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8' }}>Avg Fan-In: </span>
                    <strong className="mono" style={{ color: '#34d399' }}>{activeCluster.avg_fan_in.toFixed(1)}</strong>
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8' }}>Avg Fan-Out: </span>
                    <strong className="mono" style={{ color: '#f87171' }}>{activeCluster.avg_fan_out.toFixed(1)}</strong>
                  </div>
                </div>
              </div>
            )}

            {/* Member Wallets Table */}
            <div className="table-wrapper">
              <table className="cyber-table">
                <thead>
                  <tr>
                    <th>Member Wallet</th>
                    <th>Classification</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {memberEntities.map((m) => (
                    <tr key={m.address}>
                      <td className="mono" style={{ fontSize: '0.78rem' }}>
                        <span
                          className="clickable-entity"
                          onClick={() => onSelectEntity('wallet', m.address)}
                        >
                          {m.address}
                        </span>
                        <CopyButton text={m.address} />
                      </td>
                      <td>
                        <span className={`badge ${m.is_noise ? 'badge-moderate' : 'badge-purple'}`}>
                          {m.is_noise ? 'NOISE OUTLIER' : `CLUSTER #${m.cluster_id}`}
                        </span>
                      </td>
                      <td>
                        <button
                          className="btn-secondary"
                          style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem' }}
                          onClick={() => onSelectEntity('wallet', m.address)}
                        >
                          Dossier
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
