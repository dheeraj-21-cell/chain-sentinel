export interface HealthStatus {
  status: string;
  service: string;
}

export interface DatasetIngestionResponse {
  dataset_id: string;
  filename: string;
  status: 'SUCCESS' | 'PARTIAL' | 'FAILED';
  records_total: number;
  records_valid: number;
  records_rejected: number;
  normalized_output_path?: string | null;
  error_report_path?: string | null;
}

export interface IngestionMetadata {
  dataset_id: string;
  original_filename: string;
  file_type: string;
  ingestion_timestamp: string;
  records_total: number;
  records_valid: number;
  records_rejected: number;
  validation_status: string;
  raw_file_path: string;
  normalized_output_path?: string | null;
  error_report_path?: string | null;
}

export interface RejectedRecord {
  record_index: number;
  raw_data: Record<string, unknown>;
  errors: string[];
}

// Phase 3 Analytics Interfaces
export interface VolumeStats {
  total_input_btc: number;
  total_output_btc: number;
  avg_amount?: number | null;
  min_amount?: number | null;
  max_amount?: number | null;
}

export interface FeeStats {
  total_fee_btc: number;
  avg_fee_btc?: number | null;
  min_fee_btc?: number | null;
  max_fee_btc?: number | null;
  fee_recorded_count: number;
}

export interface DatasetAnalyticsSummary {
  dataset_id: string;
  total_records: number;
  unique_txids: number;
  unique_wallets: number;
  unique_ips: number;
  volume_stats: VolumeStats;
  fee_stats: FeeStats;
  earliest_timestamp?: string | null;
  latest_timestamp?: string | null;
  script_types: Record<string, number>;
  countries: Record<string, number>;
  asns: Record<string, number>;
  ports: Record<string, number>;
}

export interface WalletActivity {
  address: string;
  tx_count: number;
  input_count: number;
  output_count: number;
  total_sent: number;
  total_received: number;
  net_flow: number;
}

export interface TimeSeriesBucket {
  timestamp_bucket: string;
  tx_count: number;
  volume: number;
}

export interface NetworkObservation {
  src_ip?: string | null;
  dst_ip?: string | null;
  src_port?: number | null;
  dst_port?: number | null;
  geo_country?: string | null;
  asn?: number | null;
  observation_count: number;
}

export interface CorrelationRecord {
  txid?: string | null;
  timestamp?: string | null;
  input_addresses: string[];
  output_addresses: string[];
  input_amounts: number[];
  output_amounts: number[];
  fee?: number | null;
  src_ip?: string | null;
  dst_ip?: string | null;
  src_port?: number | null;
  dst_port?: number | null;
  geo_country?: string | null;
  asn?: number | null;
  script_type?: string | null;
}

// Phase 4 Neo4j Graph Interfaces
export interface GraphBuildResponse {
  dataset_id: string;
  status: string;
  transactions_created_or_matched: number;
  wallets_created_or_matched: number;
  ips_created_or_matched: number;
  asns_created_or_matched: number;
  countries_created_or_matched: number;
  relationships_created_or_matched: number;
  message: string;
}

export interface GraphSummaryResponse {
  dataset_id: string;
  total_nodes: number;
  total_relationships: number;
  nodes_by_label: Record<string, number>;
  relationships_by_type: Record<string, number>;
}

// Phase 11 Interactive Graph Workspace Interfaces
export interface GraphElementNode {
  id: string;
  label: string;
  canonical_id: string;
  properties: Record<string, any>;
  ml_anomaly?: {
    is_anomaly: boolean;
    anomaly_score: number;
    explanation?: string[];
  } | null;
  cluster_id?: number | null;
  behavior_findings_count: number;
  behavior_finding_types: string[];
  risk_priority?: string | null;
  risk_score?: number | null;
}

export interface GraphElementEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, any>;
}

export interface GraphElementsResponse {
  dataset_id: string;
  nodes: GraphElementNode[];
  edges: GraphElementEdge[];
  total_dataset_nodes: number;
  total_dataset_edges: number;
  is_bounded: boolean;
  message?: string | null;
}

// Phase 5 NetworkX Interfaces
export interface GraphMetricsSummary {
  dataset_id: string;
  node_count: number;
  edge_count: number;
  density: number;
  is_directed: boolean;
  connected_components_count: number;
  largest_component_size: number;
  nodes_by_type: Record<string, number>;
  edges_by_type: Record<string, number>;
  average_degree: number;
}

export interface WalletGraphMetrics {
  address: string;
  degree: number;
  fan_in: number;
  fan_out: number;
  in_degree_centrality: number;
  out_degree_centrality: number;
}

export interface ConnectedComponentInfo {
  component_id: number;
  node_count: number;
  edge_count: number;
  node_types: Record<string, number>;
  sample_nodes: string[];
}

export interface PathResult {
  source: string;
  target: string;
  path_exists: boolean;
  length?: number | null;
  node_path: string[];
  edge_types: string[];
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function checkBackendHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    headers: { 'Accept': 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Health check failed with HTTP ${response.status}`);
  }
  return response.json();
}

export async function uploadDataset(file: File): Promise<DatasetIngestionResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/v1/datasets/ingest`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(errorBody.detail || `Upload failed with HTTP ${response.status}`);
  }

  return response.json();
}

export async function getDatasetMetadata(datasetId: string): Promise<IngestionMetadata> {
  const response = await fetch(`${API_BASE_URL}/api/v1/datasets/${encodeURIComponent(datasetId)}`);
  if (!response.ok) {
    throw new Error(`Failed to load dataset metadata (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getDatasetErrors(datasetId: string): Promise<RejectedRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/datasets/${encodeURIComponent(datasetId)}/errors`);
  if (!response.ok) {
    throw new Error(`Failed to load dataset errors (HTTP ${response.status})`);
  }
  return response.json();
}

export async function listDatasets(): Promise<IngestionMetadata[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/datasets`);
  if (!response.ok) {
    throw new Error(`Failed to list datasets (HTTP ${response.status})`);
  }
  return response.json();
}

// Phase 3 Analytics API Methods
export async function getDatasetAnalyticsSummary(datasetId: string): Promise<DatasetAnalyticsSummary> {
  const response = await fetch(`${API_BASE_URL}/api/v1/analytics/${encodeURIComponent(datasetId)}/summary`);
  if (!response.ok) {
    throw new Error(`Failed to load DuckDB analytics summary (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getWalletAnalytics(datasetId: string, limit: number = 50): Promise<WalletActivity[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/analytics/${encodeURIComponent(datasetId)}/wallets?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to load wallet analytics (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getTimeSeriesAnalytics(datasetId: string): Promise<TimeSeriesBucket[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/analytics/${encodeURIComponent(datasetId)}/time-series`);
  if (!response.ok) {
    throw new Error(`Failed to load time series analytics (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getNetworkAnalytics(datasetId: string): Promise<{
  dataset_id: string;
  unique_source_ips: string[];
  unique_destination_ips: string[];
  observations: NetworkObservation[];
}> {
  const response = await fetch(`${API_BASE_URL}/api/v1/analytics/${encodeURIComponent(datasetId)}/network`);
  if (!response.ok) {
    throw new Error(`Failed to load network analytics (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getCorrelations(datasetId: string, limit: number = 100): Promise<CorrelationRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/analytics/${encodeURIComponent(datasetId)}/correlations?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to load correlation records (HTTP ${response.status})`);
  }
  return response.json();
}

// Phase 4 Neo4j Graph API Methods
export async function buildGraph(datasetId: string): Promise<GraphBuildResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/graph/${encodeURIComponent(datasetId)}/build`, {
    method: 'POST',
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(errorBody.detail || `Graph construction failed with HTTP ${response.status}`);
  }
  return response.json();
}

export async function getGraphSummary(datasetId: string): Promise<GraphSummaryResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/graph/${encodeURIComponent(datasetId)}/summary`);
  if (!response.ok) {
    throw new Error(`Failed to load Neo4j graph summary (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getGraphElements(
  datasetId: string,
  limit: number = 100,
  centerNode?: string,
  hops: number = 1
): Promise<GraphElementsResponse> {
  let url = `${API_BASE_URL}/api/v1/graph/${encodeURIComponent(datasetId)}/elements?limit=${limit}&hops=${hops}`;
  if (centerNode) {
    url += `&center_node=${encodeURIComponent(centerNode)}`;
  }
  const response = await fetch(url);
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(errorBody.detail || `Failed to fetch graph elements (HTTP ${response.status})`);
  }
  return response.json();
}

export async function expandGraphNeighborhood(
  datasetId: string,
  nodeId: string,
  hops: number = 1,
  limit: number = 50
): Promise<GraphElementsResponse> {
  const url = `${API_BASE_URL}/api/v1/graph/${encodeURIComponent(datasetId)}/neighborhood?node_id=${encodeURIComponent(nodeId)}&hops=${hops}&limit=${limit}`;
  const response = await fetch(url);
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(errorBody.detail || `Failed to expand neighborhood (HTTP ${response.status})`);
  }
  return response.json();
}

// Phase 5 NetworkX Graph Analysis API Methods
export async function getGraphMetrics(datasetId: string): Promise<GraphMetricsSummary> {
  const response = await fetch(`${API_BASE_URL}/api/v1/networkx/${encodeURIComponent(datasetId)}/metrics`);
  if (!response.ok) {
    throw new Error(`Failed to load NetworkX graph metrics (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getWalletGraphMetrics(datasetId: string, limit: number = 50): Promise<WalletGraphMetrics[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/networkx/${encodeURIComponent(datasetId)}/wallets?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Failed to load wallet graph metrics (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getConnectedComponents(datasetId: string): Promise<ConnectedComponentInfo[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/networkx/${encodeURIComponent(datasetId)}/components`);
  if (!response.ok) {
    throw new Error(`Failed to load connected components (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getGraphPath(datasetId: string, source: string, target: string): Promise<PathResult> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/networkx/${encodeURIComponent(datasetId)}/paths?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`
  );
  if (!response.ok) {
    throw new Error(`Failed to calculate shortest path (HTTP ${response.status})`);
  }
  return response.json();
}

// Phase 6 Isolation Forest ML Anomaly Detection Interfaces
export interface AnomalyScoreItem {
  entity_id: string;
  entity_type: string;
  anomaly_label: number;
  is_anomaly: boolean;
  raw_score: number;
  anomaly_score: number;
  features: Record<string, number>;
  explanation: string[];
}

export interface AnomalyDetectionResult {
  dataset_id: string;
  entity_type: string;
  model_name: string;
  model_version: string;
  timestamp: string;
  total_entities: number;
  anomaly_count: number;
  contamination: number;
  random_state: number;
  anomalies: AnomalyScoreItem[];
}

export interface ModelMetadata {
  dataset_id: string;
  entity_type: string;
  model_name: string;
  model_version: string;
  n_estimators: number;
  contamination: number;
  random_state: number;
  feature_names: string[];
  imputed_fields: Record<string, string>;
  training_samples: number;
  anomaly_samples: number;
  model_path: string;
  created_at: string;
}

export interface FeatureGenerationResponse {
  dataset_id: string;
  entity_type: string;
  feature_count: number;
  feature_names: string[];
  record_count: number;
  imputed_fields: Record<string, string>;
  feature_file_path: string;
}

// Phase 6 ML API Methods
export async function generateMLFeatures(
  datasetId: string,
  entityType: string = 'transaction'
): Promise<FeatureGenerationResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/ml/${encodeURIComponent(datasetId)}/features/generate?entity_type=${encodeURIComponent(entityType)}`,
    { method: 'POST' }
  );
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(errorBody.detail || `Feature generation failed (HTTP ${response.status})`);
  }
  return response.json();
}

export async function trainIsolationForest(
  datasetId: string,
  entityType: string = 'transaction',
  contamination: number = 0.1,
  nEstimators: number = 100,
  randomState: number = 42
): Promise<AnomalyDetectionResult> {
  const url = `${API_BASE_URL}/api/v1/ml/${encodeURIComponent(datasetId)}/train?entity_type=${encodeURIComponent(entityType)}&contamination=${contamination}&n_estimators=${nEstimators}&random_state=${randomState}`;
  const response = await fetch(url, { method: 'POST' });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(errorBody.detail || `Isolation Forest training failed (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getAnomalies(
  datasetId: string,
  entityType: string = 'transaction',
  limit: number = 100,
  anomaliesOnly: boolean = false
): Promise<AnomalyDetectionResult> {
  const url = `${API_BASE_URL}/api/v1/ml/${encodeURIComponent(datasetId)}/anomalies?entity_type=${encodeURIComponent(entityType)}&limit=${limit}&anomalies_only=${anomaliesOnly}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load anomaly detection results (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getModelMetadata(
  datasetId: string,
  entityType: string = 'transaction'
): Promise<ModelMetadata> {
  const url = `${API_BASE_URL}/api/v1/ml/${encodeURIComponent(datasetId)}/metadata?entity_type=${encodeURIComponent(entityType)}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load model metadata (HTTP ${response.status})`);
  }
  return response.json();
}

// Phase 7 DBSCAN Behavioral Clustering Interfaces
export interface WalletClusterItem {
  address: string;
  cluster_id: number;
  is_noise: boolean;
  features: Record<string, number>;
}

export interface ClusterSummary {
  cluster_id: number;
  member_count: number;
  sample_addresses: string[];
  avg_sent_btc: number;
  avg_received_btc: number;
  avg_degree: number;
  avg_fan_in: number;
  avg_fan_out: number;
  description: string;
}

export interface DBSCANClusteringResult {
  dataset_id: string;
  entity_type: string;
  eps: number;
  min_samples: number;
  total_entities: number;
  cluster_count: number;
  noise_count: number;
  clustered_count: number;
  clusters: ClusterSummary[];
  entities: WalletClusterItem[];
}

export interface ClusteringMetadata {
  dataset_id: string;
  entity_type: string;
  model_name: string;
  eps: number;
  min_samples: number;
  metric: string;
  total_entities: number;
  cluster_count: number;
  noise_count: number;
  features_used: string[];
  cluster_summaries: ClusterSummary[];
  created_at: string;
}

// Phase 7 Clustering API Methods
export async function runClustering(
  datasetId: string,
  eps: number = 0.5,
  minSamples: number = 2
): Promise<DBSCANClusteringResult> {
  const url = `${API_BASE_URL}/api/v1/clustering/${encodeURIComponent(datasetId)}/run?eps=${eps}&min_samples=${minSamples}`;
  const response = await fetch(url, { method: 'POST' });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(errorBody.detail || `DBSCAN clustering failed (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getClusteringSummary(datasetId: string): Promise<DBSCANClusteringResult> {
  const url = `${API_BASE_URL}/api/v1/clustering/${encodeURIComponent(datasetId)}/summary`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load clustering summary (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getClusteredEntities(
  datasetId: string,
  clusterId?: number | null,
  noiseOnly: boolean = false,
  limit: number = 100
): Promise<WalletClusterItem[]> {
  let url = `${API_BASE_URL}/api/v1/clustering/${encodeURIComponent(datasetId)}/entities?limit=${limit}&noise_only=${noiseOnly}`;
  if (clusterId !== undefined && clusterId !== null) {
    url += `&cluster_id=${clusterId}`;
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load clustered entities (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getClusteringMetadata(datasetId: string): Promise<ClusteringMetadata> {
  const url = `${API_BASE_URL}/api/v1/clustering/${encodeURIComponent(datasetId)}/metadata`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load clustering metadata (HTTP ${response.status})`);
  }
  return response.json();
}

// Phase 8 Behavioral Detection Interfaces
export interface BehavioralFinding {
  detection_id: string;
  dataset_id: string;
  detection_type: string;
  entity_type: string;
  entity_id: string;
  severity_indicator: string;
  confidence: number;
  observed_facts: Record<string, unknown>;
  supporting_transaction_ids: string[];
  supporting_ips: string[];
  first_seen?: string | null;
  last_seen?: string | null;
  parameters: Record<string, unknown>;
  explanation: string;
  limitations: string[];
}

export interface DetectorSummary {
  detector_name: string;
  status: string;
  findings_count: number;
  message?: string | null;
}

export interface BehaviorSummary {
  dataset_id: string;
  total_findings: number;
  findings_by_type: Record<string, number>;
  findings_by_severity: Record<string, number>;
  entities_flagged_count: number;
  detector_summaries: DetectorSummary[];
}

export interface BehavioralMetadata {
  dataset_id: string;
  detector_version: string;
  enabled_detectors: string[];
  configurable_thresholds: Record<string, unknown>;
  feature_definitions: Record<string, string>;
  limitations: string[];
  created_at: string;
}

export interface BehavioralDetectionRequest {
  min_fan_in_sources?: number;
  min_fan_out_destinations?: number;
  rapid_dispersion_window_seconds?: number;
  rapid_dispersion_min_destinations?: number;
  burst_window_seconds?: number;
  burst_min_tx_count?: number;
  dormancy_threshold_seconds?: number;
  min_multi_hop_depth?: number;
  max_multi_hop_depth?: number;
  min_peel_length?: number;
}

export interface BehavioralDetectionResult {
  dataset_id: string;
  summary: BehaviorSummary;
  findings: BehavioralFinding[];
}

// Phase 8 Behavioral Detection API Methods
export async function runBehavioralDetection(
  datasetId: string,
  request?: BehavioralDetectionRequest
): Promise<BehavioralDetectionResult> {
  const url = `${API_BASE_URL}/api/v1/behavior/${encodeURIComponent(datasetId)}/detect`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: request ? JSON.stringify(request) : undefined,
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(errorBody.detail || `Behavioral detection failed (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getBehaviorSummary(datasetId: string): Promise<BehaviorSummary> {
  const url = `${API_BASE_URL}/api/v1/behavior/${encodeURIComponent(datasetId)}/summary`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load behavior summary (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getBehaviorFindings(
  datasetId: string,
  filters?: {
    detectionType?: string;
    entityType?: string;
    minimumConfidence?: number;
    limit?: number;
  }
): Promise<BehavioralFinding[]> {
  let url = `${API_BASE_URL}/api/v1/behavior/${encodeURIComponent(datasetId)}/findings?limit=${filters?.limit ?? 50}`;
  if (filters?.detectionType) {
    url += `&detection_type=${encodeURIComponent(filters.detectionType)}`;
  }
  if (filters?.entityType) {
    url += `&entity_type=${encodeURIComponent(filters.entityType)}`;
  }
  if (filters?.minimumConfidence !== undefined && filters?.minimumConfidence !== null) {
    url += `&minimum_confidence=${filters.minimumConfidence}`;
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load behavior findings (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getBehaviorMetadata(datasetId: string): Promise<BehavioralMetadata> {
  const url = `${API_BASE_URL}/api/v1/behavior/${encodeURIComponent(datasetId)}/metadata`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load behavior metadata (HTTP ${response.status})`);
  }
  return response.json();
}

// Phase 9 Risk Scoring & Explainability Interfaces
export interface EvidenceContribution {
  source: string;
  points: number;
  max_points: number;
  status: 'present' | 'not_observed' | 'data_unavailable' | string;
  observed_facts: Record<string, unknown>;
  rationale: string;
}

export interface RiskFinding {
  risk_id: string;
  dataset_id: string;
  entity_type: string;
  entity_id: string;
  score: number;
  priority: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL' | string;
  confidence: number;
  evidence_contributions: Record<string, EvidenceContribution>;
  supporting_behavior_findings: string[];
  ml_evidence?: Record<string, unknown> | null;
  graph_evidence?: Record<string, unknown> | null;
  clustering_evidence?: Record<string, unknown> | null;
  activity_evidence?: Record<string, unknown> | null;
  explanation: string;
  limitations: string[];
  scoring_version: string;
}

export interface RiskSummary {
  dataset_id: string;
  total_scored_entities: number;
  counts_by_priority: Record<string, number>;
  average_score: number;
  highest_score: number;
  evidence_coverage: Record<string, number>;
  scoring_version: string;
}

export interface RiskMetadata {
  dataset_id: string;
  scoring_version: string;
  weights: Record<string, number>;
  thresholds: Record<string, unknown>;
  score_range: { min: number; max: number };
  priority_bands: Record<string, string>;
  evidence_sources: string[];
  limitations: string[];
  created_at: string;
}

export interface RiskScoringRequest {
  behavioral_weight?: number;
  ml_weight?: number;
  clustering_weight?: number;
  graph_weight?: number;
  activity_weight?: number;
}

export interface RiskScoringResult {
  dataset_id: string;
  summary: RiskSummary;
  findings: RiskFinding[];
}

// Phase 9 Risk Scoring API Methods
export async function runRiskScoring(
  datasetId: string,
  request?: RiskScoringRequest
): Promise<RiskScoringResult> {
  const url = `${API_BASE_URL}/api/v1/risk/${encodeURIComponent(datasetId)}/score`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: request ? JSON.stringify(request) : undefined,
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(errorBody.detail || `Risk scoring failed (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getRiskSummary(datasetId: string): Promise<RiskSummary> {
  const url = `${API_BASE_URL}/api/v1/risk/${encodeURIComponent(datasetId)}/summary`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load risk summary (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getRiskFindings(
  datasetId: string,
  filters?: {
    priority?: string;
    entityType?: string;
    minimumScore?: number;
    limit?: number;
  }
): Promise<RiskFinding[]> {
  let url = `${API_BASE_URL}/api/v1/risk/${encodeURIComponent(datasetId)}/findings?limit=${filters?.limit ?? 50}`;
  if (filters?.priority) {
    url += `&priority=${encodeURIComponent(filters.priority)}`;
  }
  if (filters?.entityType) {
    url += `&entity_type=${encodeURIComponent(filters.entityType)}`;
  }
  if (filters?.minimumScore !== undefined && filters?.minimumScore !== null) {
    url += `&minimum_score=${filters.minimumScore}`;
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load risk findings (HTTP ${response.status})`);
  }
  return response.json();
}

export async function getRiskMetadata(datasetId: string): Promise<RiskMetadata> {
  const url = `${API_BASE_URL}/api/v1/risk/${encodeURIComponent(datasetId)}/metadata`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load risk metadata (HTTP ${response.status})`);
  }
  return response.json();
}

// Phase 12 Evidence & Forensic Reporting Interfaces
export interface EvidenceArtifactInfo {
  artifact_id: string;
  dataset_id: string;
  artifact_type: 'evidence_package' | 'forensic_report_pdf' | string;
  filename: string;
  created_at: string;
  file_size_bytes: number;
  sha256_hash: string;
  verification_status: 'verified' | 'tampered' | 'missing' | 'unverified' | string;
  description?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface EvidenceVerificationResult {
  artifact_id: string;
  dataset_id: string;
  filename: string;
  recorded_sha256: string;
  computed_sha256?: string | null;
  status: 'verified' | 'tampered' | 'missing' | string;
  is_valid: boolean;
  verified_at: string;
  message: string;
}

export interface EvidencePackageRequest {
  case_reference?: string;
  investigator_name?: string;
  notes?: string;
  hypothesis?: string;
  include_transactions_limit?: number;
}

export interface ForensicReportRequest {
  case_reference?: string;
  investigator_name?: string;
  organization?: string;
  notes?: string;
  hypothesis?: string;
  include_executive_summary?: boolean;
  include_technical_details?: boolean;
}

// Phase 12 Evidence API Methods
export async function generateEvidencePackage(
  datasetId: string,
  request?: EvidencePackageRequest
): Promise<EvidenceArtifactInfo> {
  const url = `${API_BASE_URL}/api/v1/evidence/${encodeURIComponent(datasetId)}/package`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: request ? JSON.stringify(request) : undefined,
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(errorBody.detail || `Evidence packaging failed (HTTP ${response.status})`);
  }
  return response.json();
}

export async function generateForensicReport(
  datasetId: string,
  request?: ForensicReportRequest
): Promise<EvidenceArtifactInfo> {
  const url = `${API_BASE_URL}/api/v1/evidence/${encodeURIComponent(datasetId)}/report`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: request ? JSON.stringify(request) : undefined,
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(errorBody.detail || `Forensic report generation failed (HTTP ${response.status})`);
  }
  return response.json();
}

export async function listEvidenceArtifacts(datasetId: string): Promise<EvidenceArtifactInfo[]> {
  const url = `${API_BASE_URL}/api/v1/evidence/${encodeURIComponent(datasetId)}/artifacts`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load evidence artifacts (HTTP ${response.status})`);
  }
  return response.json();
}

export async function verifyEvidenceArtifact(
  datasetId: string,
  artifactId: string
): Promise<EvidenceVerificationResult> {
  const url = `${API_BASE_URL}/api/v1/evidence/${encodeURIComponent(datasetId)}/artifacts/${encodeURIComponent(artifactId)}/verify`;
  const response = await fetch(url);
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(errorBody.detail || `Artifact verification failed (HTTP ${response.status})`);
  }
  return response.json();
}

export function getEvidenceArtifactDownloadUrl(datasetId: string, artifactId: string): string {
  return `${API_BASE_URL}/api/v1/evidence/${encodeURIComponent(datasetId)}/artifacts/${encodeURIComponent(artifactId)}/download`;
}

export async function fetchEvidencePackageContent(datasetId: string, artifactId: string): Promise<Record<string, unknown>> {
  const url = getEvidenceArtifactDownloadUrl(datasetId, artifactId);
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to retrieve evidence package JSON (HTTP ${response.status})`);
  }
  return response.json();
}

export { API_BASE_URL };
