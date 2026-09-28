import React, { useState, useEffect, useRef } from 'react';
import {
  WalletActivity,
  CorrelationRecord,
  NetworkObservation,
  IngestionMetadata,
} from '../services/api';

interface GlobalSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  wallets: WalletActivity[];
  correlations: CorrelationRecord[];
  networkObservations: NetworkObservation[];
  datasets: IngestionMetadata[];
  onSelectEntity: (type: 'wallet' | 'transaction' | 'ip', id: string) => void;
  onSelectDataset: (datasetId: string) => void;
}

export const GlobalSearchModal: React.FC<GlobalSearchModalProps> = ({
  isOpen,
  onClose,
  wallets,
  correlations,
  networkObservations,
  datasets,
  onSelectEntity,
  onSelectDataset,
}) => {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const q = query.trim().toLowerCase();

  // Search Wallets
  const matchedWallets = q
    ? wallets.filter((w) => w.address.toLowerCase().includes(q))
    : [];

  // Search TXIDs
  const matchedTxs = q
    ? correlations.filter((c) => c.txid && c.txid.toLowerCase().includes(q))
    : [];

  // Search IPs
  const matchedIps: string[] = [];
  if (q) {
    networkObservations.forEach((o) => {
      if (o.src_ip && o.src_ip.toLowerCase().includes(q) && !matchedIps.includes(o.src_ip)) {
        matchedIps.push(o.src_ip);
      }
      if (o.dst_ip && o.dst_ip.toLowerCase().includes(q) && !matchedIps.includes(o.dst_ip)) {
        matchedIps.push(o.dst_ip);
      }
    });
  }

  // Search Datasets
  const matchedDatasets = q
    ? datasets.filter((d) => d.dataset_id.toLowerCase().includes(q) || d.original_filename.toLowerCase().includes(q))
    : [];

  const totalMatches = matchedWallets.length + matchedTxs.length + matchedIps.length + matchedDatasets.length;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-dialog"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '650px', maxHeight: '70vh' }}
      >
        <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid #1e293b', background: '#0b111e' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input
              ref={inputRef}
              type="text"
              placeholder="Search Wallets, Transactions, IP peers, or Dataset IDs..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#f8fafc',
                fontSize: '0.95rem',
                width: '100%',
                outline: 'none',
                fontFamily: 'ui-monospace, monospace',
              }}
            />
            <span style={{ fontSize: '0.7rem', color: '#64748b', background: '#1e293b', padding: '2px 6px', borderRadius: '4px' }}>
              ESC
            </span>
          </div>
        </div>

        <div className="modal-body" style={{ padding: '0.75rem 1.25rem' }}>
          {!q ? (
            <div style={{ padding: '2rem 1rem', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
              Type an address, TXID hash, IP address, or dataset name to locate entities across the active investigation scope.
            </div>
          ) : totalMatches === 0 ? (
            <div style={{ padding: '2rem 1rem', textAlign: 'center', color: '#64748b', fontSize: '0.85rem' }}>
              No entities found matching <strong style={{ color: '#94a3b8' }}>"{query}"</strong> in the active dataset.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Wallets */}
              {matchedWallets.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em', marginBottom: '0.4rem' }}>
                    Wallets ({matchedWallets.length})
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                    {matchedWallets.slice(0, 5).map((w) => (
                      <div
                        key={w.address}
                        onClick={() => {
                          onSelectEntity('wallet', w.address);
                          onClose();
                        }}
                        style={{
                          padding: '0.5rem 0.75rem',
                          background: '#0f172a',
                          border: '1px solid #1e293b',
                          borderRadius: '6px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          cursor: 'pointer',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#38bdf8')}
                        onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#1e293b')}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className="badge badge-cyan">Wallet</span>
                          <span className="mono" style={{ fontSize: '0.82rem', color: '#f8fafc' }}>
                            {w.address}
                          </span>
                        </div>
                        <span style={{ fontSize: '0.75rem', color: '#34d399' }}>
                          {w.net_flow >= 0 ? `+${w.net_flow.toFixed(4)}` : w.net_flow.toFixed(4)} ₿
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Transactions */}
              {matchedTxs.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em', marginBottom: '0.4rem' }}>
                    Transactions ({matchedTxs.length})
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                    {matchedTxs.slice(0, 5).map((tx) => (
                      <div
                        key={tx.txid || ''}
                        onClick={() => {
                          if (tx.txid) {
                            onSelectEntity('transaction', tx.txid);
                            onClose();
                          }
                        }}
                        style={{
                          padding: '0.5rem 0.75rem',
                          background: '#0f172a',
                          border: '1px solid #1e293b',
                          borderRadius: '6px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          cursor: 'pointer',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#a855f7')}
                        onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#1e293b')}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className="badge badge-purple">Transaction</span>
                          <span className="mono" style={{ fontSize: '0.82rem', color: '#f8fafc' }}>
                            {tx.txid ? `${tx.txid.slice(0, 24)}...` : 'N/A'}
                          </span>
                        </div>
                        <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                          {tx.timestamp ? tx.timestamp.slice(0, 10) : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* IPs */}
              {matchedIps.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em', marginBottom: '0.4rem' }}>
                    Network IPs ({matchedIps.length})
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                    {matchedIps.slice(0, 5).map((ip) => (
                      <div
                        key={ip}
                        onClick={() => {
                          onSelectEntity('ip', ip);
                          onClose();
                        }}
                        style={{
                          padding: '0.5rem 0.75rem',
                          background: '#0f172a',
                          border: '1px solid #1e293b',
                          borderRadius: '6px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          cursor: 'pointer',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#10b981')}
                        onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#1e293b')}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className="badge badge-low">Network IP</span>
                          <span className="mono" style={{ fontSize: '0.82rem', color: '#f8fafc' }}>
                            {ip}
                          </span>
                        </div>
                        <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Peer Observation</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Datasets */}
              {matchedDatasets.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em', marginBottom: '0.4rem' }}>
                    Datasets ({matchedDatasets.length})
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                    {matchedDatasets.slice(0, 3).map((d) => (
                      <div
                        key={d.dataset_id}
                        onClick={() => {
                          onSelectDataset(d.dataset_id);
                          onClose();
                        }}
                        style={{
                          padding: '0.5rem 0.75rem',
                          background: '#0f172a',
                          border: '1px solid #1e293b',
                          borderRadius: '6px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          cursor: 'pointer',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#f59e0b')}
                        onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#1e293b')}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span className="badge badge-moderate">Dataset</span>
                          <span style={{ fontSize: '0.82rem', color: '#f8fafc' }}>
                            {d.original_filename}
                          </span>
                        </div>
                        <span className="mono" style={{ fontSize: '0.7rem', color: '#64748b' }}>
                          {d.dataset_id.slice(0, 8)}...
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
