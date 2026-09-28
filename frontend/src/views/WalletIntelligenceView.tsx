import React, { useState } from 'react';
import {
  WalletActivity,
  WalletGraphMetrics,
  WalletClusterItem,
  RiskFinding,
  AnomalyScoreItem,
  BehavioralFinding,
} from '../services/api';
import { CopyButton } from '../components/CopyButton';
import { PATTERN_META } from '../components/EntityInvestigationSummary';
import { useI18n } from '../services/i18n';

interface WalletIntelligenceViewProps {
  wallets: WalletActivity[];
  graphMetrics: WalletGraphMetrics[];
  clusters: WalletClusterItem[];
  riskFindings: RiskFinding[];
  anomalies?: AnomalyScoreItem[];
  behaviorFindings?: BehavioralFinding[];
  onSelectEntity: (type: 'wallet' | 'transaction' | 'ip', id: string) => void;
  isLoading: boolean;
}

export const WalletIntelligenceView: React.FC<WalletIntelligenceViewProps> = ({
  wallets,
  graphMetrics,
  clusters,
  riskFindings,
  anomalies = [],
  behaviorFindings = [],
  onSelectEntity,
  isLoading,
}) => {
  const { t } = useI18n();
  const [searchTerm, setSearchTerm] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('ALL');
  const [viewLayout, setViewLayout] = useState<'cards' | 'table'>('cards');

  const graphMap = new Map(graphMetrics.map((g) => [g.address, g]));
  const clusterMap = new Map(clusters.map((c) => [c.address, c]));
  const riskMap = new Map(riskFindings.map((r) => [r.entity_id, r]));
  const anomalyMap = new Map(anomalies.map((a) => [a.entity_id, a]));

  const filtered = wallets.filter((w) => {
    if (searchTerm && !w.address.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    if (priorityFilter !== 'ALL') {
      const r = riskMap.get(w.address);
      if (!r || r.priority !== priorityFilter) return false;
    }
    return true;
  });

  // Helper to generate concise "Why Prioritized" explanation bullets
  const getWhyPrioritizedBullets = (
    address: string,
    w: WalletActivity,
    risk?: RiskFinding,
    isAnomaly?: boolean,
    deg?: number
  ): string[] => {
    const bullets: string[] = [];

    // 1. Risk explanation
    if (risk) {
      if (risk.explanation) {
        bullets.push(risk.explanation);
      } else {
        bullets.push(`Prioritized with risk score of ${risk.score.toFixed(1)} (${risk.priority})`);
      }
    }

    // 2. Behavioral detections
    const matchedBehaviors = behaviorFindings.filter(
      (b) => b.entity_id === address || b.supporting_transaction_ids.includes(address)
    );
    if (matchedBehaviors.length > 0) {
      const firstB = matchedBehaviors[0];
      const meta = PATTERN_META[firstB.detection_type];
      const label = meta ? `${meta.abbr} — ${meta.name}` : firstB.detection_type.replace(/_/g, ' ');
      bullets.push(`Pattern: ${label} (${firstB.severity_indicator})`);
    }

    // 3. ML Outlier
    if (isAnomaly) {
      bullets.push('Statistical outlier detected by Isolation Forest');
    }

    // 4. Connection degree
    if (deg && deg > 3) {
      bullets.push(`High topological connectivity (${deg} connected entities)`);
    }

    // 5. Volume / transaction activity
    if (w.tx_count > 5) {
      bullets.push(`Active participant across ${w.tx_count} transactions`);
    }

    // Fallback if low risk / baseline
    if (bullets.length === 0) {
      bullets.push('Baseline activity observed in dataset');
    }

    return bullets.slice(0, 3);
  };

  return (
    <div>
      {/* Header */}
      <div className="view-header">
        <div>
          <h1 className="view-title">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--cyber-emerald)" strokeWidth="2.2">
              <rect x="2" y="4" width="20" height="16" rx="2"></rect>
              <path d="M7 15h0M2 9.5h20"></path>
            </svg>
            {t('wallet_intel_title')}
          </h1>
          <p className="view-subtitle">{t('wallet_intel_subtitle')}</p>
        </div>

        {/* View Switcher Toggle */}
        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
          <button
            className={viewLayout === 'cards' ? 'btn-primary' : 'btn-secondary'}
            onClick={() => setViewLayout('cards')}
            style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}
          >
            Cards View
          </button>
          <button
            className={viewLayout === 'table' ? 'btn-primary' : 'btn-secondary'}
            onClick={() => setViewLayout('table')}
            style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}
          >
            Table View
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div
        className="card"
        style={{
          padding: '0.75rem 1rem',
          display: 'flex',
          gap: '0.75rem',
          alignItems: 'center',
          flexWrap: 'wrap',
          marginBottom: '1.25rem',
        }}
      >
        <div style={{ flex: 1, minWidth: '220px' }}>
          <input
            type="text"
            placeholder={t('search_wallet_placeholder')}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: '100%' }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Priority:</span>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            style={{ fontSize: '0.78rem', padding: '0.35rem 0.6rem' }}
          >
            <option value="ALL">{t('filter_all_priority')}</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MODERATE">Moderate</option>
            <option value="LOW">Low</option>
          </select>
        </div>

        <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
          {filtered.length} of {wallets.length} Wallets
        </span>
      </div>

      {/* Cards View Layout */}
      {viewLayout === 'cards' ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
            gap: '1rem',
          }}
        >
          {filtered.length === 0 ? (
            <div className="card" style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '3rem' }}>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                {isLoading ? 'Loading wallet directory...' : 'No wallets match your filter.'}
              </div>
            </div>
          ) : (
            filtered.map((w) => {
              const risk = riskMap.get(w.address);
              const g = graphMap.get(w.address);
              const c = clusterMap.get(w.address);
              const anom = anomalyMap.get(w.address);
              const isAnomaly = anom?.is_anomaly || false;
              const bullets = getWhyPrioritizedBullets(w.address, w, risk, isAnomaly, g?.degree);

              return (
                <div
                  key={w.address}
                  className="card"
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    border: risk?.priority === 'CRITICAL' ? '1px solid rgba(225, 29, 72, 0.4)' : undefined,
                  }}
                >
                  {/* Card Top: Address & Risk */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem', marginBottom: '0.6rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', minWidth: 0 }}>
                        <span
                          className="mono"
                          style={{
                            fontWeight: 700,
                            color: 'var(--cyber-blue)',
                            fontSize: '0.82rem',
                            wordBreak: 'break-all',
                          }}
                          title={w.address}
                        >
                          {w.address.slice(0, 10)}...{w.address.slice(-8)}
                        </span>
                        <CopyButton text={w.address} />
                      </div>

                      {risk ? (
                        <span className={`badge badge-${risk.priority.toLowerCase()}`}>
                          {risk.priority} ({risk.score.toFixed(0)})
                        </span>
                      ) : (
                        <span className="badge badge-neutral">UNSCORED</span>
                      )}
                    </div>

                    {/* Why Prioritized Section */}
                    <div
                      style={{
                        background: 'var(--bg-elevated)',
                        borderRadius: '6px',
                        padding: '0.6rem 0.8rem',
                        marginBottom: '0.85rem',
                        border: '1px solid var(--border-subtle)',
                      }}
                    >
                      <div
                        style={{
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          color: 'var(--cyber-amber)',
                          textTransform: 'uppercase',
                          letterSpacing: '0.04em',
                          marginBottom: '0.35rem',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.3rem',
                        }}
                      >
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                        </svg>
                        {t('why_prioritized')}
                      </div>
                      <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        {bullets.map((b, idx) => (
                          <li key={idx} style={{ marginBottom: '0.15rem' }}>
                            {b}
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Quick Metrics Grid */}
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(2, 1fr)',
                        gap: '0.5rem',
                        fontSize: '0.74rem',
                        marginBottom: '0.85rem',
                      }}
                    >
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>{t('transactions_count')}: </span>
                        <strong style={{ color: 'var(--text-primary)' }}>{w.tx_count}</strong>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>{t('connections_count')}: </span>
                        <strong style={{ color: 'var(--text-primary)' }}>{g ? g.degree : '—'}</strong>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Net Flow: </span>
                        <strong className="mono" style={{ color: w.net_flow >= 0 ? 'var(--cyber-emerald)' : 'var(--cyber-crimson)' }}>
                          {w.net_flow.toFixed(3)} ₿
                        </strong>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Cluster: </span>
                        <strong style={{ color: 'var(--text-primary)' }}>
                          {c ? (c.is_noise ? 'Noise (-1)' : `C#${c.cluster_id}`) : '—'}
                        </strong>
                      </div>
                    </div>
                  </div>

                  {/* Card Action */}
                  <div
                    style={{
                      borderTop: '1px solid var(--border-subtle)',
                      paddingTop: '0.75rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div style={{ display: 'flex', gap: '0.3rem' }}>
                      {isAnomaly && <span className="badge badge-high" style={{ fontSize: '0.62rem' }}>ML ANOMALY</span>}
                      {c?.is_noise && <span className="badge badge-moderate" style={{ fontSize: '0.62rem' }}>NOISE</span>}
                    </div>

                    <button
                      className="btn-primary"
                      onClick={() => onSelectEntity('wallet', w.address)}
                      style={{ fontSize: '0.74rem', padding: '0.3rem 0.65rem' }}
                    >
                      {t('open_investigation')}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      ) : (
        /* Tabular Layout */
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div className="table-wrapper">
            <table className="cyber-table">
              <thead>
                <tr>
                  <th>Wallet Address</th>
                  <th>Priority / Risk</th>
                  <th>Why Prioritized</th>
                  <th>Txs</th>
                  <th>Degree</th>
                  <th>Net Flow (BTC)</th>
                  <th>Cluster</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((w) => {
                  const risk = riskMap.get(w.address);
                  const g = graphMap.get(w.address);
                  const c = clusterMap.get(w.address);
                  const bullets = getWhyPrioritizedBullets(w.address, w, risk, false, g?.degree);

                  return (
                    <tr key={w.address}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                          <span className="mono" style={{ color: 'var(--cyber-blue)', fontSize: '0.78rem' }}>
                            {w.address.slice(0, 8)}...{w.address.slice(-6)}
                          </span>
                          <CopyButton text={w.address} />
                        </div>
                      </td>
                      <td>
                        {risk ? (
                          <span className={`badge badge-${risk.priority.toLowerCase()}`}>
                            {risk.priority} ({risk.score.toFixed(0)})
                          </span>
                        ) : (
                          <span className="badge badge-neutral">UNSCORED</span>
                        )}
                      </td>
                      <td style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', maxWidth: '280px' }}>
                        {bullets[0]}
                      </td>
                      <td className="mono">{w.tx_count}</td>
                      <td className="mono">{g ? g.degree : '—'}</td>
                      <td className="mono" style={{ color: w.net_flow >= 0 ? 'var(--cyber-emerald)' : 'var(--cyber-crimson)' }}>
                        {w.net_flow.toFixed(3)}
                      </td>
                      <td>{c ? (c.is_noise ? 'Noise' : `Cluster ${c.cluster_id}`) : '—'}</td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          className="btn-secondary"
                          onClick={() => onSelectEntity('wallet', w.address)}
                          style={{ fontSize: '0.72rem', padding: '0.2rem 0.55rem' }}
                        >
                          Investigate →
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
