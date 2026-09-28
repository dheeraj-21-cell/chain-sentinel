# Bitcoin Transaction Intelligence & Investigation Platform

> **Smart India Hackathon (SIH) 2026 — Forensic Blockchain Intelligence Platform**  
> An offline-first, forensic-grade investigative intelligence platform designed to trace Bitcoin transactions, correlate peer-to-peer network telemetry, detect anomalous laundering behaviors, and produce court-ready tamper-evident evidence packages.

---

## 1. Executive Summary & Architecture

The platform operates as a completely offline, containerized forensic intelligence suite combining high-performance columnar analytics, graph database modeling, unsupervised machine learning, and heuristic behavioral detection.

```
                                  +-------------------------------------------------------------+
                                  |              Web Frontend (React 18 + Vite)                 |
                                  |   - Cytoscape.js Topology Flow Workspace                    |
                                  |   - 7-Section Forensic Entity Investigation Summary         |
                                  |   - Multilingual Interface (English / Hindi / Hinglish)     |
                                  |   - Dark / Cyber Light Themes                               |
                                  +-------------------------------------------------------------+
                                                                 |
                                                    HTTP / REST API (Port 8000)
                                                                 v
+-------------------------------------------------------------------------------------------------------------------------------+
|                                                    Backend (FastAPI)                                                          |
|                                                                                                                               |
|   +--------------------------+   +--------------------------+   +--------------------------+   +--------------------------+   |
|   |   Validation & Ingest    |   |    Columnar Analytics    |   |     Graph Analysis       |   |   Unsupervised ML &      |   |
|   |   - Polars Parser        |   |    - DuckDB SQL Engine   |   |     - Neo4j Community    |   |     Behavioral Detectors |   |
|   |   - PyArrow Parquet      |   |    - Window Aggregates   |   |     - NetworkX Analytics |   |   - Isolation Forest     |   |
|   |   - Deduplication SHA    |   |    - In-Memory Flow      |   |     - 4-Tier Topology    |   |   - DBSCAN Clustering    |   |
|   +--------------------------+   +--------------------------+   +--------------------------+   |   - 7 Heuristic Engines  |   |
|                                                                                                +--------------------------+   |
|   +-----------------------------------------------------------------------------------------------------------------------+   |
|   |                                          Forensic Evidence & Reporting Layer                                          |   |
|   |   - Multi-Signal Risk Scoring (100 pt transparent rubric)                                                             |   |
|   |   - Tripartite Separation ([OBSERVED FACTS] | [MODEL INTERPRETATION] | [INVESTIGATOR HYPOTHESIS])                     |   |
|   |   - SHA-256 Cryptographic Packaging & Tamper Verification                                                             |   |
|   |   - ReportLab 4.2 Two-Pass PDF Forensic Report Generator                                                              |   |
|   +-----------------------------------------------------------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------------------------------------------------------+
        |                                                 |                                                  |
        v                                                 v                                                  v
+-------------------------------+             +-------------------------------+              +-------------------------------+
|     Data Lakehouse Storage    |             |      Graph Database Engine    |              |     Machine Learning Models   |
|     /data/processed/*.parquet |             |      bolt://neo4j:7687        |              |     /models/*.joblib          |
|     /data/evidence/*.json     |             |      http://localhost:7474    |              |     /data/features/*.parquet  |
+-------------------------------+             +-------------------------------+              +-------------------------------+
```

---

## 2. Platform Principles & Forensic Standards

1. **Zero Fake or Synthetic Intelligence**:
   - Every metric, chart value, graph node, relationship, risk score, and alert is computed live from the active dataset.
   - Zero hardcoded mock results, simulated alerts, or synthetic graph nodes exist in the codebase.
2. **Offline-First Independence**:
   - Zero external cloud AI calls (no OpenAI, no Anthropic, no Google Cloud).
   - Zero public blockchain RPC or explorer dependencies.
   - All models, analytics, graph queries, and PDF engines run self-contained locally.
3. **Rigid Tripartite Forensic Separation**:
   - Every investigation dossier cleanly separates:
     - `[OBSERVED FACTS]`: Immutable ledger and network telemetry records.
     - `[MODEL INTERPRETATION]`: Statistical anomaly percentiles and DBSCAN cluster groupings.
     - `[INVESTIGATOR HYPOTHESIS]`: Working leads and notes requiring manual verification.
   - Strict non-attribution disclaimers prevent premature accusations of criminality.
4. **Dataset Isolation & Reproducibility**:
   - Datasets are content-hashed (SHA-256) on ingestion to prevent duplication.
   - All DuckDB, Neo4j, ML, and risk artifacts are strictly partitioned by `dataset_id`.

---

## 3. Quick Start & Docker Operations

### System Requirements:
- Docker 24+ & Docker Compose v2+
- Host OS: Linux, macOS, or Windows 10/11 with WSL2
- Ports: `8000` (FastAPI), `5173` (Vite UI), `7474` (Neo4j Browser), `7687` (Neo4j Bolt)

### Commands Reference:

| Action | Command |
| :--- | :--- |
| **Start Stack** | `docker compose up -d` |
| **Stop Stack** | `docker compose down` |
| **Restart Stack** | `docker compose restart` |
| **Rebuild Images** | `docker compose build` |
| **Container Status** | `docker compose ps` |
| **Backend Logs** | `docker logs -f bitcoin_intel_backend` |
| **Frontend Logs** | `docker logs -f bitcoin_intel_frontend` |
| **Neo4j Logs** | `docker logs -f bitcoin_intel_neo4j` |
| **API Health Check** | `curl -f http://localhost:8000/health` |
| **Run Backend Tests** | `docker exec bitcoin_intel_backend pytest` |
| **Build Frontend** | `cd frontend && npm run build` |

---

## 4. End-to-End Pipeline Walkthrough

```
CSV Upload (multipart/form-data)
  ↓
1. Validation & Parsing (Polars / PyArrow)
   - Checks schema headers, field types, timestamp validity, and positive BTC volumes.
   - Rejects malformed rows with isolated error reporting.
  ↓
2. Normalization & Content Hashing
   - Computes SHA-256 content hash to detect and reject duplicates.
   - Writes normalized columnar Parquet to /data/processed/{dataset_id}/normalized.parquet.
  ↓
3. Embedded Analytics (DuckDB)
   - Calculates volume distributions, transaction fee metrics, script type frequencies, and address balances.
  ↓
4. Graph Construction (Neo4j Community)
   - Projects Wallets, Transactions, Observed IPs, Countries, and ASNs.
   - Establishes HAS_INPUT, HAS_OUTPUT, OBSERVED_TRANSACTION, LOCATED_IN, and BELONGS_TO edges.
  ↓
5. Graph Topological Analysis (NetworkX)
   - Computes graph density, connected components, PageRank, and in/out-degree centrality.
  ↓
6. Unsupervised Anomaly Detection (Isolation Forest)
   - Trains dataset-isolated scikit-learn models over numerical features (amounts, fees, degrees).
   - Generates normalized anomaly scores ($0.0 - 1.0$) and feature contribution explanations.
  ↓
7. Behavioral Clustering (DBSCAN)
   - Identifies structural behavioral clusters and isolates noise points without predetermining cluster counts.
  ↓
8. Deterministic Behavioral Detectors (7 Heuristic Engines)
   - Fan-In (`FI`), Fan-Out (`FO`), Transaction Burst (`TB`), Rapid Dispersion (`RD`),
     Multi-Hop Movement (`MH`), Peeling Chain (`PC`), Dormant-to-Active (`DA`).
  ↓
9. Multi-Signal Risk Scoring (100-Point Formula)
   - Behavioral Detections: up to 35 points
   - ML Isolation Forest Anomaly: up to 25 points
   - DBSCAN Noise/Cluster: up to 15 points
   - Graph Topological Centrality: up to 15 points
   - High Transaction Volume: up to 10 points
  ↓
10. Forensic Evidence Packaging & Reporting
    - Packages all analytical outputs into an immutable evidence JSON file.
    - Computes SHA-256 checksum and signs manifest.
    - Generates court-ready ReportLab 4.2 NumberedCanvas PDF report with legal disclaimers.
```

---

## 5. Canonical SIH Showcase Dataset

The platform includes a curated, deterministic showcase dataset designed specifically for demonstration:

* **Filename**: `sih_showcase.csv` (Dataset ID: `87c747ba-76c6-4428-b6c7-6d3001670788`)
* **SHA-256**: `74cf52491c34e80bf28962e58dfe8ab59439104e3627e40164f7075e15f01bbb`
* **Metrics**: 16 valid transactions, 21 unique wallets, 4 observed IPs, 3 countries (`IN`, `US`, `DE`), 3 ASNs (`AS55836`, `AS13335`, `AS24940`), 28.296 BTC total volume.
* **Represented Laundering Patterns**:
  1. **Fan-In Consolidation**: 3 distinct donors (`1DonorAlpha...`, `1DonorBeta...`, `1DonorGamma...`) funding `1FanInRecipient11111111111111111` (3.4985 BTC).
  2. **Fan-Out & Rapid Dispersion**: `1FanOutDistributor...` dispersing 4.499 BTC to 3 payees in a single block.
  3. **Peeling Chain & Multi-Hop**: 3-hop peeling sequence peeling 0.5 BTC to merchants while transferring change forward to a cold vault.
  4. **Transaction Burst**: High-frequency trading burst of 3 transactions within 14 minutes from IP `198.51.100.42` (`IN`, `AS55836`).

---

## 6. Graph Canvas & Forensic Summary Standards

### Graph Canvas Visualization:
* **Topology Flow Layout (Default)**: Downward hierarchical layout separating nodes into 4 clear tiers:
  * **Tier 1 (Wallets)**: `y = 80px` (`○ W`, Cyan `#38bdf8`)
  * **Tier 2 (Transactions)**: `y = 260px` (`◇ TX`, Amber `#fbbf24`)
  * **Tier 3 (Observed IPs)**: `y = 440px` (`⬡ IP`, Purple `#a855f7`)
  * **Tier 4 (Infrastructure: Country & ASN)**: `y = 620px` (`▢ CC`, Emerald `#34d399` / `△ ASN`, Orange `#f97316`)
* **Collision Avoidance**: 150px horizontal node clearance; automatic viewport auto-fit with 60px padding.
* **Alternative Layout**: Force-directed (COSE) with strong node repulsion (`450,000`) and low gravity (`0.05`).
* **Interactive Highlighting**: Clicking any node highlights its 1-hop connected sub-graph and dims non-connected nodes to `0.18` opacity.
* **Prohibited Controls Excluded**: Legacy buttons (Hop Finder, +1/+2 Hop, Trace/Scan) are omitted to ensure zero canvas clutter.

### 7-Section Forensic Entity Summary (`EntityInvestigationSummary.tsx`):
1. **Priority Header**: Score dial, priority badge (`CRITICAL`, `HIGH`, `MODERATE`, `LOW`), copy button.
2. **Why Prioritized?**: Clear bulleted triggers derived from backend evidence.
3. **Transaction Activity**: Inbound/outbound counts, volume in BTC, first/last seen timestamps, duration.
4. **Network Telemetry**: Observed IPs, countries, ASNs, observation count. Shows *"No network observations available in dataset"* if unobserved.
5. **Behavioral Signals**: Mapped to standard abbreviations (`FI`, `FO`, `TB`, `RD`, `MH`, `PC`, `DA`) with facts, reasons, and review caveats.
6. **Machine Learning Signals**: Isolation Forest score, DBSCAN cluster ID or noise point classification.
7. **Contributing Risk Signals**: Exact points awarded out of 100 maximum points.
8. **Tripartite Separation**: Rigid forensic division into Observed Facts, Model Interpretation, and Investigator Hypothesis.

---

## 7. Recommended SIH Mentor Demo Flow

For presentations to mentors, evaluators, and jury members, follow this 12-step flow:

1. **System Start**: Verify containers with `docker compose ps` and open `http://localhost:5173`.
2. **Dashboard Overview**: Point out live KPI cards (16 transactions, 21 wallets, 4 IPs, 28.296 BTC volume, zero fake metrics).
3. **Dataset Selector**: In the top navigation bar, confirm `SIH Showcase Dataset (16 records)` is selected.
4. **Wallet Intelligence**: Navigate to **Wallet Intelligence**; inspect the high-risk entity `1BurstTrader4444444444444444444`.
5. **Why Prioritized?**: Open the entity drawer and show Section 1 explaining why the entity was flagged (burst velocity + ML anomaly).
6. **Network Telemetry**: Show Section 3 displaying real IP observation `198.51.100.42`, country `IN` (India), and ASN `AS55836` (Reliance Jio).
7. **Graph Investigation**: Navigate to **Graph Investigation**; observe the clean, uncluttered 4-tier **Topology Flow** layout.
8. **Sub-graph Highlighting**: Click on `1BurstTrader...` to highlight its immediate 1-hop transaction and IP neighbors.
9. **AI/ML & Behavioral Views**: Briefly navigate to **AI/ML Anomalies** (show Isolation Forest scores) and **Behavioral Clusters** (show DBSCAN groups).
10. **Risk & Alerts**: Show the transparent 100-point risk score distribution and evidentiary contributions.
11. **Evidence & Reports**: Navigate to **Evidence & Reports**; show the cryptographic SHA-256 package and click **Verify Integrity**.
12. **Forensic PDF Export**: Download and open the generated ReportLab PDF; show the two-pass page numbering, audit timestamps, and tripartite forensic separation.

---

## 8. Extensibility & Future Modification Readiness

The architecture is built modularly so future mentor feedback can be implemented without refactoring the platform:

* **Adding New Heuristic Detectors**: Implement new detectors in `backend/app/services/behavioral_detection.py` and register in `DETECTORS` dictionary.
* **Adding New ML Algorithms**: Add model classes in `backend/app/services/` following the pattern of `anomaly_detection.py` and `clustering.py`.
* **Adding New Dataset Formats**: Extend `backend/app/services/parsers.py` with new MIME/schema parsers.
* **Adding Multi-User Authentication**: Plug an authentication middleware into `backend/app/main.py` and protect endpoints via FastAPI dependencies.
* **Extending Graph Views**: Modify Cytoscape stylesheet rules or layout profiles in `frontend/src/views/GraphInvestigationView.tsx`.

---

## 9. Known Limitations

In the interest of full transparency and forensic accuracy, the current baseline has the following known limitations:

1. **Single Case / In-Memory Session**: The frontend currently operates on the selected active dataset without persistent multi-investigator case folders.
2. **Offline Geo-IP Resolution**: IP-to-Country and IP-to-ASN resolution currently relies on metadata present in the ingested dataset records or an offline MMDB file; real-time BGP routing lookups are omitted to preserve 100% offline isolation.
3. **Single Transaction Graph Limit**: The Cytoscape visualization caps default transaction rendering at 100 subgraphs to maintain 60 FPS browser rendering on mobile and laptop GPUs.
4. **Heuristic Confidence Bounds**: Behavioral pattern detectors use deterministic rule thresholds; entities operating just below parameter thresholds (e.g. 2 burst transactions instead of 3) are not flagged by the heuristic engine but are captured by the Isolation Forest ML model.
