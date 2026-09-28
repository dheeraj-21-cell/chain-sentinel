import React from 'react';
import { useI18n } from '../services/i18n';

export type NavigationTab =
  | 'dashboard'
  | 'datasets'
  | 'transactions'
  | 'wallets'
  | 'network'
  | 'graph'
  | 'anomalies'
  | 'clusters'
  | 'risk'
  | 'evidence'
  | 'status';

interface NavigationFlashcardsProps {
  onNavigateTab: (tab: NavigationTab) => void;
  datasetCount: number;
  totalTransactions: number;
  totalWallets: number;
  totalIPs: number;
  graphNodes: number;
  graphEdges: number;
  anomalyCount: number;
  clusterCount: number;
  highRiskCount: number;
  artifactCount: number;
  isBackendHealthy: boolean;
  activeDatasetId: string | null;
}

export const NavigationFlashcards: React.FC<NavigationFlashcardsProps> = ({
  onNavigateTab,
  datasetCount,
  totalTransactions,
  totalWallets,
  totalIPs,
  graphNodes,
  graphEdges,
  anomalyCount,
  clusterCount,
  highRiskCount,
  artifactCount,
  isBackendHealthy,
  activeDatasetId,
}) => {
  const { t } = useI18n();

  const cards = [
    {
      id: 'datasets' as NavigationTab,
      title: t('card_datasets_title'),
      desc: t('card_datasets_desc'),
      metric: `${datasetCount} Ingested`,
      accent: 'var(--cyber-blue)',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
          <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
          <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
        </svg>
      ),
    },
    {
      id: 'transactions' as NavigationTab,
      title: t('card_txs_title'),
      desc: t('card_txs_desc'),
      metric: activeDatasetId ? `${totalTransactions.toLocaleString()} Transactions` : t('no_dataset'),
      accent: 'var(--cyber-cyan)',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="8" y1="6" x2="21" y2="6"></line>
          <line x1="8" y1="12" x2="21" y2="12"></line>
          <line x1="8" y1="18" x2="21" y2="18"></line>
          <line x1="3" y1="6" x2="3.01" y2="6"></line>
          <line x1="3" y1="12" x2="3.01" y2="12"></line>
          <line x1="3" y1="18" x2="3.01" y2="18"></line>
        </svg>
      ),
    },
    {
      id: 'wallets' as NavigationTab,
      title: t('card_wallets_title'),
      desc: t('card_wallets_desc'),
      metric: activeDatasetId ? `${totalWallets.toLocaleString()} Wallets` : t('no_dataset'),
      accent: 'var(--cyber-emerald)',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="2" y="4" width="20" height="16" rx="2"></rect>
          <path d="M7 15h0M2 9.5h20"></path>
        </svg>
      ),
    },
    {
      id: 'network' as NavigationTab,
      title: t('card_network_title'),
      desc: t('card_network_desc'),
      metric: activeDatasetId ? `${totalIPs.toLocaleString()} Peers / IPs` : t('no_dataset'),
      accent: 'var(--cyber-indigo)',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="2" y1="12" x2="22" y2="12"></line>
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
        </svg>
      ),
    },
    {
      id: 'graph' as NavigationTab,
      title: t('card_graph_title'),
      desc: t('card_graph_desc'),
      metric: activeDatasetId ? `${graphNodes} Nodes • ${graphEdges} Edges` : t('no_dataset'),
      accent: 'var(--cyber-purple)',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="6" cy="6" r="3"></circle>
          <circle cx="18" cy="18" r="3"></circle>
          <circle cx="18" cy="6" r="3"></circle>
          <line x1="8.5" y1="7.5" x2="15.5" y2="16.5"></line>
          <line x1="9" y1="6" x2="15" y2="6"></line>
        </svg>
      ),
    },
    {
      id: 'anomalies' as NavigationTab,
      title: t('card_anomalies_title'),
      desc: t('card_anomalies_desc'),
      metric: activeDatasetId ? `${anomalyCount} ML Outliers` : t('no_dataset'),
      accent: 'var(--cyber-amber)',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
          <polyline points="2 17 12 22 22 17"></polyline>
          <polyline points="2 12 12 17 22 12"></polyline>
        </svg>
      ),
    },
    {
      id: 'clusters' as NavigationTab,
      title: t('card_clusters_title'),
      desc: t('card_clusters_desc'),
      metric: activeDatasetId ? `${clusterCount} DBSCAN Clusters` : t('no_dataset'),
      accent: 'var(--cyber-cyan)',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="3"></circle>
          <circle cx="19" cy="5" r="2"></circle>
          <circle cx="5" cy="19" r="2"></circle>
          <circle cx="5" cy="5" r="2"></circle>
          <circle cx="19" cy="19" r="2"></circle>
        </svg>
      ),
    },
    {
      id: 'risk' as NavigationTab,
      title: t('card_risk_title'),
      desc: t('card_risk_desc'),
      metric: activeDatasetId ? `${highRiskCount} High/Critical Alerts` : t('no_dataset'),
      accent: 'var(--cyber-crimson)',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
      ),
    },
    {
      id: 'evidence' as NavigationTab,
      title: t('card_evidence_title'),
      desc: t('card_evidence_desc'),
      metric: activeDatasetId ? `${artifactCount} Signed Artifacts` : t('no_dataset'),
      accent: 'var(--cyber-blue)',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <path d="m9 15 2 2 4-4"></path>
        </svg>
      ),
    },
    {
      id: 'status' as NavigationTab,
      title: t('card_status_title'),
      desc: t('card_status_desc'),
      metric: isBackendHealthy ? 'API :8000 Healthy' : 'Backend Disconnected',
      accent: isBackendHealthy ? 'var(--cyber-emerald)' : 'var(--cyber-crimson)',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
          <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
          <line x1="6" y1="6" x2="6.01" y2="6"></line>
          <line x1="6" y1="18" x2="6.01" y2="18"></line>
        </svg>
      ),
    },
  ];

  return (
    <div>
      <div className="flashcards-section-header">
        <h2 className="flashcards-section-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--cyber-blue)" strokeWidth="2">
            <rect x="3" y="3" width="7" height="9"></rect>
            <rect x="14" y="3" width="7" height="5"></rect>
            <rect x="14" y="12" width="7" height="9"></rect>
            <rect x="3" y="16" width="7" height="5"></rect>
          </svg>
          {t('all_modules')}
        </h2>
      </div>

      <div className="flashcards-grid">
        {cards.map((c) => (
          <div
            key={c.id}
            className="flashcard"
            onClick={() => onNavigateTab(c.id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onNavigateTab(c.id);
              }
            }}
          >
            <div className="flashcard-top">
              <div
                className="flashcard-icon-wrapper"
                style={{
                  background: `${c.accent}18`,
                  color: c.accent,
                  border: `1px solid ${c.accent}44`,
                }}
              >
                {c.icon}
              </div>
              <span
                className="badge badge-neutral mono"
                style={{ fontSize: '0.68rem', color: c.accent }}
              >
                {c.metric}
              </span>
            </div>

            <div>
              <div className="flashcard-title">{c.title}</div>
              <div className="flashcard-desc">{c.desc}</div>
            </div>

            <div className="flashcard-footer">
              <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                {c.id.toUpperCase()}
              </span>
              <button
                className="flashcard-explore-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onNavigateTab(c.id);
                }}
              >
                {t('explore')}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
