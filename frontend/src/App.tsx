import { useState, useEffect, useCallback } from 'react';
import {
  checkBackendHealth,
  listDatasets,
  getDatasetAnalyticsSummary,
  getWalletAnalytics,
  getTimeSeriesAnalytics,
  getNetworkAnalytics,
  getCorrelations,
  getGraphSummary,
  getGraphMetrics,
  getWalletGraphMetrics,
  getConnectedComponents,
  getAnomalies,
  getClusteringSummary,
  getBehaviorSummary,
  getBehaviorFindings,
  getRiskSummary,
  getRiskFindings,
  listEvidenceArtifacts,
  HealthStatus,
  IngestionMetadata,
  DatasetAnalyticsSummary,
  WalletActivity,
  TimeSeriesBucket,
  NetworkObservation,
  CorrelationRecord,
  GraphSummaryResponse,
  GraphMetricsSummary,
  WalletGraphMetrics,
  ConnectedComponentInfo,
  AnomalyDetectionResult,
  DBSCANClusteringResult,
  BehaviorSummary,
  BehavioralFinding,
  RiskSummary,
  RiskFinding,
} from './services/api';

import { NavigationTab } from './components/NavigationFlashcards';
import { TopBar } from './components/TopBar';
import { EntityDetailModal } from './components/EntityDetailModal';
import { GlobalSearchModal } from './components/GlobalSearchModal';
import { PipelineRunnerModal } from './components/PipelineRunnerModal';
import { UploadDatasetModal } from './components/UploadDatasetModal';

import { DashboardOverview } from './views/DashboardOverview';
import { DatasetsView } from './views/DatasetsView';
import { TransactionsView } from './views/TransactionsView';
import { WalletIntelligenceView } from './views/WalletIntelligenceView';
import { NetworkAnalysisView } from './views/NetworkAnalysisView';
import { GraphInvestigationView } from './views/GraphInvestigationView';
import { MLAnomaliesView } from './views/MLAnomaliesView';
import { BehavioralClustersView } from './views/BehavioralClustersView';
import { RiskAlertsView } from './views/RiskAlertsView';
import { EvidenceReportsView } from './views/EvidenceReportsView';
import { SystemStatusView } from './views/SystemStatusView';

import { useTheme } from './services/theme';
import { useI18n } from './services/i18n';

export default function App() {
  const [currentTab, setCurrentTab] = useState<NavigationTab>('dashboard');
  const { theme, toggleTheme } = useTheme();
  const { lang, setLang } = useI18n();

  // Backend Health State
  const [backendHealth, setBackendHealth] = useState<HealthStatus | null>(null);
  const [isHealthChecking, setIsHealthChecking] = useState(false);

  // Datasets State
  const [datasetsList, setDatasetsList] = useState<IngestionMetadata[]>([]);
  const [activeDatasetId, setActiveDatasetId] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Analytics & Pipeline Data State
  const [analyticsSummary, setAnalyticsSummary] = useState<DatasetAnalyticsSummary | null>(null);
  const [wallets, setWallets] = useState<WalletActivity[]>([]);
  const [timeSeries, setTimeSeries] = useState<TimeSeriesBucket[]>([]);
  const [networkObservations, setNetworkObservations] = useState<NetworkObservation[]>([]);
  const [correlations, setCorrelations] = useState<CorrelationRecord[]>([]);

  const [graphSummary, setGraphSummary] = useState<GraphSummaryResponse | null>(null);
  const [_networkxMetrics, setNetworkxMetrics] = useState<GraphMetricsSummary | null>(null);
  const [networkxWallets, setNetworkxWallets] = useState<WalletGraphMetrics[]>([]);
  const [_networkxComponents, setNetworkxComponents] = useState<ConnectedComponentInfo[]>([]);

  const [anomalyResult, setAnomalyResult] = useState<AnomalyDetectionResult | null>(null);
  const [clusterResult, setClusterResult] = useState<DBSCANClusteringResult | null>(null);
  const [behaviorSummary, setBehaviorSummary] = useState<BehaviorSummary | null>(null);
  const [behaviorFindings, setBehaviorFindings] = useState<BehavioralFinding[]>([]);
  const [riskSummary, setRiskSummary] = useState<RiskSummary | null>(null);
  const [riskFindings, setRiskFindings] = useState<RiskFinding[]>([]);
  const [artifactCount, setArtifactCount] = useState<number>(0);

  // Graph Deep Navigation
  const [targetGraphNode, setTargetGraphNode] = useState<string | null>(null);

  // Modals State
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isPipelineRunnerOpen, setIsPipelineRunnerOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedEntityForModal, setSelectedEntityForModal] = useState<{
    type: 'wallet' | 'transaction' | 'ip';
    id: string;
  } | null>(null);

  // Keyboard shortcut for search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const fetchHealth = async () => {
    setIsHealthChecking(true);
    try {
      const data = await checkBackendHealth();
      setBackendHealth(data);
    } catch {
      setBackendHealth(null);
    } finally {
      setIsHealthChecking(false);
    }
  };

  const handleSelectDataset = (id: string) => {
    setActiveDatasetId(id);
    try {
      localStorage.setItem('bitcoin_intel_active_dataset', id);
    } catch {}
  };

  const loadDatasets = useCallback(async () => {
    try {
      const list = await listDatasets();
      setDatasetsList(list);
      if (list.length > 0 && !activeDatasetId) {
        let chosen: IngestionMetadata | undefined;
        try {
          const saved = localStorage.getItem('bitcoin_intel_active_dataset');
          chosen = list.find((d) => d.dataset_id === saved);
        } catch {}

        if (!chosen) {
          chosen = list.find((d) => d.original_filename.toLowerCase().includes('showcase'));
        }
        if (!chosen) {
          chosen = list.find((d) => d.records_valid > 0) || list[0];
        }
        setActiveDatasetId(chosen.dataset_id);
      }
    } catch {
      // Backend may be offline
    }
  }, [activeDatasetId]);

  const loadDatasetData = useCallback(async (datasetId: string) => {
    setIsRefreshing(true);
    try {
      // Load DuckDB Analytics in parallel
      const [sumRes, walRes, tsRes, netRes, corrRes] = await Promise.allSettled([
        getDatasetAnalyticsSummary(datasetId),
        getWalletAnalytics(datasetId, 100),
        getTimeSeriesAnalytics(datasetId),
        getNetworkAnalytics(datasetId),
        getCorrelations(datasetId, 200),
      ]);

      if (sumRes.status === 'fulfilled') setAnalyticsSummary(sumRes.value);
      else setAnalyticsSummary(null);

      if (walRes.status === 'fulfilled') setWallets(walRes.value);
      else setWallets([]);

      if (tsRes.status === 'fulfilled') setTimeSeries(tsRes.value);
      else setTimeSeries([]);

      if (netRes.status === 'fulfilled') setNetworkObservations(netRes.value.observations || []);
      else setNetworkObservations([]);

      if (corrRes.status === 'fulfilled') setCorrelations(corrRes.value);
      else setCorrelations([]);

      // Load Neo4j & NetworkX graph data
      const [gSumRes, nxMetRes, nxWalRes, nxCompRes] = await Promise.allSettled([
        getGraphSummary(datasetId),
        getGraphMetrics(datasetId),
        getWalletGraphMetrics(datasetId),
        getConnectedComponents(datasetId),
      ]);

      if (gSumRes.status === 'fulfilled') setGraphSummary(gSumRes.value);
      else setGraphSummary(null);

      if (nxMetRes.status === 'fulfilled') setNetworkxMetrics(nxMetRes.value);
      else setNetworkxMetrics(null);

      if (nxWalRes.status === 'fulfilled') setNetworkxWallets(nxWalRes.value);
      else setNetworkxWallets([]);

      if (nxCompRes.status === 'fulfilled') setNetworkxComponents(nxCompRes.value);
      else setNetworkxComponents([]);

      // Load AI/ML Pipeline Data
      const [anomRes, clustRes, behSumRes, behFindRes, riskSumRes, riskFindRes, artRes] = await Promise.allSettled([
        getAnomalies(datasetId, 'transaction', 50),
        getClusteringSummary(datasetId),
        getBehaviorSummary(datasetId),
        getBehaviorFindings(datasetId, { limit: 50 }),
        getRiskSummary(datasetId),
        getRiskFindings(datasetId, { limit: 50 }),
        listEvidenceArtifacts(datasetId),
      ]);

      if (anomRes.status === 'fulfilled') setAnomalyResult(anomRes.value);
      else setAnomalyResult(null);

      if (clustRes.status === 'fulfilled') setClusterResult(clustRes.value);
      else setClusterResult(null);

      if (behSumRes.status === 'fulfilled') setBehaviorSummary(behSumRes.value);
      else setBehaviorSummary(null);

      if (behFindRes.status === 'fulfilled') setBehaviorFindings(behFindRes.value);
      else setBehaviorFindings([]);

      if (riskSumRes.status === 'fulfilled') setRiskSummary(riskSumRes.value);
      else setRiskSummary(null);

      if (riskFindRes.status === 'fulfilled') setRiskFindings(riskFindRes.value);
      else setRiskFindings([]);

      if (artRes.status === 'fulfilled') setArtifactCount(artRes.value.length);
      else setArtifactCount(0);
    } catch {
      // Catch unexpected errors
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  // Initial mount: check health, load dataset list
  useEffect(() => {
    fetchHealth();
    loadDatasets();
  }, [loadDatasets]);

  // When activeDatasetId changes, load all analytical data
  useEffect(() => {
    if (activeDatasetId) {
      loadDatasetData(activeDatasetId);
    }
  }, [activeDatasetId, loadDatasetData]);

  const handleSelectEntity = (type: 'wallet' | 'transaction' | 'ip', id: string) => {
    setSelectedEntityForModal({ type, id });
  };

  return (
    <div className="app-layout">
      {/* Main Full-Width Application Container (Sidebar Removed) */}
      <div className="main-content">
        <TopBar
          datasets={datasetsList}
          activeDatasetId={activeDatasetId}
          onSelectDataset={handleSelectDataset}
          onOpenSearch={() => setIsSearchOpen(true)}
          onOpenPipelineRunner={() => setIsPipelineRunnerOpen(true)}
          onOpenUploadModal={() => setIsUploadModalOpen(true)}
          onRefresh={() => {
            if (activeDatasetId) loadDatasetData(activeDatasetId);
            fetchHealth();
            loadDatasets();
          }}
          isRefreshing={isRefreshing}
          totalWallets={analyticsSummary?.unique_wallets || wallets.length}
          totalTransactions={analyticsSummary?.total_records || correlations.length}
          currentTab={currentTab}
          onNavigateTab={setCurrentTab}
          theme={theme}
          onToggleTheme={toggleTheme}
          lang={lang}
          onSetLang={setLang}
          isBackendHealthy={backendHealth !== null}
        />

        <main className="view-container">
          {currentTab === 'dashboard' && (
            <DashboardOverview
              activeDatasetId={activeDatasetId}
              analyticsSummary={analyticsSummary}
              timeSeries={timeSeries}
              riskSummary={riskSummary}
              riskFindings={riskFindings}
              anomalyResult={anomalyResult}
              clusterResult={clusterResult}
              behaviorSummary={behaviorSummary}
              graphSummary={graphSummary}
              datasetCount={datasetsList.length}
              artifactCount={artifactCount}
              isBackendHealthy={backendHealth !== null}
              onSelectEntity={handleSelectEntity}
              onOpenPipelineRunner={() => setIsPipelineRunnerOpen(true)}
              onOpenUploadModal={() => setIsUploadModalOpen(true)}
              onNavigateTab={setCurrentTab}
            />
          )}

          {currentTab === 'datasets' && (
            <DatasetsView
              datasets={datasetsList}
              activeDatasetId={activeDatasetId}
              onSelectDataset={handleSelectDataset}
              onRefreshDatasets={loadDatasets}
            />
          )}

          {currentTab === 'transactions' && (
            <TransactionsView
              correlations={correlations}
              onSelectEntity={handleSelectEntity}
              isLoading={isRefreshing}
            />
          )}

          {currentTab === 'wallets' && (
            <WalletIntelligenceView
              wallets={wallets}
              graphMetrics={networkxWallets}
              clusters={clusterResult?.entities || []}
              riskFindings={riskFindings}
              anomalies={anomalyResult?.anomalies || []}
              behaviorFindings={behaviorFindings}
              onSelectEntity={handleSelectEntity}
              isLoading={isRefreshing}
            />
          )}

          {currentTab === 'network' && (
            <NetworkAnalysisView
              observations={networkObservations}
              analyticsSummary={analyticsSummary}
              onSelectEntity={handleSelectEntity}
              isLoading={isRefreshing}
            />
          )}

          {currentTab === 'graph' && activeDatasetId && (
            <GraphInvestigationView
              datasetId={activeDatasetId}
              graphSummary={graphSummary}
              onRefreshGraph={() => loadDatasetData(activeDatasetId)}
              onSelectEntity={handleSelectEntity}
              initialCenterNode={targetGraphNode}
              wallets={wallets}
              correlations={correlations}
              riskFindings={riskFindings}
              behaviorFindings={behaviorFindings}
              anomalies={anomalyResult?.anomalies || []}
              clusters={clusterResult?.entities || []}
              graphMetrics={networkxWallets}
              networkObservations={networkObservations}
            />
          )}

          {currentTab === 'anomalies' && activeDatasetId && (
            <MLAnomaliesView
              datasetId={activeDatasetId}
              anomalyResult={anomalyResult}
              onRefreshAnomalies={() => loadDatasetData(activeDatasetId)}
              onSelectEntity={handleSelectEntity}
            />
          )}

          {currentTab === 'clusters' && activeDatasetId && (
            <BehavioralClustersView
              datasetId={activeDatasetId}
              clusterResult={clusterResult}
              onRefreshClusters={() => loadDatasetData(activeDatasetId)}
              onSelectEntity={handleSelectEntity}
            />
          )}

          {currentTab === 'risk' && activeDatasetId && (
            <RiskAlertsView
              datasetId={activeDatasetId}
              riskSummary={riskSummary}
              riskFindings={riskFindings}
              onRefreshRisk={() => loadDatasetData(activeDatasetId)}
              onSelectEntity={handleSelectEntity}
            />
          )}

          {currentTab === 'evidence' && activeDatasetId && (
            <EvidenceReportsView
              datasetId={activeDatasetId}
              datasetMeta={datasetsList.find((d) => d.dataset_id === activeDatasetId) || null}
            />
          )}

          {currentTab === 'status' && (
            <SystemStatusView
              backendHealth={backendHealth}
              graphSummary={graphSummary}
              activeDatasetId={activeDatasetId}
              onCheckHealth={() => {
                fetchHealth();
                if (activeDatasetId) loadDatasetData(activeDatasetId);
              }}
              isChecking={isHealthChecking}
            />
          )}
        </main>
      </div>

      {/* Global Modals */}
      <GlobalSearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        wallets={wallets}
        correlations={correlations}
        networkObservations={networkObservations}
        datasets={datasetsList}
        onSelectEntity={handleSelectEntity}
        onSelectDataset={handleSelectDataset}
      />

      {activeDatasetId && (
        <PipelineRunnerModal
          isOpen={isPipelineRunnerOpen}
          onClose={() => setIsPipelineRunnerOpen(false)}
          datasetId={activeDatasetId}
          onComplete={() => loadDatasetData(activeDatasetId)}
        />
      )}

      <UploadDatasetModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={async (newDatasetId, runPipelines) => {
          await loadDatasets();
          handleSelectDataset(newDatasetId);
          setIsUploadModalOpen(false);
          if (runPipelines) {
            setIsPipelineRunnerOpen(true);
          }
        }}
      />

      {selectedEntityForModal && activeDatasetId && (
        <EntityDetailModal
          entityType={selectedEntityForModal.type}
          entityId={selectedEntityForModal.id}
          datasetId={activeDatasetId}
          onClose={() => setSelectedEntityForModal(null)}
          wallets={wallets}
          correlations={correlations}
          riskFindings={riskFindings}
          behaviorFindings={behaviorFindings}
          anomalies={anomalyResult?.anomalies || []}
          graphMetrics={networkxWallets}
          clusters={clusterResult?.entities || []}
          onNavigateToGraph={(nodeId) => {
            setTargetGraphNode(nodeId);
            setCurrentTab('graph');
          }}
        />
      )}
    </div>
  );
}
