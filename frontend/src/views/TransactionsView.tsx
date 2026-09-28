import React, { useState } from 'react';
import { CorrelationRecord } from '../services/api';
import { CopyButton } from '../components/CopyButton';

interface TransactionsViewProps {
  correlations: CorrelationRecord[];
  onSelectEntity: (type: 'wallet' | 'transaction' | 'ip', id: string) => void;
  isLoading: boolean;
}

export const TransactionsView: React.FC<TransactionsViewProps> = ({
  correlations,
  onSelectEntity,
  isLoading,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [minAmount, setMinAmount] = useState<string>('');
  const [scriptFilter, setScriptFilter] = useState<string>('ALL');
  const [selectedTx, setSelectedTx] = useState<CorrelationRecord | null>(null);

  // Script types options
  const scriptTypes = Array.from(new Set(correlations.map((c) => c.script_type).filter(Boolean))) as string[];

  // Filter logic
  const filtered = correlations.filter((tx) => {
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      const matchTxid = tx.txid?.toLowerCase().includes(q);
      const matchInput = tx.input_addresses.some((a) => a.toLowerCase().includes(q));
      const matchOutput = tx.output_addresses.some((a) => a.toLowerCase().includes(q));
      if (!matchTxid && !matchInput && !matchOutput) return false;
    }

    if (minAmount) {
      const min = parseFloat(minAmount);
      if (!isNaN(min)) {
        const totalOut = tx.output_amounts.reduce((sum, a) => sum + a, 0);
        if (totalOut < min) return false;
      }
    }

    if (scriptFilter !== 'ALL' && tx.script_type !== scriptFilter) {
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
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2">
              <line x1="8" y1="6" x2="21" y2="6"></line>
              <line x1="8" y1="12" x2="21" y2="12"></line>
              <line x1="8" y1="18" x2="21" y2="18"></line>
              <line x1="3" y1="6" x2="3.01" y2="6"></line>
              <line x1="3" y1="12" x2="3.01" y2="12"></line>
              <line x1="3" y1="18" x2="3.01" y2="18"></line>
            </svg>
            Bitcoin Transaction Ledger
          </h1>
          <p className="view-subtitle">
            Inspect on-chain Bitcoin transaction UTXOs, input/output flow distributions, fees, script types, and network peer observations.
          </p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div
        style={{
          background: '#0f172a',
          border: '1px solid #1e293b',
          borderRadius: '8px',
          padding: '0.85rem 1rem',
          display: 'flex',
          gap: '1rem',
          alignItems: 'center',
          flexWrap: 'wrap',
          marginBottom: '1.25rem',
        }}
      >
        <div style={{ flex: 1, minWidth: '220px' }}>
          <input
            type="text"
            placeholder="Search by TXID or Wallet address..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: '100%' }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Min Volume:</span>
          <input
            type="number"
            placeholder="0.0 BTC"
            value={minAmount}
            onChange={(e) => setMinAmount(e.target.value)}
            style={{ width: '100px' }}
            step="0.1"
          />
        </div>

        {scriptTypes.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Script:</span>
            <select
              value={scriptFilter}
              onChange={(e) => setScriptFilter(e.target.value)}
              style={{ padding: '0.45rem 0.65rem' }}
            >
              <option value="ALL">All Scripts</option>
              {scriptTypes.map((st) => (
                <option key={st} value={st}>{st}</option>
              ))}
            </select>
          </div>
        )}

        <div style={{ fontSize: '0.78rem', color: '#64748b', marginLeft: 'auto' }}>
          Showing <strong>{filtered.length}</strong> of {correlations.length} transactions
        </div>
      </div>

      {/* Transactions Table */}
      {isLoading ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: '#38bdf8' }}>Loading ledger transactions...</div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-title">No Transactions Match Filters</div>
          <p className="empty-desc">Try clearing the search query or adjusting the volume filters.</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table className="cyber-table">
            <thead>
              <tr>
                <th>Transaction Hash (TXID)</th>
                <th>Timestamp</th>
                <th>Inputs (Sources)</th>
                <th>Outputs (Destinations)</th>
                <th>Total Out (BTC)</th>
                <th>Fee</th>
                <th>Script</th>
                <th>Network Peer</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((tx, idx) => {
                const totalOut = tx.output_amounts.reduce((sum, a) => sum + a, 0);
                return (
                  <tr key={idx}>
                    <td className="mono" style={{ fontSize: '0.78rem' }}>
                      <span
                        className="clickable-entity"
                        onClick={() => tx.txid && onSelectEntity('transaction', tx.txid)}
                      >
                        {tx.txid ? `${tx.txid.slice(0, 14)}...` : 'Coinbase'}
                      </span>
                      {tx.txid && <CopyButton text={tx.txid} />}
                    </td>

                    <td style={{ fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
                      {tx.timestamp ? tx.timestamp.slice(0, 19).replace('T', ' ') : 'N/A'}
                    </td>

                    <td style={{ fontSize: '0.75rem' }}>
                      {tx.input_addresses.length > 0 ? (
                        tx.input_addresses.slice(0, 2).map((addr, i) => (
                          <div key={i} className="mono">
                            <span
                              className="clickable-entity"
                              onClick={() => onSelectEntity('wallet', addr)}
                            >
                              {addr.slice(0, 8)}...
                            </span>{' '}
                            <span style={{ color: '#94a3b8' }}>({tx.input_amounts[i] ?? '?'} ₿)</span>
                          </div>
                        ))
                      ) : (
                        <span style={{ color: '#64748b' }}>Coinbase (Newly Mined)</span>
                      )}
                      {tx.input_addresses.length > 2 && (
                        <span style={{ color: '#64748b', fontSize: '0.7rem' }}>
                          +{tx.input_addresses.length - 2} more inputs
                        </span>
                      )}
                    </td>

                    <td style={{ fontSize: '0.75rem' }}>
                      {tx.output_addresses.length > 0 ? (
                        tx.output_addresses.slice(0, 2).map((addr, i) => (
                          <div key={i} className="mono">
                            <span
                              className="clickable-entity"
                              onClick={() => onSelectEntity('wallet', addr)}
                            >
                              {addr.slice(0, 8)}...
                            </span>{' '}
                            <span style={{ color: '#34d399' }}>({tx.output_amounts[i] ?? '?'} ₿)</span>
                          </div>
                        ))
                      ) : (
                        <span style={{ color: '#64748b' }}>None</span>
                      )}
                      {tx.output_addresses.length > 2 && (
                        <span style={{ color: '#64748b', fontSize: '0.7rem' }}>
                          +{tx.output_addresses.length - 2} more outputs
                        </span>
                      )}
                    </td>

                    <td className="mono" style={{ fontWeight: 600, color: '#f8fafc' }}>
                      {totalOut.toFixed(4)} ₿
                    </td>

                    <td className="mono" style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                      {tx.fee !== undefined && tx.fee !== null ? `${tx.fee} ₿` : '—'}
                    </td>

                    <td style={{ fontSize: '0.75rem' }}>
                      {tx.script_type ? (
                        <span className="badge badge-purple">{tx.script_type}</span>
                      ) : (
                        '—'
                      )}
                    </td>

                    <td className="mono" style={{ fontSize: '0.75rem' }}>
                      {tx.src_ip ? (
                        <span
                          className="clickable-entity"
                          onClick={() => onSelectEntity('ip', tx.src_ip!)}
                        >
                          {tx.src_ip}
                        </span>
                      ) : (
                        <span style={{ color: '#64748b' }}>—</span>
                      )}
                    </td>

                    <td>
                      <button
                        className="btn-secondary"
                        style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem' }}
                        onClick={() => setSelectedTx(tx)}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Transaction UTXO Inspection Modal */}
      {selectedTx && (
        <div className="modal-backdrop" onClick={() => setSelectedTx(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '750px' }}>
            <div className="modal-header">
              <h3 className="modal-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2">
                  <rect x="2" y="2" width="20" height="20" rx="4"></rect>
                  <line x1="12" y1="8" x2="12" y2="16"></line>
                  <line x1="8" y1="12" x2="16" y2="12"></line>
                </svg>
                Transaction UTXO Inspection
              </h3>
              <button className="btn-ghost" onClick={() => setSelectedTx(null)}>✕</button>
            </div>

            <div className="modal-body">
              <div style={{ marginBottom: '1rem', background: '#0b111e', padding: '0.75rem 1rem', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>TXID Hash</div>
                <div className="mono" style={{ fontSize: '0.85rem', color: '#f8fafc', wordBreak: 'break-all', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  {selectedTx.txid || 'Coinbase'}
                  {selectedTx.txid && <CopyButton text={selectedTx.txid} />}
                </div>
              </div>

              <div className="grid-cols-2" style={{ marginBottom: '1rem' }}>
                {/* Inputs Box */}
                <div className="card">
                  <h4 className="card-title" style={{ color: '#38bdf8' }}>
                    Inputs ({selectedTx.input_addresses.length})
                  </h4>
                  {selectedTx.input_addresses.length === 0 ? (
                    <div style={{ color: '#64748b', fontSize: '0.8rem' }}>Coinbase / No inputs</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      {selectedTx.input_addresses.map((addr, i) => (
                        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem' }}>
                          <span
                            className="mono clickable-entity"
                            onClick={() => {
                              setSelectedTx(null);
                              onSelectEntity('wallet', addr);
                            }}
                          >
                            {addr.slice(0, 14)}...
                          </span>
                          <span className="mono" style={{ color: '#cbd5e1' }}>
                            {selectedTx.input_amounts[i] ?? '?'} ₿
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Outputs Box */}
                <div className="card">
                  <h4 className="card-title" style={{ color: '#34d399' }}>
                    Outputs ({selectedTx.output_addresses.length})
                  </h4>
                  {selectedTx.output_addresses.length === 0 ? (
                    <div style={{ color: '#64748b', fontSize: '0.8rem' }}>No outputs</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      {selectedTx.output_addresses.map((addr, i) => (
                        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem' }}>
                          <span
                            className="mono clickable-entity"
                            onClick={() => {
                              setSelectedTx(null);
                              onSelectEntity('wallet', addr);
                            }}
                          >
                            {addr.slice(0, 14)}...
                          </span>
                          <span className="mono" style={{ color: '#34d399', fontWeight: 600 }}>
                            {selectedTx.output_amounts[i] ?? '?'} ₿
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Metadata row */}
              <div className="card">
                <h4 className="card-title">Metadata & Observation Telemetry</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.5rem', fontSize: '0.8rem' }}>
                  <div>
                    <span style={{ color: '#94a3b8' }}>Fee: </span>
                    <strong className="mono">{selectedTx.fee !== null && selectedTx.fee !== undefined ? `${selectedTx.fee} ₿` : 'Not recorded'}</strong>
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8' }}>Script Type: </span>
                    <strong>{selectedTx.script_type || 'Unspecified'}</strong>
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8' }}>Source IP: </span>
                    <strong className="mono">{selectedTx.src_ip || 'N/A'}{selectedTx.src_port ? `:${selectedTx.src_port}` : ''}</strong>
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8' }}>Destination IP: </span>
                    <strong className="mono">{selectedTx.dst_ip || 'N/A'}{selectedTx.dst_port ? `:${selectedTx.dst_port}` : ''}</strong>
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8' }}>Country / ASN: </span>
                    <strong>{selectedTx.geo_country || 'N/A'} {selectedTx.asn ? `(AS${selectedTx.asn})` : ''}</strong>
                  </div>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setSelectedTx(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
