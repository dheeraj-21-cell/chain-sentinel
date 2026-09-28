import React from 'react';
import { CopyButton } from './CopyButton';
import {
  WalletActivity,
  CorrelationRecord,
  RiskFinding,
  BehavioralFinding,
  AnomalyScoreItem,
  WalletGraphMetrics,
  WalletClusterItem,
  NetworkObservation,
} from '../services/api';

// Verified behavioral pattern abbreviations from backend services/behavioral_detection.py
export const PATTERN_META: Record<
  string,
  { abbr: string; name: string; description: string; why: string }
> = {
  fan_in: {
    abbr: 'FI',
    name: 'Fan-In',
    description: 'Multiple incoming transaction relationships converge on an entity.',
    why: 'Incoming funding was received from multiple distinct input addresses across transactions.',
  },
  fan_out: {
    abbr: 'FO',
    name: 'Fan-Out',
    description: 'One entity connects to multiple outgoing destinations.',
    why: 'Funds were distributed to multiple distinct output destinations across transactions.',
  },
  transaction_burst: {
    abbr: 'TB',
    name: 'Transaction Burst',
    description: 'Multiple transactions occurred within a short time window.',
    why: 'High-density cluster of transactions exceeded the configured burst threshold.',
  },
  rapid_dispersion: {
    abbr: 'RD',
    name: 'Rapid Dispersion',
    description: 'Funds/transaction relationships disperse rapidly across multiple destinations.',
    why: 'Outflow occurred within a short observed time window following fund arrival.',
  },
  multi_hop_movement: {
    abbr: 'MH',
    name: 'Multi-Hop',
    description: 'Observed transaction relationships span multiple intermediary entities.',
    why: 'Directed flow traversed through consecutive intermediary transaction hops.',
  },
  peeling_chain_like: {
    abbr: 'PC',
    name: 'Peeling Chain',
    description: 'A sequential transaction structure resembling a peeling-chain pattern.',
    why: 'Sequential transactions showed asymmetric split outputs and continuation change addresses.',
  },
  dormant_to_active: {
    abbr: 'DA',
    name: 'Dormant-to-Active',
    description: 'Previously inactive entity becomes active after a period of inactivity.',
    why: 'Prolonged inactivity followed by renewed transaction activity.',
  },
};

export interface EntityInvestigationSummaryProps {
  entityType: 'wallet' | 'transaction' | 'ip' | 'asn' | 'country';
  entityId: string;
  datasetId: string;
  wallets?: WalletActivity[];
  correlations?: CorrelationRecord[];
  riskFindings?: RiskFinding[];
  behaviorFindings?: BehavioralFinding[];
  anomalies?: AnomalyScoreItem[];
  graphMetrics?: WalletGraphMetrics[];
  clusters?: WalletClusterItem[];
  networkObservations?: NetworkObservation[];
  compact?: boolean;
  onNavigateToGraph?: (entityId: string) => void;
  onSelectEntity?: (type: 'wallet' | 'transaction' | 'ip', id: string) => void;
}

export const EntityInvestigationSummary: React.FC<EntityInvestigationSummaryProps> = ({
  entityType,
  entityId,
  datasetId,
  wallets = [],
  correlations = [],
  riskFindings = [],
  behaviorFindings = [],
  anomalies = [],
  graphMetrics = [],
  clusters = [],
  networkObservations = [],
  compact = false,
  onNavigateToGraph,
  onSelectEntity,
}) => {
  // 1. Resolve entity records strictly from active dataset
  const walletData = wallets.find((w) => w.address === entityId);
  const txData = correlations.find((c) => c.txid === entityId);
  const riskData = riskFindings.find((r) => r.entity_id === entityId);
  const anomalyData = anomalies.find((a) => a.entity_id === entityId);
  const graphData = graphMetrics.find((g) => g.address === entityId);
  const clusterData = clusters.find((c) => c.address === entityId);

  // 2. Filter correlated transaction records involving this entity
  const associatedTxs = correlations.filter((c) => {
    if (entityType === 'wallet') {
      return (c.input_addresses && c.input_addresses.includes(entityId)) ||
             (c.output_addresses && c.output_addresses.includes(entityId));
    }
    if (entityType === 'transaction') {
      return c.txid === entityId;
    }
    if (entityType === 'ip') {
      return c.src_ip === entityId || c.dst_ip === entityId;
    }
    if (entityType === 'asn') {
      return c.asn?.toString() === entityId.replace(/^AS/i, '');
    }
    if (entityType === 'country') {
      return c.geo_country?.toUpperCase() === entityId.toUpperCase();
    }
    return false;
  });

  // 3. Extract unique observed IPs, Countries, ASNs from real transaction correlations
  const observedIPs = Array.from(
    new Set(
      associatedTxs
        .flatMap((tx) => [tx.src_ip, tx.dst_ip])
        .filter((ip): ip is string => Boolean(ip) && ip !== 'unknown' && ip !== '')
    )
  );

  const observedCountries = Array.from(
    new Set(
      associatedTxs
        .map((tx) => tx.geo_country)
        .filter((c): c is string => Boolean(c) && c !== 'unknown' && c !== '')
    )
  );

  const observedASNs = Array.from(
    new Set(
      associatedTxs
        .map((tx) => tx.asn)
        .filter((a): a is number => typeof a === 'number' && a > 0)
    )
  );

  // 4. Resolve behavioral findings linked to entity or its supporting txids
  const entityBehaviors = behaviorFindings.filter((b) => {
    if (b.entity_id === entityId) return true;
    if (b.supporting_transaction_ids && b.supporting_transaction_ids.includes(entityId)) return true;
    if (b.supporting_ips && b.supporting_ips.includes(entityId)) return true;
    return false;
  });

  // 5. Calculate Activity Timestamps and Duration
  const allTimestamps = associatedTxs
    .map((tx) => tx.timestamp)
    .filter((ts): ts is string => Boolean(ts))
    .sort();

  const firstSeen = allTimestamps[0] || null;
  const lastSeen = allTimestamps[allTimestamps.length - 1] || null;

  const calculateDuration = (first: string | null, last: string | null): string => {
    if (!first || !last) return 'Not available in dataset';
    try {
      const start = new Date(first.replace('Z', '+00:00')).getTime();
      const end = new Date(last.replace('Z', '+00:00')).getTime();
      const diffSec = Math.max(0, Math.floor((end - start) / 1000));
      if (diffSec === 0) return 'Single block / simultaneous';
      if (diffSec < 60) return `${diffSec} seconds`;
      if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ${diffSec % 60}s`;
      if (diffSec < 86400) return `${(diffSec / 3600).toFixed(1)} hours`;
      return `${(diffSec / 86400).toFixed(1)} days`;
    } catch {
      return 'Not available in dataset';
    }
  };

  const activityDuration = calculateDuration(firstSeen, lastSeen);

  // 6. Transaction Flow Breakdown
  const incomingTxs = associatedTxs.filter(
    (tx) => tx.output_addresses && tx.output_addresses.includes(entityId)
  );
  const outgoingTxs = associatedTxs.filter(
    (tx) => tx.input_addresses && tx.input_addresses.includes(entityId)
  );

  const incomingAmountSum = incomingTxs.reduce((sum, tx) => {
    let sub = 0;
    tx.output_addresses.forEach((addr, idx) => {
      if (addr === entityId && tx.output_amounts && tx.output_amounts[idx] !== undefined) {
        sub += Number(tx.output_amounts[idx]) || 0;
      }
    });
    return sum + sub;
  }, 0);

  const outgoingAmountSum = outgoingTxs.reduce((sum, tx) => {
    let sub = 0;
    tx.input_addresses.forEach((addr, idx) => {
      if (addr === entityId && tx.input_amounts && tx.input_amounts[idx] !== undefined) {
        sub += Number(tx.input_amounts[idx]) || 0;
      }
    });
    return sum + sub;
  }, 0);

  const totalIncomingBTC = walletData?.total_received !== undefined
    ? walletData.total_received
    : incomingAmountSum > 0 ? incomingAmountSum : null;

  const totalOutgoingBTC = walletData?.total_sent !== undefined
    ? walletData.total_sent
    : outgoingAmountSum > 0 ? outgoingAmountSum : null;

  // 7. Generate "Why prioritized?" Evidence Bullets (Part 5)
  const generateWhyPrioritizedBullets = (): string[] => {
    const bullets: string[] = [];

    // Fact: Transaction Volume
    if (associatedTxs.length > 0) {
      bullets.push(`${associatedTxs.length} transaction record(s) observed in the active dataset.`);
    }

    // Fact: Network Telemetry
    if (observedIPs.length > 0) {
      bullets.push(`${observedIPs.length} network observation(s) across ${observedCountries.length || 1} geographic location(s).`);
    }

    // Algorithmic: Behavioral Detectors
    if (entityBehaviors.length > 0) {
      const distinctTypes = Array.from(new Set(entityBehaviors.map((b) => b.detection_type)));
      distinctTypes.forEach((dtype) => {
        const meta = PATTERN_META[dtype];
        const label = meta ? `${meta.abbr} — ${meta.name}` : dtype.replace(/_/g, ' ');
        bullets.push(`Behavioral pattern detected: ${label}.`);
      });
    }

    // Algorithmic: Isolation Forest Outlier
    if (anomalyData?.is_anomaly) {
      bullets.push(
        `Isolation Forest anomaly detected (score: ${anomalyData.anomaly_score.toFixed(3)} relative to dataset baseline).`
      );
    }

    // Algorithmic: DBSCAN Clustering Status
    if (clusterData) {
      if (clusterData.is_noise) {
        bullets.push('DBSCAN identified entity as an isolated topological outlier (noise).');
      } else {
        bullets.push(`DBSCAN grouped entity into structural cluster #${clusterData.cluster_id}.`);
      }
    }

    // Algorithmic: Graph Connectivity
    if (graphData && graphData.degree > 2) {
      bullets.push(`Graph degree elevated: connected to ${graphData.degree} on-chain entities.`);
    }

    // Explicit Risk Engine Rationale
    if (riskData?.explanation) {
      bullets.push(`Risk scoring engine rationale: ${riskData.explanation}`);
    }

    if (bullets.length === 0) {
      bullets.push('Baseline on-chain ledger activity with no anomalous indicators flagged.');
    }

    return bullets;
  };

  const whyBullets = generateWhyPrioritizedBullets();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.82rem' }}>
      {/* ---------------------------------------------------------------- */}
      {/* HEADER: ENTITY INVESTIGATION SUMMARY */}
      {/* ---------------------------------------------------------------- */}
      <div
        style={{
          borderBottom: '1px solid var(--border-medium)',
          paddingBottom: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
          <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.06em' }}>
            ENTITY INVESTIGATION SUMMARY
          </span>
          {riskData ? (
            <span className={`badge badge-${riskData.priority.toLowerCase()}`}>
              {riskData.priority} PRIORITY ({riskData.score.toFixed(1)}/100)
            </span>
          ) : (
            <span className="badge badge-neutral">UNSCORED</span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span className="badge badge-cyan">{entityType.toUpperCase()}</span>
          <span className="mono" style={{ fontWeight: 700, color: 'var(--cyber-blue)', fontSize: '0.88rem', wordBreak: 'break-all' }}>
            {entityId}
          </span>
          <CopyButton text={entityId} />
          {onNavigateToGraph && (
            <button
              className="btn-secondary"
              style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
              onClick={() => onNavigateToGraph(entityId)}
            >
              View on Graph →
            </button>
          )}
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* SECTION 1: WHY PRIORITIZED? (Part 5) */}
      {/* ---------------------------------------------------------------- */}
      <div
        className="card"
        style={{
          background: 'rgba(245, 158, 11, 0.05)',
          border: '1px solid rgba(245, 158, 11, 0.3)',
          padding: '0.85rem 1rem',
          borderRadius: '6px',
        }}
      >
        <div
          style={{
            fontSize: '0.74rem',
            fontWeight: 700,
            color: 'var(--cyber-amber)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: '0.45rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
          }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
          </svg>
          Why prioritized?
        </div>
        <ul style={{ margin: 0, paddingLeft: '1.2rem', color: 'var(--text-primary)', lineHeight: 1.55 }}>
          {whyBullets.map((bullet, idx) => (
            <li key={idx} style={{ marginBottom: '0.25rem' }}>
              {bullet}
            </li>
          ))}
        </ul>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* SECTION 2: TRANSACTION ACTIVITY SUMMARY (Part 6) */}
      {/* ---------------------------------------------------------------- */}
      <div className="card" style={{ padding: '0.85rem 1rem', background: 'var(--bg-elevated)' }}>
        <div style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.6rem', textTransform: 'uppercase' }}>
          Transaction Activity Summary
        </div>

        {entityType === 'wallet' && (
          <div style={{ display: 'grid', gridTemplateColumns: compact ? '1fr' : 'repeat(2, 1fr)', gap: '0.5rem', fontSize: '0.76rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Total Transactions: </span>
              <strong>{walletData?.tx_count ?? associatedTxs.length}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Incoming Transactions: </span>
              <strong>{incomingTxs.length}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Outgoing Transactions: </span>
              <strong>{outgoingTxs.length}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Activity Duration: </span>
              <strong>{activityDuration}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Total Incoming: </span>
              <strong className="mono" style={{ color: 'var(--cyber-emerald)' }}>
                {totalIncomingBTC !== null ? `${totalIncomingBTC.toFixed(4)} ₿` : 'Not available in dataset'}
              </strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Total Outgoing: </span>
              <strong className="mono" style={{ color: 'var(--cyber-crimson)' }}>
                {totalOutgoingBTC !== null ? `${totalOutgoingBTC.toFixed(4)} ₿` : 'Not available in dataset'}
              </strong>
            </div>
            <div style={{ gridColumn: compact ? 'auto' : 'span 2' }}>
              <span style={{ color: 'var(--text-muted)' }}>First Seen: </span>
              <span className="mono" style={{ color: 'var(--text-secondary)' }}>
                {firstSeen || 'Not available in dataset'}
              </span>
            </div>
            <div style={{ gridColumn: compact ? 'auto' : 'span 2' }}>
              <span style={{ color: 'var(--text-muted)' }}>Last Seen: </span>
              <span className="mono" style={{ color: 'var(--text-secondary)' }}>
                {lastSeen || 'Not available in dataset'}
              </span>
            </div>
          </div>
        )}

        {entityType === 'transaction' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '0.45rem', fontSize: '0.76rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Timestamp: </span>
              <span className="mono">{txData?.timestamp || 'Not available in dataset'}</span>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Total Output Amount: </span>
              <strong className="mono" style={{ color: 'var(--cyber-blue)' }}>
                {txData?.output_amounts && txData.output_amounts.length > 0
                  ? `${txData.output_amounts.reduce((a, b) => a + b, 0).toFixed(4)} ₿`
                  : 'Not available in dataset'}
              </strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Transaction Fee: </span>
              <span className="mono">
                {txData?.fee !== undefined && txData?.fee !== null ? `${txData.fee.toFixed(6)} ₿` : 'Not available in dataset'}
              </span>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Input Wallets ({txData?.input_addresses?.length || 0}): </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', marginTop: '0.2rem' }}>
                {txData?.input_addresses && txData.input_addresses.length > 0 ? (
                  txData.input_addresses.map((addr) => (
                    <span
                      key={addr}
                      className="mono clickable-entity"
                      style={{ fontSize: '0.7rem', background: 'var(--bg-darkest)', padding: '0.15rem 0.4rem', borderRadius: '3px' }}
                      onClick={() => onSelectEntity && onSelectEntity('wallet', addr)}
                    >
                      {addr.slice(0, 10)}...{addr.slice(-6)}
                    </span>
                  ))
                ) : (
                  <span style={{ color: 'var(--text-muted)' }}>Not available in dataset</span>
                )}
              </div>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Output Wallets ({txData?.output_addresses?.length || 0}): </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', marginTop: '0.2rem' }}>
                {txData?.output_addresses && txData.output_addresses.length > 0 ? (
                  txData.output_addresses.map((addr) => (
                    <span
                      key={addr}
                      className="mono clickable-entity"
                      style={{ fontSize: '0.7rem', background: 'var(--bg-darkest)', padding: '0.15rem 0.4rem', borderRadius: '3px' }}
                      onClick={() => onSelectEntity && onSelectEntity('wallet', addr)}
                    >
                      {addr.slice(0, 10)}...{addr.slice(-6)}
                    </span>
                  ))
                ) : (
                  <span style={{ color: 'var(--text-muted)' }}>Not available in dataset</span>
                )}
              </div>
            </div>
          </div>
        )}

        {entityType !== 'wallet' && entityType !== 'transaction' && (
          <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
            <div>Associated Transactions: <strong>{associatedTxs.length}</strong></div>
            <div>First Seen: <span className="mono">{firstSeen || 'Not available in dataset'}</span></div>
            <div>Last Seen: <span className="mono">{lastSeen || 'Not available in dataset'}</span></div>
          </div>
        )}
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* SECTION 3: NETWORK ACTIVITY SUMMARY (Part 7) */}
      {/* ---------------------------------------------------------------- */}
      <div className="card" style={{ padding: '0.85rem 1rem', background: 'var(--bg-elevated)' }}>
        <div style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.6rem', textTransform: 'uppercase' }}>
          Network Observations
        </div>

        {observedIPs.length === 0 ? (
          <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
            No network observations available in dataset.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.76rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Observed IP Addresses ({observedIPs.length}): </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', marginTop: '0.25rem' }}>
                {observedIPs.map((ip) => (
                  <span
                    key={ip}
                    className="mono clickable-entity"
                    style={{
                      fontSize: '0.72rem',
                      background: 'var(--bg-darkest)',
                      padding: '0.2rem 0.45rem',
                      borderRadius: '4px',
                      border: '1px solid var(--border-subtle)',
                      color: 'var(--cyber-purple)',
                    }}
                    onClick={() => onSelectEntity && onSelectEntity('ip', ip)}
                  >
                    {ip}
                  </span>
                ))}
              </div>
            </div>

            <div style={{ marginTop: '0.3rem', display: 'grid', gridTemplateColumns: compact ? '1fr' : 'repeat(2, 1fr)', gap: '0.4rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Countries Observed: </span>
                <strong>{observedCountries.length > 0 ? observedCountries.join(', ') : 'Not available in dataset'}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>ASNs Observed: </span>
                <strong>{observedASNs.length > 0 ? observedASNs.map((a) => `AS${a}`).join(', ') : 'Not available in dataset'}</strong>
              </div>
            </div>

            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
              Network observations correlated with {associatedTxs.length} transaction record(s) in active dataset
              {networkObservations.length > 0 ? ` across ${networkObservations.length} aggregated network observation clusters.` : '.'}
            </div>
          </div>
        )}
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* SECTION 4: UNUSUAL BEHAVIOR EXPLANATION (Parts 8 & 9) */}
      {/* ---------------------------------------------------------------- */}
      <div className="card" style={{ padding: '0.85rem 1rem', background: 'var(--bg-elevated)' }}>
        <div style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.6rem', textTransform: 'uppercase' }}>
          Behavioral Signals
        </div>

        {entityBehaviors.length === 0 ? (
          <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
            No behavioral pattern detected.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {entityBehaviors.map((b) => {
              const meta = PATTERN_META[b.detection_type];
              const abbr = meta?.abbr || 'PAT';
              const name = meta?.name || b.detection_type.replace(/_/g, ' ');

              return (
                <div
                  key={b.detection_id}
                  style={{
                    borderLeft: '3px solid var(--cyber-amber)',
                    paddingLeft: '0.65rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.2rem',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
                    <span className="badge badge-amber" style={{ fontWeight: 800 }}>
                      {abbr}
                    </span>
                    <strong style={{ color: 'var(--text-primary)', fontSize: '0.78rem' }}>{name}</strong>
                    <span className="badge badge-neutral" style={{ fontSize: '0.65rem' }}>
                      {b.severity_indicator.toUpperCase()}
                    </span>
                    <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                      Conf: {(b.confidence * 100).toFixed(0)}%
                    </span>
                  </div>

                  <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                    <strong>Observed: </strong>
                    {b.explanation || meta?.description}
                  </div>

                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    <strong>Why flagged: </strong>
                    {meta?.why || 'Detector rules triggered based on observed transaction relationships.'}
                  </div>

                  {b.supporting_transaction_ids && b.supporting_transaction_ids.length > 0 && (
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      Supporting transactions: {b.supporting_transaction_ids.length} txid(s)
                    </div>
                  )}

                  <div style={{ fontSize: '0.68rem', color: 'var(--cyber-blue)', fontStyle: 'italic', marginTop: '0.1rem' }}>
                    This is an investigative signal and requires investigator review.
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* SECTION 5: MACHINE LEARNING SIGNALS (Part 10) */}
      {/* ---------------------------------------------------------------- */}
      <div className="card" style={{ padding: '0.85rem 1rem', background: 'var(--bg-elevated)' }}>
        <div style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.6rem', textTransform: 'uppercase' }}>
          Machine Learning Signals
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.76rem' }}>
          {/* Isolation Forest */}
          <div style={{ borderLeft: '3px solid var(--cyber-blue)', paddingLeft: '0.6rem' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
              Isolation Forest: {anomalyData ? (anomalyData.is_anomaly ? 'Outlier Detected' : 'Normal Baseline') : 'Not available in dataset'}
            </div>
            {anomalyData ? (
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                <div>Anomaly Score: <strong className="mono">{anomalyData.anomaly_score.toFixed(4)}</strong></div>
                <div>Model: Isolation Forest Unsupervised Outlier Detector</div>
                <div style={{ color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                  {anomalyData.is_anomaly
                    ? 'The entity/transaction was identified as unusual relative to the modeled dataset behavior.'
                    : 'Transaction metrics adhere to standard multivariate distributions.'}
                </div>
              </div>
            ) : (
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                No ML anomaly result available in dataset.
              </div>
            )}
          </div>

          {/* DBSCAN */}
          <div style={{ borderLeft: '3px solid var(--cyber-purple)', paddingLeft: '0.6rem' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
              DBSCAN Spatial Clustering:{' '}
              {clusterData ? (clusterData.is_noise ? 'Noise Point (-1)' : `Cluster #${clusterData.cluster_id}`) : 'Not available in dataset'}
            </div>
            {clusterData ? (
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                <div style={{ color: 'var(--text-muted)' }}>
                  {clusterData.is_noise
                    ? 'Entity does not belong to a dense structural cluster and was marked as an isolated topological outlier.'
                    : `Entity belongs to dense topological community #${clusterData.cluster_id}.`}
                </div>
              </div>
            ) : (
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                No clustering result available in dataset.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* SECTION 6: RISK SCORE CONTRIBUTING SIGNALS (Part 11) */}
      {/* ---------------------------------------------------------------- */}
      {riskData && riskData.evidence_contributions && (
        <div className="card" style={{ padding: '0.85rem 1rem', background: 'var(--bg-elevated)' }}>
          <div style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.6rem', textTransform: 'uppercase' }}>
            Contributing Risk Signals ({riskData.priority})
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', fontSize: '0.74rem' }}>
            {Object.entries(riskData.evidence_contributions).map(([src, contrib]) => (
              <div
                key={src}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  background: 'var(--bg-darkest)',
                  padding: '0.35rem 0.6rem',
                  borderRadius: '4px',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div>
                  <span style={{ textTransform: 'capitalize', color: 'var(--text-secondary)', fontWeight: 600 }}>
                    {src.replace(/_/g, ' ')}
                  </span>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{contrib.rationale}</div>
                </div>
                <strong className="mono" style={{ color: contrib.points > 0 ? 'var(--cyber-blue)' : 'var(--text-muted)' }}>
                  {contrib.points.toFixed(1)} / {contrib.max_points}
                </strong>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* SECTION 7: TRIPARTITE FORENSIC SEPARATION (Parts 12 & 13) */}
      {/* ---------------------------------------------------------------- */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.25rem' }}>
        <div
          style={{
            background: 'rgba(56, 189, 248, 0.05)',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            borderRadius: '6px',
            padding: '0.6rem 0.8rem',
            fontSize: '0.72rem',
          }}
        >
          <div style={{ fontWeight: 700, color: 'var(--cyber-blue)', marginBottom: '0.2rem' }}>
            [OBSERVED FACTS]
          </div>
          <div style={{ color: 'var(--text-secondary)', lineHeight: 1.45 }}>
            {associatedTxs.length} transaction(s) and {observedIPs.length} network observation(s) recorded in active dataset {datasetId.slice(0, 8)}...
          </div>
        </div>

        <div
          style={{
            background: 'rgba(168, 85, 247, 0.05)',
            border: '1px solid rgba(168, 85, 247, 0.25)',
            borderRadius: '6px',
            padding: '0.6rem 0.8rem',
            fontSize: '0.72rem',
          }}
        >
          <div style={{ fontWeight: 700, color: 'var(--cyber-purple)', marginBottom: '0.2rem' }}>
            [MODEL INTERPRETATION]
          </div>
          <div style={{ color: 'var(--text-secondary)', lineHeight: 1.45 }}>
            Algorithmic anomaly and behavioral detectors prioritize this entity based on empirical deviations from dataset baselines.
          </div>
        </div>

        <div
          style={{
            background: 'rgba(245, 158, 11, 0.05)',
            border: '1px solid rgba(245, 158, 11, 0.25)',
            borderRadius: '6px',
            padding: '0.6rem 0.8rem',
            fontSize: '0.72rem',
          }}
        >
          <div style={{ fontWeight: 700, color: 'var(--cyber-amber)', marginBottom: '0.2rem' }}>
            [INVESTIGATOR HYPOTHESIS]
          </div>
          <div style={{ color: 'var(--text-secondary)', lineHeight: 1.45 }}>
            Topological patterns suggest structured on-chain movement requiring manual correlation with corroborating off-chain intelligence.
          </div>
        </div>

        <div
          style={{
            fontSize: '0.68rem',
            color: 'var(--text-muted)',
            lineHeight: 1.4,
            padding: '0.4rem 0.2rem',
            fontStyle: 'italic',
          }}
        >
          Graph relationships represent observed/correlated evidence from the selected dataset; they do not by themselves establish ownership or criminal attribution.
        </div>
      </div>
    </div>
  );
};
