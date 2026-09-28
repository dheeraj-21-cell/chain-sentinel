from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import polars as pl

from app import config
from app.models.risk import (
    EvidenceContribution,
    RiskFinding,
    RiskMetadata,
    RiskScoringRequest,
    RiskScoringResult,
    RiskSummary,
)
from app.services import (
    analytics,
    anomaly_detection,
    behavioral_detection,
    clustering,
    graph_analysis,
)
from app.services.storage import load_metadata


SCORING_VERSION = "1.0.0"

PRIORITY_BANDS: Dict[str, str] = {
    "LOW": "0.0 - 24.9",
    "MODERATE": "25.0 - 49.9",
    "HIGH": "50.0 - 74.9",
    "CRITICAL": "75.0 - 100.0",
}

EVIDENCE_SOURCES: List[str] = [
    "behavioral",
    "ml_anomaly",
    "clustering",
    "graph_topology",
    "activity_volume",
]

SYSTEM_LIMITATIONS: List[str] = [
    "Risk scores represent investigative prioritization only and do NOT imply guilt, culpability, or malicious intent.",
    "Scores are computed solely from dataset-isolated records and lack visibility into unobserved blockchain transactions.",
    "Confidence scores reflect multi-pipeline evidence completeness, NOT the probability that a crime occurred.",
    "Prohibited accusatory terms (criminal, ransomware, laundering, mixer, illegal) are strictly excluded from all outputs.",
]


def _make_risk_id(dataset_id: str, entity_type: str, entity_id: str) -> str:
    """Generate a deterministic risk finding identifier."""
    raw = f"{dataset_id}:{entity_type}:{entity_id}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()
    return f"RSK-{digest}"


def _assign_priority(score: float) -> str:
    """Determine priority band based on normalized score."""
    if score >= 75.0:
        return "CRITICAL"
    elif score >= 50.0:
        return "HIGH"
    elif score >= 25.0:
        return "MODERATE"
    else:
        return "LOW"


def _generate_explanation(
    entity_id: str,
    score: float,
    priority: str,
    confidence: float,
    contributions: Dict[str, EvidenceContribution],
) -> str:
    """Construct a neutral, human-readable forensic explanation detailing evidence drivers."""
    # Find active contributors sorted by points descending
    active = [c for c in contributions.values() if c.points > 0]
    active.sort(key=lambda c: c.points, reverse=True)

    if not active:
        return (
            f"Investigative priority is {priority} (Score: {score:.1f}/100, Confidence: {confidence:.2f}). "
            f"Entity '{entity_id}' was evaluated across all evidence pipelines with zero anomalous or elevated indicators observed. "
            f"Available dataset records show standard, unexceptional transactional behavior."
        )

    driver_phrases = []
    for c in active[:3]:
        if c.source == "behavioral":
            driver_phrases.append(f"behavioral indicators ({c.points:.1f} pts)")
        elif c.source == "ml_anomaly":
            driver_phrases.append(f"Isolation Forest statistical anomaly ({c.points:.1f} pts)")
        elif c.source == "clustering":
            driver_phrases.append(f"DBSCAN density outlier status ({c.points:.1f} pts)")
        elif c.source == "graph_topology":
            driver_phrases.append(f"graph connectivity degree ({c.points:.1f} pts)")
        elif c.source == "activity_volume":
            driver_phrases.append(f"observed transaction volume/telemetry ({c.points:.1f} pts)")

    drivers_str = ", ".join(driver_phrases)
    return (
        f"Investigative priority is {priority} (Score: {score:.1f}/100, Confidence: {confidence:.2f}). "
        f"Prioritization is elevated primarily by {drivers_str}. "
        f"The available dataset records and analytical models prioritize this entity for investigative review. "
        f"On-chain metadata does not establish entity ownership, attribution, or illicit intent."
    )


def run_risk_scoring(
    dataset_id: str,
    request: Optional[RiskScoringRequest] = None,
) -> RiskScoringResult:
    """Execute deterministic multi-pipeline risk scoring across all entities in the dataset."""
    metadata = load_metadata(dataset_id)
    if not metadata:
        raise FileNotFoundError(f"Dataset with ID '{dataset_id}' not found.")

    req = request or RiskScoringRequest()

    # Normalize weights so total max equals 100.0
    raw_total_weight = (
        req.behavioral_weight
        + req.ml_weight
        + req.clustering_weight
        + req.graph_weight
        + req.activity_weight
    )
    weight_scale = 100.0 / raw_total_weight if raw_total_weight > 0 else 1.0
    w_bhv = req.behavioral_weight * weight_scale
    w_ml = req.ml_weight * weight_scale
    w_clu = req.clustering_weight * weight_scale
    w_graph = req.graph_weight * weight_scale
    w_act = req.activity_weight * weight_scale

    # Check for empty dataset (records_valid == 0)
    if getattr(metadata, "records_valid", None) == 0:
        empty_summary = RiskSummary(
            dataset_id=dataset_id,
            total_scored_entities=0,
            counts_by_priority={"LOW": 0, "MODERATE": 0, "HIGH": 0, "CRITICAL": 0},
            average_score=0.0,
            highest_score=0.0,
            evidence_coverage={s: 0 for s in EVIDENCE_SOURCES},
            scoring_version=SCORING_VERSION,
        )
        return RiskScoringResult(
            dataset_id=dataset_id,
            summary=empty_summary,
            findings=[],
        )

    # 1. Collect all distinct wallets from normalized dataset
    parquet_path = config.PROCESSED_DATA_DIR / dataset_id / "normalized.parquet"
    if not parquet_path.is_file():
        raise FileNotFoundError(f"Normalized parquet file not found for dataset '{dataset_id}'.")
    df_norm = pl.read_parquet(parquet_path)

    all_wallets: Set[str] = set()
    wallet_ips: Dict[str, Set[str]] = {}

    for row in df_norm.to_dicts():
        inputs = [a for a in (row.get("input_addresses") or []) if a]
        outputs = [a for a in (row.get("output_addresses") or []) if a]
        src_ip = row.get("src_ip")
        for w in inputs + outputs:
            all_wallets.add(w)
            if src_ip:
                if w not in wallet_ips:
                    wallet_ips[w] = set()
                wallet_ips[w].add(src_ip)

    sorted_wallets = sorted(list(all_wallets))

    # 2. Gather Evidence: Phase 8 Behavioral Findings
    behavior_findings_map: Dict[str, List[Any]] = {}
    try:
        b_findings = behavioral_detection.get_behavior_findings(dataset_id, limit=5000)
        for bf in b_findings:
            if bf.entity_id not in behavior_findings_map:
                behavior_findings_map[bf.entity_id] = []
            behavior_findings_map[bf.entity_id].append(bf)
        bhv_available = True
    except Exception:
        bhv_available = False

    # 3. Gather Evidence: Phase 6 ML Anomalies
    ml_anomalies_map: Dict[str, Any] = {}
    try:
        anom_file = config.FEATURES_DATA_DIR / dataset_id / "wallet_anomalies.parquet"
        if not anom_file.is_file():
            anomaly_detection.train_and_evaluate_isolation_forest(dataset_id, "wallet")
        if anom_file.is_file():
            df_anom = pl.read_parquet(anom_file)
            for row in df_anom.to_dicts():
                ml_anomalies_map[row["entity_id"]] = row
        ml_available = True
    except Exception:
        ml_available = False

    # 4. Gather Evidence: Phase 7 DBSCAN Clusters
    clustering_map: Dict[str, Any] = {}
    try:
        clu_file = config.FEATURES_DATA_DIR / dataset_id / "wallet_clusters.parquet"
        if not clu_file.is_file():
            clustering.run_dbscan_clustering(dataset_id)
        if clu_file.is_file():
            df_clu = pl.read_parquet(clu_file)
            for row in df_clu.to_dicts():
                clustering_map[row["address"]] = row
        clu_available = True
    except Exception:
        clu_available = False

    # 5. Gather Evidence: Phase 5 NetworkX Graph Features
    graph_features_map: Dict[str, Any] = {}
    try:
        w_metrics = graph_analysis.get_wallet_features(dataset_id, limit=10000)
        for wm in w_metrics:
            graph_features_map[wm.address] = wm
        graph_available = True
    except Exception:
        graph_available = False

    # 6. Gather Evidence: Phase 3 Analytics & Flow
    analytics_map: Dict[str, Any] = {}
    try:
        w_acts = analytics.get_wallet_analytics(dataset_id, limit=10000)
        for wa in w_acts:
            analytics_map[wa.address] = wa
        act_available = True
    except Exception:
        act_available = False

    # 7. Evaluate each wallet across evidence categories
    findings: List[RiskFinding] = []
    coverage_counts: Dict[str, int] = {s: 0 for s in EVIDENCE_SOURCES}

    for address in sorted_wallets:
        contributions: Dict[str, EvidenceContribution] = {}
        evaluated_sources = 0

        # --- A. Behavioral Contribution ---
        if bhv_available:
            evaluated_sources += 1
            b_list = behavior_findings_map.get(address, [])
            if b_list:
                coverage_counts["behavioral"] += 1
                b_pts = 0.0
                types = []
                for bf in b_list:
                    types.append(bf.detection_type)
                    if bf.detection_type in ("peeling_chain_like", "rapid_dispersion", "transaction_burst"):
                        b_pts += 15.0 * (w_bhv / 35.0)
                    elif bf.detection_type in ("fan_in", "fan_out"):
                        fact_count = bf.observed_facts.get("distinct_source_count") or bf.observed_facts.get("distinct_destination_count", 0)
                        if fact_count >= 5:
                            b_pts += 12.0 * (w_bhv / 35.0)
                        else:
                            b_pts += 8.0 * (w_bhv / 35.0)
                    else:
                        b_pts += 8.0 * (w_bhv / 35.0)
                b_pts = min(b_pts, w_bhv)
                contributions["behavioral"] = EvidenceContribution(
                    source="behavioral",
                    points=round(b_pts, 2),
                    max_points=round(w_bhv, 2),
                    status="present",
                    observed_facts={"finding_count": len(b_list), "finding_types": sorted(list(set(types)))},
                    rationale=f"Observed {len(b_list)} behavioral finding(s): {', '.join(sorted(list(set(types))))}.",
                )
            else:
                contributions["behavioral"] = EvidenceContribution(
                    source="behavioral",
                    points=0.0,
                    max_points=round(w_bhv, 2),
                    status="not_observed",
                    observed_facts={"finding_count": 0},
                    rationale="No behavioral patterns met threshold for this wallet.",
                )
        else:
            contributions["behavioral"] = EvidenceContribution(
                source="behavioral",
                points=0.0,
                max_points=round(w_bhv, 2),
                status="data_unavailable",
                observed_facts={},
                rationale="Behavioral detection pipeline data unavailable.",
            )

        # --- B. ML Anomaly Contribution ---
        if ml_available:
            evaluated_sources += 1
            if address in ml_anomalies_map:
                coverage_counts["ml_anomaly"] += 1
                rec = ml_anomalies_map[address]
                is_anom = rec.get("is_anomaly", False)
                a_score = float(rec.get("anomaly_score", 0.5))
                raw_score = float(rec.get("raw_score", 0.0))
                if is_anom:
                    pts = 15.0 * (w_ml / 25.0) + (a_score - 0.5) * 20.0 * (10.0 / 25.0) * (w_ml / 25.0)
                    pts = min(max(pts, 0.0), w_ml)
                    rationale = f"Classified as Isolation Forest outlier (anomaly score: {a_score:.4f}, raw score: {raw_score:.4f})."
                else:
                    pts = 0.0
                    rationale = f"Evaluated by Isolation Forest and falls within normal baseline (score: {a_score:.4f})."
                contributions["ml_anomaly"] = EvidenceContribution(
                    source="ml_anomaly",
                    points=round(pts, 2),
                    max_points=round(w_ml, 2),
                    status="present",
                    observed_facts={"is_anomaly": is_anom, "anomaly_score": a_score, "raw_score": raw_score},
                    rationale=rationale,
                )
            else:
                contributions["ml_anomaly"] = EvidenceContribution(
                    source="ml_anomaly",
                    points=0.0,
                    max_points=round(w_ml, 2),
                    status="not_observed",
                    observed_facts={},
                    rationale="Entity was not profiled by ML anomaly detector.",
                )
        else:
            contributions["ml_anomaly"] = EvidenceContribution(
                source="ml_anomaly",
                points=0.0,
                max_points=round(w_ml, 2),
                status="data_unavailable",
                observed_facts={},
                rationale="ML anomaly detection data unavailable.",
            )

        # --- C. Clustering Contribution ---
        if clu_available:
            evaluated_sources += 1
            if address in clustering_map:
                coverage_counts["clustering"] += 1
                c_rec = clustering_map[address]
                is_noise = c_rec.get("is_noise", False)
                cid = c_rec.get("cluster_id", 0)
                if is_noise:
                    pts = w_clu
                    rationale = "Classified as isolated density outlier (noise point, cluster_id=-1) by DBSCAN."
                else:
                    pts = 0.0
                    rationale = f"Grouped into standard behavioral cluster {cid} with dense neighborhood peer group."
                contributions["clustering"] = EvidenceContribution(
                    source="clustering",
                    points=round(pts, 2),
                    max_points=round(w_clu, 2),
                    status="present",
                    observed_facts={"cluster_id": cid, "is_noise": is_noise},
                    rationale=rationale,
                )
            else:
                contributions["clustering"] = EvidenceContribution(
                    source="clustering",
                    points=0.0,
                    max_points=round(w_clu, 2),
                    status="not_observed",
                    observed_facts={},
                    rationale="Entity was not profiled by DBSCAN clustering.",
                )
        else:
            contributions["clustering"] = EvidenceContribution(
                source="clustering",
                points=0.0,
                max_points=round(w_clu, 2),
                status="data_unavailable",
                observed_facts={},
                rationale="DBSCAN clustering data unavailable.",
            )

        # --- D. Graph Topology Contribution ---
        if graph_available:
            evaluated_sources += 1
            if address in graph_features_map:
                coverage_counts["graph_topology"] += 1
                gm = graph_features_map[address]
                deg = gm.degree
                fin = gm.fan_in
                fout = gm.fan_out
                cin = gm.in_degree_centrality
                cout = gm.out_degree_centrality
                if deg >= 5 or max(cin, cout) >= 0.2:
                    pts = w_graph
                elif deg >= 2 or max(cin, cout) >= 0.1:
                    pts = 8.0 * (w_graph / 15.0)
                elif deg == 1:
                    pts = 3.0 * (w_graph / 15.0)
                else:
                    pts = 0.0
                contributions["graph_topology"] = EvidenceContribution(
                    source="graph_topology",
                    points=round(pts, 2),
                    max_points=round(w_graph, 2),
                    status="present",
                    observed_facts={"degree": deg, "fan_in": fin, "fan_out": fout, "in_centrality": cin, "out_centrality": cout},
                    rationale=f"Network connectivity degree {deg} (fan-in: {fin}, fan-out: {fout}, centrality: {cin:.4f}).",
                )
            else:
                contributions["graph_topology"] = EvidenceContribution(
                    source="graph_topology",
                    points=0.0,
                    max_points=round(w_graph, 2),
                    status="not_observed",
                    observed_facts={"degree": 0},
                    rationale="Node had zero observed topological connectivity edges in NetworkX graph.",
                )
        else:
            contributions["graph_topology"] = EvidenceContribution(
                source="graph_topology",
                points=0.0,
                max_points=round(w_graph, 2),
                status="data_unavailable",
                observed_facts={},
                rationale="Graph analysis data unavailable.",
            )

        # --- E. Activity & Telemetry Contribution ---
        if act_available:
            evaluated_sources += 1
            if address in analytics_map:
                coverage_counts["activity_volume"] += 1
                wa = analytics_map[address]
                tot_vol = wa.total_sent + wa.total_received
                has_ip = address in wallet_ips and len(wallet_ips[address]) > 0
                pts = 0.0
                if tot_vol >= 10.0:
                    pts += 7.0 * (w_act / 10.0)
                elif tot_vol >= 1.0:
                    pts += 4.0 * (w_act / 10.0)
                elif tot_vol > 0.0:
                    pts += 1.0 * (w_act / 10.0)
                if has_ip:
                    pts += 3.0 * (w_act / 10.0)
                pts = min(pts, w_act)
                contributions["activity_volume"] = EvidenceContribution(
                    source="activity_volume",
                    points=round(pts, 2),
                    max_points=round(w_act, 2),
                    status="present",
                    observed_facts={"total_volume_btc": tot_vol, "tx_count": wa.tx_count, "has_ip_telemetry": has_ip},
                    rationale=f"Observed volume {tot_vol:.4f} BTC across {wa.tx_count} tx(s) (observable IP: {has_ip}).",
                )
            else:
                contributions["activity_volume"] = EvidenceContribution(
                    source="activity_volume",
                    points=0.0,
                    max_points=round(w_act, 2),
                    status="not_observed",
                    observed_facts={"total_volume_btc": 0.0},
                    rationale="Zero financial volume recorded in analytical ledger.",
                )
        else:
            contributions["activity_volume"] = EvidenceContribution(
                source="activity_volume",
                points=0.0,
                max_points=round(w_act, 2),
                status="data_unavailable",
                observed_facts={},
                rationale="Analytics activity data unavailable.",
            )

        # Compute total score and metrics
        total_score = round(min(max(sum(c.points for c in contributions.values()), 0.0), 100.0), 1)
        priority = _assign_priority(total_score)
        confidence = round(evaluated_sources / float(len(EVIDENCE_SOURCES)), 2)

        # Extract linked evidence details
        bf_ids = [bf.detection_id for bf in behavior_findings_map.get(address, [])]
        ml_ev = ml_anomalies_map.get(address)
        clu_ev = clustering_map.get(address)
        graph_ev = graph_features_map.get(address).model_dump() if address in graph_features_map else None
        act_ev = analytics_map.get(address).model_dump() if address in analytics_map else None

        explanation = _generate_explanation(address, total_score, priority, confidence, contributions)
        risk_id = _make_risk_id(dataset_id, "wallet", address)

        findings.append(
            RiskFinding(
                risk_id=risk_id,
                dataset_id=dataset_id,
                entity_type="wallet",
                entity_id=address,
                score=total_score,
                priority=priority,
                confidence=confidence,
                evidence_contributions=contributions,
                supporting_behavior_findings=bf_ids,
                ml_evidence=ml_ev,
                graph_evidence=graph_ev,
                clustering_evidence=clu_ev,
                activity_evidence=act_ev,
                explanation=explanation,
                limitations=SYSTEM_LIMITATIONS,
                scoring_version=SCORING_VERSION,
            )
        )

    # Sort deterministically: highest score first, highest confidence second, entity_id alphabetically third
    findings.sort(key=lambda x: (-x.score, -x.confidence, x.entity_id))

    # Aggregations
    total_entities = len(findings)
    counts_by_priority = dict(Counter(f.priority for f in findings))
    for p in ("LOW", "MODERATE", "HIGH", "CRITICAL"):
        if p not in counts_by_priority:
            counts_by_priority[p] = 0

    avg_score = round(sum(f.score for f in findings) / total_entities, 1) if total_entities > 0 else 0.0
    highest_score = max((f.score for f in findings), default=0.0)

    summary = RiskSummary(
        dataset_id=dataset_id,
        total_scored_entities=total_entities,
        counts_by_priority=counts_by_priority,
        average_score=avg_score,
        highest_score=highest_score,
        evidence_coverage=coverage_counts,
        scoring_version=SCORING_VERSION,
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Persist Risk Findings to Parquet
    features_dir = config.FEATURES_DATA_DIR / dataset_id
    features_dir.mkdir(parents=True, exist_ok=True)
    parquet_file = features_dir / "risk_scores.parquet"

    if findings:
        df_risk = pl.DataFrame({
            "risk_id": [f.risk_id for f in findings],
            "dataset_id": [f.dataset_id for f in findings],
            "entity_type": [f.entity_type for f in findings],
            "entity_id": [f.entity_id for f in findings],
            "score": [f.score for f in findings],
            "priority": [f.priority for f in findings],
            "confidence": [f.confidence for f in findings],
            "explanation": [f.explanation for f in findings],
            "scoring_version": [f.scoring_version for f in findings],
        })
    else:
        df_risk = pl.DataFrame(
            schema={
                "risk_id": pl.Utf8,
                "dataset_id": pl.Utf8,
                "entity_type": pl.Utf8,
                "entity_id": pl.Utf8,
                "score": pl.Float64,
                "priority": pl.Utf8,
                "confidence": pl.Float64,
                "explanation": pl.Utf8,
                "scoring_version": pl.Utf8,
            }
        )
    df_risk.write_parquet(parquet_file)

    # 2. Persist Risk Metadata to JSON
    metadata_obj = RiskMetadata(
        dataset_id=dataset_id,
        scoring_version=SCORING_VERSION,
        weights={
            "behavioral": round(w_bhv, 2),
            "ml_anomaly": round(w_ml, 2),
            "clustering": round(w_clu, 2),
            "graph_topology": round(w_graph, 2),
            "activity_volume": round(w_act, 2),
        },
        thresholds={"priority_bands": PRIORITY_BANDS},
        score_range={"min": 0.0, "max": 100.0},
        priority_bands=PRIORITY_BANDS,
        evidence_sources=EVIDENCE_SOURCES,
        limitations=SYSTEM_LIMITATIONS,
        created_at=now_iso,
    )

    models_dir = config.MODELS_DIR / dataset_id
    models_dir.mkdir(parents=True, exist_ok=True)
    with open(models_dir / "risk_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata_obj.model_dump(), f, indent=2)

    return RiskScoringResult(
        dataset_id=dataset_id,
        summary=summary,
        findings=findings,
    )


def get_risk_summary(dataset_id: str) -> RiskSummary:
    """Retrieve risk summary for a dataset, executing scoring if not yet computed."""
    res = run_risk_scoring(dataset_id)
    return res.summary


def get_risk_findings(
    dataset_id: str,
    priority: Optional[str] = None,
    entity_type: Optional[str] = None,
    minimum_score: Optional[float] = None,
    limit: int = 50,
) -> List[RiskFinding]:
    """Retrieve filtered, ranked risk findings for a dataset."""
    res = run_risk_scoring(dataset_id)
    findings = res.findings

    if priority:
        findings = [f for f in findings if f.priority.upper() == priority.upper()]
    if entity_type:
        findings = [f for f in findings if f.entity_type.lower() == entity_type.lower()]
    if minimum_score is not None:
        findings = [f for f in findings if f.score >= minimum_score]

    return findings[:limit]


def get_risk_metadata(dataset_id: str) -> RiskMetadata:
    """Retrieve scoring configuration, weights, and limitations."""
    metadata = load_metadata(dataset_id)
    if not metadata:
        raise FileNotFoundError(f"Dataset with ID '{dataset_id}' not found.")

    meta_file = config.MODELS_DIR / dataset_id / "risk_metadata.json"
    if meta_file.is_file():
        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return RiskMetadata(**data)

    res = run_risk_scoring(dataset_id)
    return RiskMetadata(
        dataset_id=dataset_id,
        scoring_version=SCORING_VERSION,
        weights={"behavioral": 35.0, "ml_anomaly": 25.0, "clustering": 15.0, "graph_topology": 15.0, "activity_volume": 10.0},
        thresholds={"priority_bands": PRIORITY_BANDS},
        score_range={"min": 0.0, "max": 100.0},
        priority_bands=PRIORITY_BANDS,
        evidence_sources=EVIDENCE_SOURCES,
        limitations=SYSTEM_LIMITATIONS,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
