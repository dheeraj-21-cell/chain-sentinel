import React from 'react';
import { NetworkObservation, DatasetAnalyticsSummary } from '../services/api';
import { CategoryBarChart } from '../components/Charts';
import { CopyButton } from '../components/CopyButton';

interface NetworkAnalysisViewProps {
  observations: NetworkObservation[];
  analyticsSummary: DatasetAnalyticsSummary | null;
  onSelectEntity: (type: 'wallet' | 'transaction' | 'ip', id: string) => void;
  isLoading: boolean;
}

export const NetworkAnalysisView: React.FC<NetworkAnalysisViewProps> = ({
  observations,
  analyticsSummary,
  onSelectEntity,
  isLoading,
}) => {
  return (
    <div>
      {/* Header */}
      <div className="view-header">
        <div>
          <h1 className="view-title">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" strokeWidth="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="2" y1="12" x2="22" y2="12"></line>
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
            </svg>
            P2P Network Analysis & Telemetry
          </h1>
          <p className="view-subtitle">
            Inspect observed peer IP communication endpoints, TCP ports, autonomous system numbers (ASNs), and geographic origins.
          </p>
        </div>
      </div>

      {/* Network Metrics Cards */}
      <div className="grid-cols-4" style={{ marginBottom: '1.5rem' }}>
        <div className="kpi-card">
          <div className="kpi-label">Unique Communicating IPs</div>
          <div className="kpi-value">{analyticsSummary?.unique_ips ?? 0}</div>
          <div className="kpi-subtext">Source & destination nodes</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Total Observations</div>
          <div className="kpi-value">{observations.length}</div>
          <div className="kpi-subtext">Communicating IP pairs</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Observed ASNs</div>
          <div className="kpi-value">{analyticsSummary?.asns ? Object.keys(analyticsSummary.asns).length : 0}</div>
          <div className="kpi-subtext">Autonomous systems</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Observed Countries</div>
          <div className="kpi-value">{analyticsSummary?.countries ? Object.keys(analyticsSummary.countries).length : 0}</div>
          <div className="kpi-subtext">Geographic jurisdictions</div>
        </div>
      </div>

      {/* Breakdown Charts Grid */}
      <div className="grid-cols-3" style={{ marginBottom: '1.5rem' }}>
        <div className="card">
          <h3 className="card-title">Geographic Distribution</h3>
          {analyticsSummary?.countries && Object.keys(analyticsSummary.countries).length > 0 ? (
            <CategoryBarChart data={analyticsSummary.countries} color="#10b981" />
          ) : (
            <div style={{ color: '#64748b', fontSize: '0.82rem', padding: '1rem 0' }}>No geographic country data recorded</div>
          )}
        </div>

        <div className="card">
          <h3 className="card-title">Autonomous Systems (ASNs)</h3>
          {analyticsSummary?.asns && Object.keys(analyticsSummary.asns).length > 0 ? (
            <CategoryBarChart
              data={Object.fromEntries(Object.entries(analyticsSummary.asns).map(([k, v]) => [`AS${k}`, v]))}
              color="#38bdf8"
            />
          ) : (
            <div style={{ color: '#64748b', fontSize: '0.82rem', padding: '1rem 0' }}>No ASN metadata recorded</div>
          )}
        </div>

        <div className="card">
          <h3 className="card-title">Active TCP Ports</h3>
          {analyticsSummary?.ports && Object.keys(analyticsSummary.ports).length > 0 ? (
            <CategoryBarChart
              data={Object.fromEntries(Object.entries(analyticsSummary.ports).map(([k, v]) => [`Port :${k}`, v]))}
              color="#a855f7"
            />
          ) : (
            <div style={{ color: '#64748b', fontSize: '0.82rem', padding: '1rem 0' }}>No port data recorded</div>
          )}
        </div>
      </div>

      {/* Observations Table */}
      <div className="card">
        <h3 className="card-title">P2P Network Observation Log ({observations.length})</h3>
        {isLoading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#38bdf8' }}>Loading network observations...</div>
        ) : observations.length === 0 ? (
          <div className="empty-state">
            <div className="empty-title">No Network Telemetry Recorded</div>
            <p className="empty-desc">The active dataset does not include IP-level network observation metadata.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="cyber-table">
              <thead>
                <tr>
                  <th>Source IP Address</th>
                  <th>Destination IP Address</th>
                  <th>Communicating Ports</th>
                  <th>Geo Country</th>
                  <th>Autonomous System</th>
                  <th>Observation Count</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {observations.map((obs, idx) => (
                  <tr key={idx}>
                    <td className="mono" style={{ fontSize: '0.78rem' }}>
                      {obs.src_ip ? (
                        <span
                          className="clickable-entity"
                          onClick={() => onSelectEntity('ip', obs.src_ip!)}
                        >
                          {obs.src_ip}
                        </span>
                      ) : (
                        <span style={{ color: '#64748b' }}>—</span>
                      )}
                      {obs.src_ip && <CopyButton text={obs.src_ip} />}
                    </td>

                    <td className="mono" style={{ fontSize: '0.78rem' }}>
                      {obs.dst_ip ? (
                        <span
                          className="clickable-entity"
                          onClick={() => onSelectEntity('ip', obs.dst_ip!)}
                        >
                          {obs.dst_ip}
                        </span>
                      ) : (
                        <span style={{ color: '#64748b' }}>—</span>
                      )}
                      {obs.dst_ip && <CopyButton text={obs.dst_ip} />}
                    </td>

                    <td className="mono" style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>
                      {obs.src_port ? `:${obs.src_port}` : '—'} → {obs.dst_port ? `:${obs.dst_port}` : '—'}
                    </td>

                    <td>
                      {obs.geo_country ? (
                        <span className="badge badge-low">{obs.geo_country}</span>
                      ) : (
                        <span style={{ color: '#64748b' }}>Unspecified</span>
                      )}
                    </td>

                    <td className="mono" style={{ fontSize: '0.78rem' }}>
                      {obs.asn ? (
                        <span className="badge badge-cyan">AS{obs.asn}</span>
                      ) : (
                        <span style={{ color: '#64748b' }}>—</span>
                      )}
                    </td>

                    <td className="mono" style={{ fontWeight: 600 }}>
                      {obs.observation_count}
                    </td>

                    <td>
                      {obs.src_ip && (
                        <button
                          className="btn-secondary"
                          style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem' }}
                          onClick={() => onSelectEntity('ip', obs.src_ip!)}
                        >
                          Inspect Peer
                        </button>
                      )}
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
