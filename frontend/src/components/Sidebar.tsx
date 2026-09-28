import React from 'react';

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

interface SidebarProps {
  currentTab: NavigationTab;
  onSelectTab: (tab: NavigationTab) => void;
  activeDatasetId: string | null;
  isBackendHealthy: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  activeDatasetId,
  isBackendHealthy,
}) => {
  const navItems: { id: NavigationTab; label: string; icon: React.ReactNode }[] = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="9"></rect>
          <rect x="14" y="3" width="7" height="5"></rect>
          <rect x="14" y="12" width="7" height="9"></rect>
          <rect x="3" y="16" width="7" height="5"></rect>
        </svg>
      ),
    },
    {
      id: 'datasets',
      label: 'Datasets & Ingestion',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
          <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
          <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
        </svg>
      ),
    },
    {
      id: 'transactions',
      label: 'Transactions Ledger',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
      id: 'wallets',
      label: 'Wallet Intelligence',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="4" width="20" height="16" rx="2"></rect>
          <path d="M7 15h0M2 9.5h20"></path>
        </svg>
      ),
    },
    {
      id: 'network',
      label: 'Network Analysis',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="2" y1="12" x2="22" y2="12"></line>
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
        </svg>
      ),
    },
    {
      id: 'graph',
      label: 'Graph Investigation',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="6" cy="6" r="3"></circle>
          <circle cx="18" cy="18" r="3"></circle>
          <circle cx="18" cy="6" r="3"></circle>
          <line x1="8.5" y1="7.5" x2="15.5" y2="16.5"></line>
          <line x1="9" y1="6" x2="15" y2="6"></line>
        </svg>
      ),
    },
    {
      id: 'anomalies',
      label: 'ML Anomalies',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
          <line x1="12" y1="9" x2="12" y2="13"></line>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
      ),
    },
    {
      id: 'clusters',
      label: 'Behavioral Clusters',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3"></circle>
          <circle cx="19" cy="5" r="2"></circle>
          <circle cx="5" cy="19" r="2"></circle>
          <circle cx="5" cy="5" r="2"></circle>
          <circle cx="19" cy="19" r="2"></circle>
        </svg>
      ),
    },
    {
      id: 'risk',
      label: 'Risk & Alerts',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        </svg>
      ),
    },
    {
      id: 'evidence',
      label: 'Evidence & Reports',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <path d="m9 15 2 2 4-4"></path>
        </svg>
      ),
    },
    {
      id: 'status',
      label: 'System Status',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
          <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
          <line x1="6" y1="6" x2="6.01" y2="6"></line>
          <line x1="6" y1="18" x2="6.01" y2="18"></line>
        </svg>
      ),
    },
  ];

  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-header">
        <div className="brand-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
            <polyline points="2 17 12 22 22 17"></polyline>
            <polyline points="2 12 12 17 22 12"></polyline>
          </svg>
        </div>
        <div>
          <div className="brand-title">BITCOIN INTEL</div>
          <div className="brand-subtitle">FORENSIC SUITE</div>
        </div>
        <span className="badge badge-neutral" style={{ marginLeft: 'auto', fontSize: '0.62rem' }}>
          SIH
        </span>
      </div>

      {/* Navigation List */}
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${currentTab === item.id ? 'active' : ''}`}
            onClick={() => onSelectTab(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      {/* Bottom Status Panel */}
      <div className="sidebar-footer">
        <div className="air-gapped-badge">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          </svg>
          Air-Gapped Offline
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.72rem', color: '#94a3b8' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span className={`status-dot ${isBackendHealthy ? 'online pulse' : 'offline'}`} />
            API :8000
          </span>
          <span className="mono" style={{ color: activeDatasetId ? '#38bdf8' : '#64748b' }}>
            {activeDatasetId ? `${activeDatasetId.slice(0, 8)}` : 'No Dataset'}
          </span>
        </div>
      </div>
    </aside>
  );
};
