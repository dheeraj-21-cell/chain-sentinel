import React from 'react';
import {
  DatasetAnalyticsSummary,
  TimeSeriesBucket,
  RiskSummary,
  RiskFinding,
  AnomalyDetectionResult,
  DBSCANClusteringResult,
  BehaviorSummary,
  GraphSummaryResponse,
} from '../services/api';
import { TimeSeriesChart, PriorityDonutChart } from '../components/Charts';
import { NavigationFlashcards, NavigationTab } from '../components/NavigationFlashcards';
import { useI18n } from '../services/i18n';

interface DashboardOverviewProps {
  activeDatasetId: string | null;
  analyticsSummary: DatasetAnalyticsSummary | null;
  timeSeries: TimeSeriesBucket[];
  riskSummary: RiskSummary | null;
  riskFindings: RiskFinding[];
  anomalyResult: AnomalyDetectionResult | null;
  clusterResult: DBSCANClusteringResult | null;
  behaviorSummary: BehaviorSummary | null;
  graphSummary: GraphSummaryResponse | null;
  datasetCount: number;
  artifactCount: number;
  isBackendHealthy: boolean;
  onSelectEntity: (type: 'wallet' | 'transaction' | 'ip', id: string) => void;
  onOpenPipelineRunner: () => void;
  onOpenUploadModal: () => void;
  onNavigateTab: (tab: NavigationTab) => void;
}

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  activeDatasetId,
  analyticsSummary,
  timeSeries,
  riskSummary,
  riskFindings,
  anomalyResult,
  clusterResult,
  behaviorSummary: _behaviorSummary,
  graphSummary,
  datasetCount,
  artifactCount,
  isBackendHealthy,
  onSelectEntity,
  onOpenPipelineRunner,
  onOpenUploadModal,
  onNavigateTab,
}) => {
  const { t } = useI18n();

  if (!activeDatasetId) {
    return (
      <div className="empty-state">
        <div className="empty-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
            <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
          </svg>
        </div>
        <h3 className="empty-title">{t('empty_no_dataset')}</h3>
        <p className="empty-desc">{t('empty_no_dataset_desc')}</p>
        <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.5rem' }}>
          <button className="btn-secondary" onClick={onOpenUploadModal}>
            {t('upload_dataset')}
          </button>
          <button className="btn-primary" onClick={() => onNavigateTab('datasets')}>
            {t('card_datasets_title')} →
          </button>
        </div>
      </div>
    );
  }

  const criticalAndHigh =
    (riskSummary?.counts_by_priority?.CRITICAL || 0) + (riskSummary?.counts_by_priority?.HIGH || 0);

  const totalWallets = analyticsSummary?.unique_wallets || 0;
  const totalTransactions = analyticsSummary?.total_records || 0;
  const totalIPs = analyticsSummary?.unique_ips || 0;
  const graphNodes = graphSummary?.total_nodes || 0;
  const graphEdges = graphSummary?.total_relationships || 0;
  const anomalyCount = anomalyResult?.anomaly_count || 0;
  const clusterCount = clusterResult?.cluster_count || 0;

  return (
    <div>
      {/* Header Banner */}
      <div className="view-header">
        <div>
          <h1 className="view-title">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--cyber-blue)" strokeWidth="2.2">
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
            {t('dashboard_title')}
          </h1>
          <p className="view-subtitle">{t('dashboard_subtitle')}</p>
        </div>

        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
          <button
            className="btn-secondary"
            onClick={onOpenUploadModal}
            style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            {t('upload_dataset')}
          </button>
          <button className="btn-primary" onClick={onOpenPipelineRunner}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
            {t('run_pipelines')}
          </button>
        </div>
      </div>

      {/* Case Investigation Summary Card */}
      <div
        className="card"
        style={{
          marginBottom: '1.25rem',
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-medium)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          padding: '0.9rem 1.25rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'rgba(56, 189, 248, 0.15)',
              color: 'var(--cyber-blue)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
              {t('summary_banner_title')}
            </div>
            <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
              {t('summary_banner_desc')}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span className="badge badge-cyan mono">DATASET: {activeDatasetId.slice(0, 8)}</span>
          <span className="badge badge-low">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            OFFLINE AIR-GAPPED
          </span>
          <span className="badge badge-neutral">CASE: SIH 2026</span>
        </div>
      </div>

      {/* Compact KPI Strip */}
      <div className="grid-cols-4">
        <div className="kpi-card">
          <div className="kpi-label">
            <span>{t('total_txs')}</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="8" y1="6" x2="21" y2="6"></line>
              <line x1="8" y1="12" x2="21" y2="12"></line>
              <line x1="8" y1="18" x2="21" y2="18"></line>
            </svg>
          </div>
          <div className="kpi-value">{totalTransactions.toLocaleString()}</div>
          <div className="kpi-subtext">{t('total_txs_sub')}</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>{t('unique_wallets')}</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="4" width="20" height="16" rx="2"></rect>
              <path d="M7 15h0M2 9.5h20"></path>
            </svg>
          </div>
          <div className="kpi-value">{totalWallets.toLocaleString()}</div>
          <div className="kpi-subtext">{t('unique_wallets_sub')}</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>{t('total_volume')}</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"></path>
            </svg>
          </div>
          <div className="kpi-value" style={{ color: 'var(--cyber-cyan)' }}>
            {analyticsSummary?.volume_stats?.total_output_btc
              ? `${analyticsSummary.volume_stats.total_output_btc.toFixed(2)} ₿`
              : '0.00 ₿'}
          </div>
          <div className="kpi-subtext">{t('total_volume_sub')}</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">
            <span>{t('high_risk_alerts')}</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--cyber-crimson)" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
            </svg>
          </div>
          <div
            className="kpi-value"
            style={{ color: criticalAndHigh > 0 ? 'var(--cyber-crimson)' : 'var(--text-primary)' }}
          >
            {riskSummary ? criticalAndHigh : '—'}
          </div>
          <div className="kpi-subtext">{t('high_risk_alerts_sub')}</div>
        </div>
      </div>

      {/* 2 Essential Charts & Top Prioritized Triage Table */}
      <div className="grid-cols-2">
        {/* Activity Over Time */}
        <div className="card">
          <div className="card-title">
            <span>{t('activity_over_time')}</span>
            <span className="badge badge-neutral">DuckDB Timeline</span>
          </div>
          <TimeSeriesChart
            data={timeSeries.map((t) => ({
              timestamp: t.timestamp_bucket,
              tx_count: t.tx_count,
              volume: t.volume,
            }))}
            height={180}
            metric="volume"
          />
        </div>

        {/* Multi-Pipeline Risk Priority Donut */}
        <div className="card">
          <div className="card-title">
            <span>{t('risk_prioritization')}</span>
            <span className="badge badge-neutral">5 Pipelines</span>
          </div>
          {riskSummary ? (
            <PriorityDonutChart counts={riskSummary.counts_by_priority} size={160} />
          ) : (
            <div className="empty-state" style={{ padding: '1.5rem' }}>
              <div className="empty-title" style={{ fontSize: '0.88rem' }}>Risk pipeline uncalculated</div>
              <p className="empty-desc" style={{ fontSize: '0.76rem' }}>
                Run all intelligence pipelines to compute priority band distribution.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Top Prioritized Entities Triage Strip */}
      <div className="card" style={{ marginBottom: '1.25rem' }}>
        <div className="card-title">
          <span>{t('top_prioritized')}</span>
          <button className="btn-ghost" onClick={() => onNavigateTab('risk')}>
            {t('view_all_risk')}
          </button>
        </div>
        {riskFindings.length === 0 ? (
          <div style={{ padding: '1.25rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
            No entities scored yet. Run the intelligence pipeline above.
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="cyber-table">
              <thead>
                <tr>
                  <th>Entity ID</th>
                  <th>Type</th>
                  <th>Priority</th>
                  <th>Score</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {riskFindings.slice(0, 4).map((rf) => (
                  <tr key={rf.risk_id}>
                    <td>
                      <span className="mono" style={{ color: 'var(--cyber-blue)', fontSize: '0.78rem' }}>
                        {rf.entity_id.length > 20
                          ? `${rf.entity_id.slice(0, 8)}...${rf.entity_id.slice(-6)}`
                          : rf.entity_id}
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-neutral">{rf.entity_type}</span>
                    </td>
                    <td>
                      <span className={`badge badge-${rf.priority.toLowerCase()}`}>{rf.priority}</span>
                    </td>
                    <td className="mono" style={{ fontWeight: 700 }}>
                      {rf.score.toFixed(1)}
                    </td>
                    <td>
                      <button
                        className="btn-secondary"
                        onClick={() =>
                          onSelectEntity(
                            rf.entity_type === 'wallet' ? 'wallet' : rf.entity_type === 'transaction' ? 'transaction' : 'ip',
                            rf.entity_id
                          )
                        }
                        style={{ fontSize: '0.72rem', padding: '0.2rem 0.5rem' }}
                      >
                        Inspect →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Clickable Module Flashcards Grid (Replaces Persistent Sidebar) */}
      <NavigationFlashcards
        onNavigateTab={onNavigateTab}
        datasetCount={datasetCount}
        totalTransactions={totalTransactions}
        totalWallets={totalWallets}
        totalIPs={totalIPs}
        graphNodes={graphNodes}
        graphEdges={graphEdges}
        anomalyCount={anomalyCount}
        clusterCount={clusterCount}
        highRiskCount={criticalAndHigh}
        artifactCount={artifactCount}
        isBackendHealthy={isBackendHealthy}
        activeDatasetId={activeDatasetId}
      />
    </div>
  );
};
