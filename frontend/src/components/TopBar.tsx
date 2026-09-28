import React, { useState } from 'react';
import { IngestionMetadata } from '../services/api';
import { NavigationTab } from './NavigationFlashcards';
import { useI18n, Language } from '../services/i18n';
import { Theme } from '../services/theme';

interface TopBarProps {
  datasets: IngestionMetadata[];
  activeDatasetId: string | null;
  onSelectDataset: (datasetId: string) => void;
  onOpenSearch: () => void;
  onOpenPipelineRunner: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
  totalWallets: number;
  totalTransactions: number;
  currentTab: NavigationTab;
  onNavigateTab: (tab: NavigationTab) => void;
  theme: Theme;
  onToggleTheme: () => void;
  lang: Language;
  onSetLang: (lang: Language) => void;
  investigatorName?: string;
  caseName?: string;
  isBackendHealthy: boolean;
  onOpenUploadModal?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  datasets,
  activeDatasetId,
  onSelectDataset,
  onOpenSearch,
  onOpenPipelineRunner,
  onRefresh,
  isRefreshing,
  totalWallets,
  totalTransactions,
  currentTab,
  onNavigateTab,
  theme,
  onToggleTheme,
  lang,
  onSetLang,
  investigatorName = 'Special Agent SIH',
  caseName = 'SIH 2026',
  isBackendHealthy,
  onOpenUploadModal,
}) => {
  const { t } = useI18n();
  const [showInvestigatorMenu, setShowInvestigatorMenu] = useState(false);
  const [showModuleMenu, setShowModuleMenu] = useState(false);

  const modules: { id: NavigationTab; label: string }[] = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'datasets', label: 'Datasets & Ingestion' },
    { id: 'transactions', label: 'Transactions Ledger' },
    { id: 'wallets', label: 'Wallet Intelligence' },
    { id: 'network', label: 'Network Analysis' },
    { id: 'graph', label: 'Graph Investigation' },
    { id: 'anomalies', label: 'AI/ML Anomalies' },
    { id: 'clusters', label: 'Behavioral Clusters' },
    { id: 'risk', label: 'Risk & Alerts' },
    { id: 'evidence', label: 'Evidence & Reports' },
    { id: 'status', label: 'System Status' },
  ];

  return (
    <header className="topbar">
      <div className="topbar-left">
        {/* Brand & Home */}
        <div className="brand-section" onClick={() => onNavigateTab('dashboard')} title="Go to Dashboard">
          <div className="brand-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
          </div>
          <div>
            <div className="brand-title">{t('platform_title')}</div>
            <div className="brand-subtitle">{t('platform_subtitle')}</div>
          </div>
        </div>

        {/* Back to Dashboard / Module Switcher */}
        {currentTab !== 'dashboard' ? (
          <button
            className="btn-secondary"
            onClick={() => onNavigateTab('dashboard')}
            style={{ fontSize: '0.76rem', padding: '0.3rem 0.65rem' }}
          >
            {t('back_to_dashboard')}
          </button>
        ) : null}

        {/* Module Switcher Dropdown */}
        <div style={{ position: 'relative' }}>
          <button
            className="btn-ghost module-switcher-btn"
            onClick={() => setShowModuleMenu((prev) => !prev)}
            style={{ fontSize: '0.78rem', padding: '0.35rem 0.55rem', border: '1px solid var(--border-medium)', borderRadius: '6px' }}
            title="Switch between investigation modules"
          >
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
              {modules.find((m) => m.id === currentTab)?.label || 'Modules'}
            </span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>

          {showModuleMenu && (
            <div
              style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                marginTop: '4px',
                background: 'var(--bg-card)',
                border: '1px solid var(--border-medium)',
                borderRadius: '8px',
                boxShadow: 'var(--card-shadow)',
                zIndex: 50,
                width: '210px',
                padding: '0.4rem 0',
              }}
            >
              {modules.map((m) => (
                <button
                  key={m.id}
                  onClick={() => {
                    onNavigateTab(m.id);
                    setShowModuleMenu(false);
                  }}
                  style={{
                    display: 'block',
                    width: '100%',
                    textAlign: 'left',
                    padding: '0.45rem 0.9rem',
                    background: currentTab === m.id ? 'var(--bg-hover)' : 'transparent',
                    border: 'none',
                    color: currentTab === m.id ? 'var(--cyber-blue)' : 'var(--text-primary)',
                    fontSize: '0.78rem',
                    fontWeight: currentTab === m.id ? 700 : 400,
                    cursor: 'pointer',
                  }}
                >
                  {m.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Dataset Selector */}
        <div className="dataset-select-wrapper">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--cyber-blue)" strokeWidth="2">
            <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
            <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
            <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
          </svg>
          <select
            className="dataset-select"
            value={activeDatasetId || ''}
            onChange={(e) => onSelectDataset(e.target.value)}
          >
            {datasets.length === 0 ? (
              <option value="">{t('no_dataset')}</option>
            ) : (
              datasets.map((d) => {
                const isShowcase = d.original_filename.toLowerCase().includes('showcase');
                const displayName = isShowcase ? 'SIH Showcase Dataset' : d.original_filename;
                const hasDuplicateName = datasets.filter((x) => x.original_filename === d.original_filename).length > 1;
                const label = hasDuplicateName
                  ? `${displayName} (${d.records_valid} records) - ${d.dataset_id.slice(0, 8)}`
                  : `${displayName} (${d.records_valid} records)`;
                return (
                  <option key={d.dataset_id} value={d.dataset_id}>
                    {label}
                  </option>
                );
              })
            )}
          </select>
        </div>

        {/* Global Search Button */}
        <button className="search-trigger-btn" onClick={onOpenSearch}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <span>{t('search_placeholder')}</span>
          <span className="search-shortcut">{t('search_shortcut')}</span>
        </button>
      </div>

      <div className="topbar-right">
        {/* Upload Dataset Button */}
        {onOpenUploadModal && (
          <button
            className="btn-secondary"
            onClick={onOpenUploadModal}
            title={t('upload_dataset')}
            style={{ fontSize: '0.76rem', padding: '0.35rem 0.65rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <span style={{ display: 'none', minWidth: '0' }} className="d-md-inline">{t('upload_dataset')}</span>
          </button>
        )}

        {/* Pipeline Runner */}
        {activeDatasetId && (
          <button
            className="btn-primary"
            onClick={onOpenPipelineRunner}
            title={t('run_pipelines')}
            style={{ fontSize: '0.76rem', padding: '0.35rem 0.7rem' }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
            <span style={{ display: 'none', minWidth: '0' }} className="d-md-inline">Run Pipelines</span>
          </button>
        )}

        {/* Refresh Action */}
        <button
          className="btn-secondary"
          onClick={onRefresh}
          disabled={isRefreshing}
          title={t('refresh')}
          style={{ fontSize: '0.76rem', padding: '0.35rem 0.55rem' }}
        >
          <svg
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className={isRefreshing ? 'pulse' : ''}
          >
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
        </button>

        {/* Trilingual Language Selector */}
        <div style={{ display: 'flex', border: '1px solid var(--border-medium)', borderRadius: '6px', overflow: 'hidden' }}>
          {(['en', 'hi', 'hinglish'] as const).map((l) => (
            <button
              key={l}
              onClick={() => onSetLang(l)}
              style={{
                background: lang === l ? 'var(--cyber-blue)' : 'var(--bg-card)',
                color: lang === l ? '#ffffff' : 'var(--text-secondary)',
                border: 'none',
                padding: '0.25rem 0.45rem',
                fontSize: '0.68rem',
                fontWeight: lang === l ? 700 : 500,
                cursor: 'pointer',
              }}
              title={l === 'en' ? 'English' : l === 'hi' ? 'हिंदी (Hindi)' : 'Hinglish'}
            >
              {l === 'en' ? 'EN' : l === 'hi' ? 'हिं' : 'HING'}
            </button>
          ))}
        </div>

        {/* Theme Toggle (Dark / Light) */}
        <button
          className="btn-secondary theme-toggle-btn"
          onClick={onToggleTheme}
          title={theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
          style={{ padding: '0.35rem 0.55rem', fontSize: '0.78rem' }}
        >
          {theme === 'dark' ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--cyber-amber)" strokeWidth="2">
              <circle cx="12" cy="12" r="5"></circle>
              <line x1="12" y1="1" x2="12" y2="3"></line>
              <line x1="12" y1="21" x2="12" y2="23"></line>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
              <line x1="1" y1="12" x2="3" y2="12"></line>
              <line x1="21" y1="12" x2="23" y2="12"></line>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--cyber-blue)" strokeWidth="2">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
            </svg>
          )}
        </button>

        {/* Investigator Menu Dropdown */}
        <div style={{ position: 'relative' }}>
          <button
            className="btn-secondary"
            onClick={() => setShowInvestigatorMenu((prev) => !prev)}
            style={{
              padding: '0.3rem 0.55rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              fontSize: '0.76rem',
            }}
          >
            <div
              style={{
                width: '18px',
                height: '18px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, var(--cyber-emerald), var(--cyber-cyan))',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontSize: '0.62rem',
                fontWeight: 800,
              }}
            >
              SA
            </div>
            <span style={{ fontWeight: 600 }}>{caseName}</span>
          </button>

          {showInvestigatorMenu && (
            <div
              style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: '6px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-medium)',
                borderRadius: '8px',
                boxShadow: 'var(--card-shadow)',
                zIndex: 60,
                width: '240px',
                padding: '0.85rem',
              }}
            >
              <div style={{ marginBottom: '0.6rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.6rem' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{t('investigator')}</div>
                <div style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--text-primary)' }}>{investigatorName}</div>
                <div style={{ fontSize: '0.72rem', color: 'var(--cyber-blue)' }}>{caseName}</div>
              </div>

              <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)', marginBottom: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <div>
                  <strong>{t('active_dataset')}:</strong>{' '}
                  <span className="mono" style={{ color: activeDatasetId ? 'var(--cyber-blue)' : 'var(--text-muted)' }}>
                    {activeDatasetId ? activeDatasetId.slice(0, 8) : 'None'}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span className={`status-dot ${isBackendHealthy ? 'online pulse' : 'offline'}`} />
                  <span>{isBackendHealthy ? 'API Connected' : 'API Offline'}</span>
                </div>
                <div>
                  <strong>Scope:</strong> {totalWallets} Wallets • {totalTransactions} Txs
                </div>
              </div>

              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '0.5rem' }}>
                <button
                  className="btn-ghost"
                  onClick={() => {
                    setShowInvestigatorMenu(false);
                    onNavigateTab('status');
                  }}
                  style={{ width: '100%', textAlign: 'left', fontSize: '0.75rem', justifyContent: 'flex-start' }}
                >
                  System Diagnostics & Health →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
