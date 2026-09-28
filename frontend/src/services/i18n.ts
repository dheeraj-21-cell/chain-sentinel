import { useState } from 'react';

export type Language = 'en' | 'hi' | 'hinglish';

const LANG_STORAGE_KEY = 'bitcoin_intel_lang';

export const translations = {
  en: {
    // Navigation & Common
    platform_title: 'BITCOIN INTEL',
    platform_subtitle: 'FORENSIC SUITE',
    case_label: 'Case',
    active_dataset: 'Active Dataset',
    no_dataset: 'No Dataset Selected',
    investigator: 'Investigator',
    search_placeholder: 'Search Wallets, TXIDs, IPs...',
    search_shortcut: 'Ctrl+K',
    back_to_dashboard: '← Dashboard & Modules',
    switch_module: 'Jump to Module...',
    explore: 'Explore →',
    run_pipelines: 'Run All Pipelines',
    upload_dataset: '+ Upload Dataset',
    upload_modal_title: 'Upload Forensic Dataset',
    upload_modal_desc: 'Ingest raw Bitcoin transaction or P2P network telemetry records (CSV, JSON, XML).',
    drag_drop_file: 'Drag & drop file here, or click to browse',
    supported_formats: 'Supported formats: CSV, JSON, XML (Max 50MB)',
    selected_file: 'Selected File',
    cancel: 'Cancel',
    upload_and_validate: 'Upload & Ingest',
    uploading: 'Ingesting & Validating...',
    upload_success_title: 'Dataset Successfully Ingested',
    switch_to_dataset: 'Inspect This Dataset',
    refresh: 'Refresh',
    offline_engine: 'Air-Gapped Forensic Engine',
    all_modules: 'All Forensic Modules',

    // Dashboard
    dashboard_title: 'Executive Investigation Dashboard',
    dashboard_subtitle: 'Forensic intelligence synthesis across DuckDB columnar queries, Neo4j graphs, Isolation Forest ML, and behavioral detection.',
    summary_banner_title: 'Active Case Intelligence Summary',
    summary_banner_desc: 'Deterministic multi-signal correlation of blockchain transactions and peer-to-peer network observations.',
    total_txs: 'Total Transactions',
    total_txs_sub: 'Validated ledger records',
    unique_wallets: 'Unique Wallets',
    unique_wallets_sub: 'Observed input & output addresses',
    total_volume: 'Total Output Volume',
    total_volume_sub: 'Cumulative Bitcoin transferred',
    network_peers: 'Network Peers / IPs',
    network_peers_sub: 'Observed communicating endpoints',
    ml_anomalies: 'ML Flagged Anomalies',
    ml_anomalies_sub: 'Isolation Forest outliers',
    high_risk_alerts: 'High/Critical Risk Alerts',
    high_risk_alerts_sub: 'Priority scored entities',
    activity_over_time: 'Activity & Volume Over Time',
    risk_prioritization: 'Multi-Pipeline Risk Prioritization',
    top_prioritized: 'Top Prioritized Entities',
    view_all_risk: 'View All Risk & Alerts →',

    // Modules Flashcards
    card_datasets_title: 'Datasets & Ingestion',
    card_datasets_desc: 'Upload, validate, and normalize Bitcoin ledger and network records.',
    card_txs_title: 'Transactions Ledger',
    card_txs_desc: 'Inspect confirmed Bitcoin transactions, amounts, and associated fees.',
    card_wallets_title: 'Wallet Intelligence',
    card_wallets_desc: 'Review prioritized entities, balance flows, and connection degrees.',
    card_network_title: 'Network Analysis',
    card_network_desc: 'Examine peer IP addresses, ASNs, and geographical correlations.',
    card_graph_title: 'Graph Investigation',
    card_graph_desc: 'Trace entity connections, transaction flows, and observed IP nodes.',
    card_anomalies_title: 'AI/ML Anomalies',
    card_anomalies_desc: 'Identify structural outliers detected by unsupervised Isolation Forest.',
    card_clusters_title: 'Behavioral Clusters',
    card_clusters_desc: 'Analyze entity groupings and noise points discovered by DBSCAN.',
    card_risk_title: 'Risk & Alerts',
    card_risk_desc: 'Inspect explainable risk scores combining 5 intelligence pipelines.',
    card_evidence_title: 'Evidence & Reports',
    card_evidence_desc: 'Generate SHA-256 tamper-evident JSON packages and forensic PDF reports.',
    card_status_title: 'System Status',
    card_status_desc: 'Check backend API, Neo4j, DuckDB, and worker service health.',

    // Wallet Intelligence
    wallet_intel_title: 'Wallet Intelligence Directory',
    wallet_intel_subtitle: 'Correlate on-chain Wallet addresses with flow metrics, behavioral patterns, and multi-pipeline risk priorities.',
    why_prioritized: 'Why prioritized?',
    transactions_count: 'Transactions',
    connections_count: 'Connections',
    behavior_pattern: 'Behavior Pattern',
    ml_status: 'ML Status',
    open_investigation: 'Open Investigation →',
    search_wallet_placeholder: 'Search Wallet address...',
    filter_all_priority: 'All Priorities',

    // Investigation Modal / Dossier
    investigation_dossier: 'WALLET INVESTIGATION',
    entity_investigation: 'ENTITY INVESTIGATION',
    dossier_why_title: 'Executive Investigative Summary',
    tab_overview: 'Overview',
    tab_transactions: 'Transactions',
    tab_graph: 'Graph',
    tab_ml: 'ML Analysis',
    tab_behavior: 'Behavior',
    tab_network: 'Network',
    tab_evidence: 'Evidence',
    btn_view_txs: 'View Transactions',
    btn_view_graph: 'View in Graph',
    btn_view_evidence: 'View Evidence',

    // Graph Workspace
    graph_title: 'Graph Investigation Workspace',
    graph_subtitle: 'Explore entity relationships, transaction flows, and observed network telemetry.',
    graph_search_placeholder: 'Search Wallet, TXID, or IP address...',
    graph_search_btn: 'Search',
    graph_fit_btn: 'Fit Graph',
    graph_reset_btn: 'Reset',
    graph_legend_btn: 'Legend',
    graph_selected_entity: 'Selected Entity',
    observed_ips: 'Observed IPs',
    connected_wallets: 'Connected Wallets',
    observed_txs: 'Observed Transactions',
    large_graph_notice: 'Large graph detected. Search for a Wallet, TXID, or IP to inspect its immediate neighborhood.',
    network_disclaimer: 'Network observations represent dataset correlations and do not imply definitive ownership or criminal attribution.',

    // Status & Empty States
    empty_no_dataset: 'No Active Dataset Selected',
    empty_no_dataset_desc: 'Upload a Bitcoin transaction CSV file or select an ingested dataset from the top bar.',
    loading_label: 'Analyzing dataset...',
  },

  hi: {
    // Navigation & Common
    platform_title: 'BITCOIN INTEL',
    platform_subtitle: 'फोरेंसिक सुइट',
    case_label: 'केस',
    active_dataset: 'सक्रिय डेटासेट',
    no_dataset: 'कोई डेटासेट चुना नहीं गया',
    investigator: 'जांचकर्ता',
    search_placeholder: 'Wallet, TXID, IP खोजें...',
    search_shortcut: 'Ctrl+K',
    back_to_dashboard: '← डैशबोर्ड और मॉड्यूल',
    switch_module: 'मॉड्यूल बदलें...',
    explore: 'देखें →',
    run_pipelines: 'सभी पाइपलाइन चलाएं',
    upload_dataset: '+ डेटासेट अपलोड करें',
    upload_modal_title: 'फोरेंसिक डेटासेट अपलोड करें',
    upload_modal_desc: 'कच्चे बिटकॉइन लेन-देन या P2P नेटवर्क टेलीमेट्री रिकॉर्ड्स (CSV, JSON, XML) शामिल करें।',
    drag_drop_file: 'फ़ाइल यहाँ खींचें और छोड़ें, या ब्राउज़ करने के लिए क्लिक करें',
    supported_formats: 'समर्थित प्रारूप: CSV, JSON, XML (अधिकतम 50MB)',
    selected_file: 'चयनित फ़ाइल',
    cancel: 'रद्द करें',
    upload_and_validate: 'अपलोड और शामिल करें',
    uploading: 'अपलोड और सत्यापन जारी है...',
    upload_success_title: 'डेटासेट सफलतापूर्वक लोड हो गया',
    switch_to_dataset: 'इस डेटासेट का निरीक्षण करें',
    refresh: 'रिफ्रेश करें',
    offline_engine: 'एयर-गैप्ड फोरेंसिक इंजन',
    all_modules: 'सभी फोरेंसिक मॉड्यूल',

    // Dashboard
    dashboard_title: 'कार्यकारी जांच डैशबोर्ड',
    dashboard_subtitle: 'DuckDB, Neo4j, Isolation Forest ML और व्यवहार जांच का फोरेंसिक विश्लेषण।',
    summary_banner_title: 'सक्रिय केस जांच सारांश',
    summary_banner_desc: 'ब्लॉकचेन लेनदेन और पीयर-टू-पीयर नेटवर्क अवलोकनों का बहु-संकेत सहसंबंध।',
    total_txs: 'कुल लेनदेन',
    total_txs_sub: 'सत्यापित बहीखाता रिकॉर्ड्स',
    unique_wallets: 'विशिष्ट Wallets',
    unique_wallets_sub: 'देखे गए इनपुट और आउटपुट पते',
    total_volume: 'कुल आउटपुट वॉल्यूम',
    total_volume_sub: 'कुल ट्रांसफर किया गया Bitcoin',
    network_peers: 'नेटवर्क पीयर्स / IPs',
    network_peers_sub: 'देखे गए संचार एंडपॉइंट्स',
    ml_anomalies: 'ML विसंगतियां',
    ml_anomalies_sub: 'Isolation Forest निष्कर्ष',
    high_risk_alerts: 'उच्च/गंभीर जोखिम अलर्ट',
    high_risk_alerts_sub: 'प्राथमिकता-प्राप्त इकाइयां',
    activity_over_time: 'समय के अनुसार गतिविधि और वॉल्यूम',
    risk_prioritization: 'बहु-पाइपलाइन जोखिम प्राथमिकता',
    top_prioritized: 'शीर्ष प्राथमिकता वाली इकाइयां',
    view_all_risk: 'सभी जोखिम और अलर्ट देखें →',

    // Modules Flashcards
    card_datasets_title: 'डेटासेट्स और इनजेशन',
    card_datasets_desc: 'Bitcoin बहीखाता और नेटवर्क रिकॉर्ड अपलोड, सत्यापित और सामान्य करें।',
    card_txs_title: 'लेनदेन लेजर',
    card_txs_desc: 'सत्यापित लेनदेन, राशियां और संबंधित नेटवर्क शुल्क की समीक्षा करें।',
    card_wallets_title: 'Wallet इंटेलिजेंस',
    card_wallets_desc: 'प्राथमिकता वाली इकाइयों, बैलेंस प्रवाह और कनेक्शन डिग्री की जांच करें।',
    card_network_title: 'नेटवर्क विश्लेषण',
    card_network_desc: 'पीयर IP पते, ASNs और भौगोलिक सहसंबंधों की जांच करें।',
    card_graph_title: 'Graph जांच',
    card_graph_desc: 'इकाइयों के संबंध, लेनदेन प्रवाह और देखे गए IP नोड्स का पता लगाएं।',
    card_anomalies_title: 'AI/ML विसंगतियां',
    card_anomalies_desc: 'Isolation Forest द्वारा पाई गई संरचनात्मक विसंगतियों की पहचान करें।',
    card_clusters_title: 'व्यवहार क्लस्टर',
    card_clusters_desc: 'DBSCAN द्वारा खोजे गए व्यवहार समूहों और नॉइज़ की जांच करें।',
    card_risk_title: 'जोखिम और अलर्ट',
    card_risk_desc: '5 इंटेलिजेंस पाइपलाइनों को मिलाकर व्याख्या योग्य जोखिम स्कोर की समीक्षा करें।',
    card_evidence_title: 'सबूत और रिपोर्ट्स',
    card_evidence_desc: 'SHA-256 डिजिटल हस्ताक्षर पैकेज और फोरेंसिक PDF रिपोर्ट बनाएं।',
    card_status_title: 'सिस्टम स्थिति',
    card_status_desc: 'FastAPI, Neo4j, DuckDB और वर्कर सेवाओं की स्थिति जांचें।',

    // Wallet Intelligence
    wallet_intel_title: 'Wallet इंटेलिजेंस डायरेक्टरी',
    wallet_intel_subtitle: 'ऑन-चेन Wallet पतों को फ्लो मेट्रिक्स, व्यवहार पैटर्न और जोखिम प्राथमिकताओं के साथ सहसंबंधित करें।',
    why_prioritized: 'क्यों प्राथमिकता दी गई?',
    transactions_count: 'लेनदेन',
    connections_count: 'कनेक्शन',
    behavior_pattern: 'व्यवहार पैटर्न',
    ml_status: 'ML स्थिति',
    open_investigation: 'जांच खोलें →',
    search_wallet_placeholder: 'Wallet पता खोजें...',
    filter_all_priority: 'सभी प्राथमिकताएं',

    // Investigation Modal / Dossier
    investigation_dossier: 'WALLET जांच',
    entity_investigation: 'इकाई जांच',
    dossier_why_title: 'कार्यकारी जांच सारांश',
    tab_overview: 'अवलोकन',
    tab_transactions: 'लेनदेन',
    tab_graph: 'Graph',
    tab_ml: 'ML विश्लेषण',
    tab_behavior: 'व्यवहार',
    tab_network: 'नेटवर्क',
    tab_evidence: 'सबूत',
    btn_view_txs: 'लेनदेन देखें',
    btn_view_graph: 'Graph में देखें',
    btn_view_evidence: 'सबूत देखें',

    // Graph Workspace
    graph_title: 'Graph जांच कार्यक्षेत्र',
    graph_subtitle: 'इकाई संबंधों, लेनदेन प्रवाह और देखे गए नेटवर्क डेटा की खोज करें।',
    graph_search_placeholder: 'Wallet, TXID या IP पता खोजें...',
    graph_search_btn: 'खोजें',
    graph_fit_btn: 'Graph फ़िट करें',
    graph_reset_btn: 'रीसेट',
    graph_legend_btn: 'संकेत (Legend)',
    graph_selected_entity: 'चयनित इकाई',
    observed_ips: 'देखे गए IPs',
    connected_wallets: 'जुड़े हुए Wallets',
    observed_txs: 'देखे गए लेनदेन',
    large_graph_notice: 'बड़ा ग्राफ मिला। पड़ोस की जांच के लिए Wallet, TXID या IP खोजें।',
    network_disclaimer: 'नेटवर्क अवलोकन केवल डेटासेट सहसंबंध हैं और सीधे स्वामित्व का दावा नहीं करते।',

    // Status & Empty States
    empty_no_dataset: 'कोई सक्रिय डेटासेट नहीं चुना गया',
    empty_no_dataset_desc: 'Bitcoin लेनदेन CSV फ़ाइल अपलोड करें या शीर्ष बार से डेटासेट चुनें।',
    loading_label: 'डेटासेट का विश्लेषण हो रहा है...',
  },

  hinglish: {
    // Navigation & Common
    platform_title: 'BITCOIN INTEL',
    platform_subtitle: 'FORENSIC SUITE',
    case_label: 'Case',
    active_dataset: 'Active Dataset',
    no_dataset: 'Koi Dataset Selected Nahi Hai',
    investigator: 'Investigator',
    search_placeholder: 'Wallet, TXID, ya IP search karein...',
    search_shortcut: 'Ctrl+K',
    back_to_dashboard: '← Dashboard & Modules',
    switch_module: 'Module Switch Karein...',
    explore: 'Explore Karein →',
    run_pipelines: 'Saari Pipelines Run Karein',
    upload_dataset: '+ Dataset Upload Karein',
    upload_modal_title: 'Forensic Dataset Upload Karein',
    upload_modal_desc: 'Raw Bitcoin transaction ya P2P network telemetry records (CSV, JSON, XML) ingest karein.',
    drag_drop_file: 'File yahan drag & drop karein, ya browse karne ke liye click karein',
    supported_formats: 'Supported formats: CSV, JSON, XML (Max 50MB)',
    selected_file: 'Selected File',
    cancel: 'Cancel',
    upload_and_validate: 'Upload & Ingest Karein',
    uploading: 'Ingesting & Validating...',
    upload_success_title: 'Dataset Successfully Ingest Ho Gaya',
    switch_to_dataset: 'Is Dataset Ko Inspect Karein',
    refresh: 'Refresh Karein',
    offline_engine: 'Air-Gapped Forensic Engine',
    all_modules: 'All Forensic Modules',

    // Dashboard
    dashboard_title: 'Executive Investigation Dashboard',
    dashboard_subtitle: 'DuckDB columnar queries, Neo4j graph, Isolation Forest ML aur behavioral detection ka forensic analysis.',
    summary_banner_title: 'Active Case Investigation Summary',
    summary_banner_desc: 'Blockchain transactions aur peer-to-peer network observations ka evidence-based correlation.',
    total_txs: 'Total Transactions',
    total_txs_sub: 'Validated ledger records',
    unique_wallets: 'Unique Wallets',
    unique_wallets_sub: 'Observed input aur output addresses',
    total_volume: 'Total Output Volume',
    total_volume_sub: 'Cumulative Bitcoin volume transferred',
    network_peers: 'Network Peers / IPs',
    network_peers_sub: 'Observed communicating endpoints',
    ml_anomalies: 'ML Anomalies',
    ml_anomalies_sub: 'Isolation Forest flagged outliers',
    high_risk_alerts: 'High/Critical Risk Alerts',
    high_risk_alerts_sub: 'Prioritized scored entities',
    activity_over_time: 'Activity & Volume Timeline',
    risk_prioritization: 'Multi-Pipeline Risk Prioritization',
    top_prioritized: 'Top Prioritized Entities',
    view_all_risk: 'Saare Risk & Alerts Dekhein →',

    // Modules Flashcards
    card_datasets_title: 'Datasets & Ingestion',
    card_datasets_desc: 'Bitcoin ledger aur network CSV records upload, validate aur normalize karein.',
    card_txs_title: 'Transactions Ledger',
    card_txs_desc: 'Confirmed transactions, BTC amounts aur network fees inspect karein.',
    card_wallets_title: 'Wallet Intelligence',
    card_wallets_desc: 'Prioritized entities, balance flows aur connection degrees review karein.',
    card_network_title: 'Network Analysis',
    card_network_desc: 'Peer IP addresses, ASNs aur geographic locations examine karein.',
    card_graph_title: 'Graph Investigation',
    card_graph_desc: 'Entity connections, transaction flows aur observed IP nodes trace karein.',
    card_anomalies_title: 'AI/ML Anomalies',
    card_anomalies_desc: 'Isolation Forest se detect hue statistical outliers check karein.',
    card_clusters_title: 'Behavioral Clusters',
    card_clusters_desc: 'DBSCAN clustering dwara discover hue patterns aur noise points review karein.',
    card_risk_title: 'Risk & Alerts',
    card_risk_desc: '5 pipelines se banaye gaye explainable risk scores inspect karein.',
    card_evidence_title: 'Evidence & Reports',
    card_evidence_desc: 'SHA-256 cryptographic packages aur forensic PDF reports generate karein.',
    card_status_title: 'System Status',
    card_status_desc: 'FastAPI backend, Neo4j, DuckDB aur overall health monitor karein.',

    // Wallet Intelligence
    wallet_intel_title: 'Wallet Intelligence Directory',
    wallet_intel_subtitle: 'On-chain Wallet addresses ko flow metrics, behavioral patterns aur risk priorities ke sath correlate karein.',
    why_prioritized: 'Priority kyun mili?',
    transactions_count: 'Transactions',
    connections_count: 'Connections',
    behavior_pattern: 'Behavior Pattern',
    ml_status: 'ML Status',
    open_investigation: 'Investigation Kholein →',
    search_wallet_placeholder: 'Wallet address search karein...',
    filter_all_priority: 'Sabhi Priorities',

    // Investigation Modal / Dossier
    investigation_dossier: 'WALLET INVESTIGATION',
    entity_investigation: 'ENTITY INVESTIGATION',
    dossier_why_title: 'Executive Investigative Summary',
    tab_overview: 'Overview',
    tab_transactions: 'Transactions',
    tab_graph: 'Graph',
    tab_ml: 'ML Analysis',
    tab_behavior: 'Behavior',
    tab_network: 'Network',
    tab_evidence: 'Evidence',
    btn_view_txs: 'Transactions Dekhein',
    btn_view_graph: 'Graph Mein Dekhein',
    btn_view_evidence: 'Evidence Dekhein',

    // Graph Workspace
    graph_title: 'Graph Investigation Workspace',
    graph_subtitle: 'Entity relationships, transaction flows aur observed network telemetry explore karein.',
    graph_search_placeholder: 'Wallet, TXID, ya IP address search karein...',
    graph_search_btn: 'Search',
    graph_fit_btn: 'Fit Graph',
    graph_reset_btn: 'Reset',
    graph_legend_btn: 'Legend',
    graph_selected_entity: 'Selected Entity',
    observed_ips: 'Observed IPs',
    connected_wallets: 'Connected Wallets',
    observed_txs: 'Observed Transactions',
    large_graph_notice: 'Bada graph detected. Surrounding neighborhood dekhne ke liye Wallet, TXID ya IP search karein.',
    network_disclaimer: 'Network observations dataset correlation dikhate hain, ye legal criminal proof nahi hain.',

    // Status & Empty States
    empty_no_dataset: 'Koi Active Dataset Selected Nahi Hai',
    empty_no_dataset_desc: 'Bitcoin transaction CSV file upload karein ya top bar se dataset select karein.',
    loading_label: 'Dataset analyze ho raha hai...',
  },
};

export type TranslationKey = keyof typeof translations.en;

export function getInitialLanguage(): Language {
  try {
    const saved = localStorage.getItem(LANG_STORAGE_KEY);
    if (saved === 'en' || saved === 'hi' || saved === 'hinglish') {
      return saved;
    }
  } catch {
    // localStorage not accessible
  }
  return 'en';
}

export function useI18n() {
  const [lang, setLangState] = useState<Language>(getInitialLanguage);

  const setLang = (newLang: Language) => {
    setLangState(newLang);
    try {
      localStorage.setItem(LANG_STORAGE_KEY, newLang);
    } catch {
      // storage unavailable
    }
  };

  const t = (key: TranslationKey): string => {
    const dict = translations[lang] || translations.en;
    return dict[key] || translations.en[key] || key;
  };

  return { lang, setLang, t };
}
