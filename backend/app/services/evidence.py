import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import polars as pl
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app import config
from app.models.evidence import (
    EvidenceArtifactInfo,
    EvidenceManifest,
    EvidencePackage,
    EvidencePackageRequest,
    EvidenceVerificationResult,
    ForensicReportRequest,
)
from app.services import (
    analytics,
    anomaly_detection,
    behavioral_detection,
    clustering,
    graph,
    graph_analysis,
    risk_scoring,
    storage,
)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas that computes dynamic total page count and adds running forensic headers/footers."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, total_pages: int) -> None:
        page_w, page_h = letter
        margin = 36  # 0.5 inch

        # Running Header (on all pages)
        self.saveState()
        self.setFont("Helvetica-Bold", 7)
        self.setFillColor(colors.HexColor("#475569"))
        self.drawString(margin, page_h - 24, "BITCOIN INTEL FORENSIC SUITE // OFFICIAL INVESTIGATIVE REPORT")
        self.setFont("Helvetica", 7)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawRightString(page_w - margin, page_h - 24, "AIR-GAPPED OFFLINE ANALYSIS")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(margin, page_h - 28, page_w - margin, page_h - 28)

        # Running Footer
        self.line(margin, 30, page_w - margin, 30)
        self.setFont("Helvetica-Bold", 7)
        self.setFillColor(colors.HexColor("#b91c1c"))
        self.drawString(margin, 20, "CONFIDENTIAL // LAW ENFORCEMENT & INVESTIGATIVE SENSITIVE")
        self.setFont("Helvetica", 7)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawRightString(page_w - margin, 20, f"Page {self._pageNumber} of {total_pages}")
        self.restoreState()

def _get_dataset_evidence_dir(dataset_id: str) -> Path:
    target_dir = config.EVIDENCE_DATA_DIR / dataset_id
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def _get_manifest_path(dataset_id: str) -> Path:
    return _get_dataset_evidence_dir(dataset_id) / "manifest.json"


def _load_manifest(dataset_id: str) -> EvidenceManifest:
    manifest_path = _get_manifest_path(dataset_id)
    if manifest_path.is_file():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return EvidenceManifest(**data)
        except Exception:
            pass
    return EvidenceManifest(
        dataset_id=dataset_id,
        updated_at=datetime.now(timezone.utc).isoformat(),
        artifacts=[],
    )


def _save_manifest(manifest: EvidenceManifest) -> None:
    manifest.updated_at = datetime.now(timezone.utc).isoformat()
    manifest_path = _get_manifest_path(manifest.dataset_id)
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))


def _compute_file_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def _gather_dataset_intelligence(dataset_id: str, sample_limit: int = 100) -> Dict[str, Any]:
    """Gather all real observed facts and analytical results from the active dataset."""
    meta = storage.load_metadata(dataset_id)
    if not meta:
        raise FileNotFoundError(f"Dataset '{dataset_id}' not found in storage.")

    raw_path = Path(meta.raw_file_path) if getattr(meta, "raw_file_path", None) else None
    file_size = raw_path.stat().st_size if raw_path and raw_path.is_file() else 0

    parquet_path = config.PROCESSED_DATA_DIR / dataset_id / "normalized.parquet"
    col_names = []
    if parquet_path.is_file():
        try:
            df_schema = pl.read_parquet_schema(parquet_path)
            col_names = list(df_schema.keys())
        except Exception:
            pass

    dataset_profile: Dict[str, Any] = {
        "dataset_id": meta.dataset_id,
        "source_file": meta.original_filename,
        "file_size_bytes": file_size,
        "total_records_ingested": meta.records_total,
        "valid_records": meta.records_valid,
        "rejected_records": meta.records_rejected,
        "ingestion_timestamp": str(meta.ingestion_timestamp),
        "column_names": col_names,
    }

    analytics_summary = None
    try:
        summary_res = analytics.get_dataset_summary(dataset_id)
        analytics_summary = summary_res.model_dump()
    except Exception:
        analytics_summary = {"status": "Not Available"}

    network_summary = None
    try:
        network_summary = analytics.get_network_analytics(dataset_id)
    except Exception:
        network_summary = {"status": "Not Available"}

    wallet_sample: List[Dict[str, Any]] = []
    try:
        wallets_res = analytics.get_wallet_analytics(dataset_id, limit=sample_limit)
        wallet_sample = [w.model_dump() for w in wallets_res]
    except Exception:
        wallet_sample = []

    transactions_sample: List[Dict[str, Any]] = []
    parquet_path = config.PROCESSED_DATA_DIR / dataset_id / "normalized.parquet"
    if parquet_path.is_file():
        try:
            df = pl.read_parquet(parquet_path)
            take_n = min(len(df), sample_limit)
            tx_subset = df.head(take_n).to_dicts()
            for row in tx_subset:
                if "timestamp" in row and hasattr(row["timestamp"], "isoformat"):
                    row["timestamp"] = row["timestamp"].isoformat()
            transactions_sample = tx_subset
        except Exception:
            transactions_sample = []

    neo4j_summary = None
    try:
        g_res = graph.get_graph_summary(dataset_id)
        neo4j_summary = g_res.model_dump()
    except Exception:
        neo4j_summary = {"status": "Not Available / Unconstructed"}

    networkx_metrics = None
    try:
        nx_res = graph_analysis.get_graph_metrics(dataset_id)
        networkx_metrics = nx_res.model_dump()
    except Exception:
        networkx_metrics = {"status": "Not Available"}

    connected_components: List[Dict[str, Any]] = []
    try:
        comp_res = graph_analysis.get_connected_components(dataset_id)
        connected_components = [c.model_dump() for c in comp_res[:10]]
    except Exception:
        connected_components = []

    anomaly_findings = None
    try:
        anom_res = anomaly_detection.get_anomalies(dataset_id, entity_type="transaction", limit=50)
        anomaly_findings = anom_res.model_dump()
    except Exception:
        anomaly_findings = {"status": "Not Available / Model Not Executed"}

    clustering_findings = None
    try:
        clust_res = clustering.get_clustering_summary(dataset_id)
        clustering_findings = clust_res.model_dump()
    except Exception:
        clustering_findings = {"status": "Not Available / Clustering Not Executed"}

    behavioral_findings: Dict[str, Any] = {"summary": None, "findings_count": 0, "top_findings": []}
    try:
        beh_sum = behavioral_detection.get_behavior_summary(dataset_id)
        beh_finds = behavioral_detection.get_behavior_findings(dataset_id, limit=50)
        behavioral_findings = {
            "summary": beh_sum.model_dump(),
            "findings_count": len(beh_finds),
            "top_findings": [f.model_dump() for f in beh_finds[:25]],
        }
    except Exception:
        behavioral_findings = {"status": "Not Available / Heuristics Not Executed"}

    risk_findings: Dict[str, Any] = {"summary": None, "findings_count": 0, "top_findings": []}
    try:
        r_sum = risk_scoring.get_risk_summary(dataset_id)
        r_finds = risk_scoring.get_risk_findings(dataset_id, limit=50)
        risk_findings = {
            "summary": r_sum.model_dump(),
            "findings_count": len(r_finds),
            "top_findings": [rf.model_dump() for rf in r_finds[:25]],
        }
    except Exception:
        risk_findings = {"status": "Not Available / Risk Scoring Not Executed"}

    return {
        "profile": dataset_profile,
        "analytics_summary": analytics_summary,
        "network_summary": network_summary,
        "wallet_sample": wallet_sample,
        "transactions_sample": transactions_sample,
        "neo4j_summary": neo4j_summary,
        "networkx_metrics": networkx_metrics,
        "connected_components": connected_components,
        "anomaly_findings": anomaly_findings,
        "clustering_findings": clustering_findings,
        "behavioral_findings": behavioral_findings,
        "risk_findings": risk_findings,
    }

def generate_evidence_package(
    dataset_id: str,
    request: Optional[EvidencePackageRequest] = None,
) -> EvidenceArtifactInfo:
    """Generate a structured, dataset-scoped JSON Evidence Package with SHA-256 cryptographic fingerprint."""
    req = request or EvidencePackageRequest()
    intel = _gather_dataset_intelligence(dataset_id, sample_limit=req.include_transactions_limit)

    now_utc = datetime.now(timezone.utc)
    timestamp_str = now_utc.strftime("%Y%m%d_%H%M%S")
    prefix = dataset_id[:8]
    artifact_id = f"ev_pkg_{prefix}_{timestamp_str}"
    filename = f"evidence_{prefix}_{timestamp_str}.json"

    package_data = EvidencePackage(
        artifact_id=artifact_id,
        dataset_id=dataset_id,
        artifact_type="evidence_package",
        generated_at=now_utc.isoformat(),
        provenance={
            "system": "Bitcoin Transaction Intelligence Platform",
            "component": "Phase 12 Evidence & Integrity Engine",
            "dataset_id": dataset_id,
            "source_filename": intel["profile"]["source_file"],
            "ingestion_timestamp": intel["profile"]["ingestion_timestamp"],
            "total_records_ingested": intel["profile"]["total_records_ingested"],
            "offline_verification": True,
        },
        forensic_classification={
            "evidentiary_purpose": "Investigative prioritization and blockchain entity correlation.",
            "legal_status": "Investigative lead intelligence only. Does NOT constitute direct proof of guilt, intent, or legal attribution.",
            "standard": "Deterministic, dataset-isolated cryptographic provenance.",
        },
        investigator_context={
            "case_reference": req.case_reference,
            "investigator_name": req.investigator_name,
            "notes": req.notes,
            "hypothesis": req.hypothesis,
        },
        observed_facts={
            "dataset_statistics": intel["analytics_summary"],
            "network_telemetry": intel["network_summary"],
            "wallets_observed": intel["wallet_sample"],
            "transactions_sample": intel["transactions_sample"],
        },
        algorithmic_findings={
            "graph_topology": {
                "neo4j": intel["neo4j_summary"],
                "networkx": intel["networkx_metrics"],
                "connected_components": intel["connected_components"],
            },
            "machine_learning_anomalies": intel["anomaly_findings"],
            "behavioral_clusters": intel["clustering_findings"],
            "behavioral_indicators": intel["behavioral_findings"],
            "risk_prioritization": intel["risk_findings"],
        },
        limitations_and_methodology=[
            "All records are strictly scoped to the ingested dataset window; external unrecorded blockchain transactions are excluded.",
            "Entity clustering relies on heuristic and machine-learning associations, not definitive identity proof.",
            "Risk scores reflect multi-signal investigative prioritization rather than legal culpability.",
            "Missing network or transaction telemetry values are preserved as null and not synthetically fabricated.",
        ],
    )

    target_dir = _get_dataset_evidence_dir(dataset_id)
    target_file = target_dir / filename
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(package_data.model_dump_json(indent=2))

    sha256 = _compute_file_sha256(target_file)
    file_size = target_file.stat().st_size

    info = EvidenceArtifactInfo(
        artifact_id=artifact_id,
        dataset_id=dataset_id,
        filename=filename,
        artifact_type="evidence_package",
        created_at=now_utc.isoformat(),
        file_size_bytes=file_size,
        sha256_hash=sha256,
        case_reference=req.case_reference,
        investigator_name=req.investigator_name,
        description=f"Dataset Evidence Package ({file_size / 1024:.1f} KB, SHA-256: {sha256[:12]}...)",
    )

    manifest = _load_manifest(dataset_id)
    manifest.artifacts.insert(0, info)
    _save_manifest(manifest)

    return info

def generate_forensic_report_pdf(
    dataset_id: str,
    request: Optional[ForensicReportRequest] = None,
) -> EvidenceArtifactInfo:
    """Generate a publication-grade, professional PDF Forensic Investigation Report using ReportLab."""
    req = request or ForensicReportRequest()
    intel = _gather_dataset_intelligence(dataset_id, sample_limit=50)

    now_utc = datetime.now(timezone.utc)
    timestamp_str = now_utc.strftime("%Y%m%d_%H%M%S")
    prefix = dataset_id[:8]
    artifact_id = f"rep_pdf_{prefix}_{timestamp_str}"
    filename = f"forensic_report_{prefix}_{timestamp_str}.pdf"

    target_dir = _get_dataset_evidence_dir(dataset_id)
    target_file = target_dir / filename

    doc = SimpleDocTemplate(
        str(target_file),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    base_styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=base_styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        textColor=colors.HexColor("#0f172a"),
        alignment=0,
        spaceAfter=3,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1e3a8a"),
        spaceAfter=2,
    )
    h1_style = ParagraphStyle(
        "SectionHeading",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=3,
    )
    body_bold = ParagraphStyle(
        "ReportBodyBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )
    mono_style = ParagraphStyle(
        "ReportMono",
        fontName="Courier",
        fontSize=6.5,
        leading=8.5,
        textColor=colors.HexColor("#0f172a"),
    )
    disclaimer_style = ParagraphStyle(
        "ReportDisclaimer",
        fontName="Helvetica-Oblique",
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor("#78350f"),
    )

    story: List[Any] = []

    # Document Header
    story.append(Paragraph("BITCOIN TRANSACTION INTELLIGENCE PLATFORM", subtitle_style))
    story.append(Paragraph("FORENSIC INVESTIGATION REPORT", title_style))

    case_ref_text = f"Case Ref: <b>{req.case_reference}</b> | " if req.case_reference else ""
    inv_text = f"Investigator: <b>{req.investigator_name}</b> | " if req.investigator_name else ""
    org_text = f"Agency: <b>{req.organization}</b> | " if req.organization else ""
    story.append(
        Paragraph(
            f"{case_ref_text}{inv_text}{org_text}Generated: <b>{now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}</b>",
            body_style,
        )
    )
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e3a8a"), spaceAfter=8))

    # SECTION 1: Legal & Forensic Attribution Disclaimer
    disclaimer_box = [
        [
            Paragraph(
                "<b>FORENSIC NOTICE & LEGAL ATTRIBUTION DISCLAIMER:</b><br/>"
                "This forensic report represents algorithmic analysis, deterministic heuristic detection, and statistical machine-learning "
                "evaluations conducted strictly on the ingested dataset records. Findings are provided as <b>investigative leads only</b>. "
                "No finding herein asserts criminal culpability, unlawful intent, ownership of pseudonymized cryptographic wallets, or "
                "definitive attribution of illicit activity as established legal fact. Independent verification is required prior to legal filings.",
                disclaimer_style,
            )
        ]
    ]
    t_disc = Table(disclaimer_box, colWidths=[540])
    t_disc.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#f59e0b")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(t_disc)
    story.append(Spacer(1, 6))

    # SECTION 2: Dataset Provenance & Profile
    story.append(Paragraph("1. DATASET PROVENANCE & IDENTIFICATION", h1_style))
    prof = intel["profile"]
    meta_rows = [
        [Paragraph("Dataset UUID:", body_bold), Paragraph(str(prof.get("dataset_id")), mono_style)],
        [Paragraph("Source File:", body_bold), Paragraph(str(prof.get("source_file")), body_style)],
        [Paragraph("Ingestion Timestamp:", body_bold), Paragraph(str(prof.get("ingestion_timestamp")), body_style)],
        [
            Paragraph("Records Ingested:", body_bold),
            Paragraph(
                f"{prof.get('total_records_ingested', 0):,} total ({prof.get('valid_records', 0):,} valid, {prof.get('rejected_records', 0):,} rejected)",
                body_style,
            ),
        ],
        [Paragraph("File Size:", body_bold), Paragraph(f"{prof.get('file_size_bytes', 0):,} bytes", body_style)],
    ]
    t_meta = Table(meta_rows, colWidths=[130, 410])
    t_meta.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ])
    )
    story.append(t_meta)
    story.append(Spacer(1, 6))

    # Investigator Context if provided
    if req.notes or req.hypothesis:
        story.append(Paragraph("2. INVESTIGATOR CONTEXT & HYPOTHESIS", h1_style))
        ctx_rows = []
        if req.hypothesis:
            ctx_rows.append([Paragraph("Investigative Hypothesis:", body_bold), Paragraph(req.hypothesis, body_style)])
        if req.notes:
            ctx_rows.append([Paragraph("Examiner Observations:", body_bold), Paragraph(req.notes, body_style)])
        t_ctx = Table(ctx_rows, colWidths=[140, 400])
        t_ctx.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        story.append(t_ctx)
        story.append(Spacer(1, 6))

    # SECTION 3: Dataset Statistics & Analytics (DuckDB)
    story.append(Paragraph("3. TRANSACTION SUMMARY & AGGREGATE METRICS", h1_style))
    sum_data = intel.get("analytics_summary", {})
    if sum_data and isinstance(sum_data, dict) and "total_transactions" in sum_data:
        vol = sum_data.get("total_volume_btc", 0.0) or 0.0
        fees = sum_data.get("total_fees_btc", 0.0) or 0.0
        stats_table = [
            [
                Paragraph("<b>Total Transactions</b>", body_style),
                Paragraph("<b>Total Volume (BTC)</b>", body_style),
                Paragraph("<b>Total Fees (BTC)</b>", body_style),
                Paragraph("<b>Unique Wallets</b>", body_style),
                Paragraph("<b>Observed IPs</b>", body_style),
            ],
            [
                Paragraph(f"{sum_data.get('total_transactions', 0):,}", body_bold),
                Paragraph(f"{vol:,.4f}", body_bold),
                Paragraph(f"{fees:,.6f}", body_bold),
                Paragraph(f"{sum_data.get('unique_wallets_count', 0):,}", body_bold),
                Paragraph(f"{sum_data.get('unique_ips_count', 0):,}", body_bold),
            ],
        ]
        t_stats = Table(stats_table, colWidths=[108, 108, 108, 108, 108])
        t_stats.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ffffff")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ])
        )
        story.append(t_stats)
    else:
        story.append(Paragraph("Analytical summary not currently compiled for this dataset.", body_style))
    story.append(Spacer(1, 6))

    # SECTION 4: Entity & Wallet Intelligence
    story.append(Paragraph("4. ENTITY & WALLET OBSERVATIONS", h1_style))
    wallets = intel.get("wallet_sample", [])
    if wallets:
        w_headers = ["Wallet Address", "Transactions", "Total Sent (BTC)", "Total Received (BTC)", "Net Flow (BTC)"]
        w_rows = [[Paragraph(f"<b>{h}</b>", body_style) for h in w_headers]]
        for w in wallets[:6]:
            addr = w.get("wallet_address", "")
            trunc_addr = f"{addr[:10]}...{addr[-8:]}" if len(addr) > 20 else addr
            sent = w.get("total_sent_btc", 0.0) or 0.0
            recv = w.get("total_received_btc", 0.0) or 0.0
            net = recv - sent
            w_rows.append([
                Paragraph(trunc_addr, mono_style),
                Paragraph(str(w.get("transaction_count", 0)), body_style),
                Paragraph(f"{sent:,.4f}", body_style),
                Paragraph(f"{recv:,.4f}", body_style),
                Paragraph(f"{net:+,.4f}", body_style),
            ])
        t_wallets = Table(w_rows, colWidths=[160, 70, 105, 105, 100])
        t_wallets.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ])
        )
        story.append(t_wallets)
    else:
        story.append(Paragraph("No individual wallet records isolated in current sample.", body_style))
    story.append(Spacer(1, 6))

    # SECTION 5: Network & Geolocation Telemetry
    story.append(Paragraph("5. NETWORK OBSERVATIONS & TELEMETRY", h1_style))
    net_data = intel.get("network_summary", {})
    if net_data and isinstance(net_data, dict) and "observations" in net_data:
        obs_list = net_data.get("observations", [])
        if obs_list:
            net_headers = ["IP Address", "Associated TXID", "ASN / ISP", "Country / Region"]
            net_rows = [[Paragraph(f"<b>{h}</b>", body_style) for h in net_headers]]
            for obs in obs_list[:5]:
                txid = obs.get("txid", "")
                trunc_tx = f"{txid[:8]}...{txid[-6:]}" if len(txid) > 16 else txid
                asn = obs.get("asn", "N/A")
                country = obs.get("country", "N/A")
                net_rows.append([
                    Paragraph(obs.get("ip_address", "N/A"), mono_style),
                    Paragraph(trunc_tx, mono_style),
                    Paragraph(str(asn), body_style),
                    Paragraph(str(country), body_style),
                ])
            t_net = Table(net_rows, colWidths=[130, 130, 140, 140])
            t_net.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ])
            )
            story.append(t_net)
        else:
            story.append(Paragraph("Network observations list is empty for this dataset.", body_style))
    else:
        story.append(Paragraph("Network telemetry not available for this dataset.", body_style))
    story.append(Spacer(1, 6))

    # SECTION 6: Graph Investigation & Topological Analysis
    story.append(Paragraph("6. GRAPH TOPOLOGY & NETWORKX METRICS", h1_style))
    neo = intel.get("neo4j_summary", {})
    nx_met = intel.get("networkx_metrics", {})
    graph_rows = [
        [
            Paragraph("Neo4j Total Nodes:", body_bold),
            Paragraph(str(neo.get("total_nodes", "N/A")), body_style),
            Paragraph("Neo4j Relationships:", body_bold),
            Paragraph(str(neo.get("total_relationships", "N/A")), body_style),
        ],
        [
            Paragraph("Network Structure:", body_bold),
            Paragraph("MultiDiGraph (Directed Multi-Edge)", body_style),
            Paragraph("Network Density:", body_bold),
            Paragraph(f"{nx_met.get('density', 0.0):.6f}" if isinstance(nx_met.get("density"), (int, float)) else "N/A", body_style),
        ],
        [
            Paragraph("Average Degree:", body_bold),
            Paragraph(f"{nx_met.get('average_degree', 0.0):.2f}" if isinstance(nx_met.get("average_degree"), (int, float)) else "N/A", body_style),
            Paragraph("Connected Components:", body_bold),
            Paragraph(str(len(intel.get("connected_components", []))), body_style),
        ],
    ]
    t_graph = Table(graph_rows, colWidths=[130, 140, 130, 140])
    t_graph.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ])
    )
    story.append(t_graph)
    story.append(Spacer(1, 6))

    # SECTION 7: Isolation Forest Machine Learning Anomaly Detection
    story.append(Paragraph("7. MACHINE LEARNING ANOMALY DETECTION (ISOLATION FOREST)", h1_style))
    anom = intel.get("anomaly_findings", {})
    if anom and isinstance(anom, dict) and "total_evaluated" in anom:
        story.append(
            Paragraph(
                f"Evaluated: <b>{anom.get('total_evaluated', 0):,}</b> entities | "
                f"Anomalies Flagged: <b>{anom.get('anomalies_detected', 0):,}</b> "
                f"({anom.get('anomaly_percentage', 0.0):.1f}%) | "
                f"Contamination: <b>{anom.get('contamination', 0.05):.2f}</b>",
                body_style,
            )
        )
        anom_list = anom.get("anomalies", [])
        if anom_list:
            anom_headers = ["Entity ID", "Type", "Score", "Percentile", "Primary Factors"]
            anom_rows = [[Paragraph(f"<b>{h}</b>", body_style) for h in anom_headers]]
            for itm in anom_list[:4]:
                eid = itm.get("entity_id", "")
                trunc_eid = f"{eid[:8]}...{eid[-6:]}" if len(eid) > 16 else eid
                expl = ", ".join(itm.get("explanation", [])[:2])
                anom_rows.append([
                    Paragraph(trunc_eid, mono_style),
                    Paragraph(str(itm.get("entity_type", "tx")), body_style),
                    Paragraph(f"{itm.get('anomaly_score', 0.0):.4f}", body_bold),
                    Paragraph(f"{itm.get('percentile', 0.0):.1f}%", body_style),
                    Paragraph(expl or "Statistical outlier", body_style),
                ])
            t_anom = Table(anom_rows, colWidths=[110, 50, 75, 75, 230])
            t_anom.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ])
            )
            story.append(t_anom)
    else:
        story.append(Paragraph("Isolation Forest model has not been executed on this dataset.", body_style))
    story.append(Spacer(1, 6))

    # SECTION 8: DBSCAN Behavioral Clustering
    story.append(Paragraph("8. BEHAVIORAL CLUSTERING (DBSCAN)", h1_style))
    clust = intel.get("clustering_findings", {})
    if clust and isinstance(clust, dict) and "total_entities" in clust:
        story.append(
            Paragraph(
                f"Clustered Entities: <b>{clust.get('total_entities', 0):,}</b> | "
                f"Clusters Formed: <b>{clust.get('total_clusters', 0):,}</b> | "
                f"Noise / Outliers (-1): <b>{clust.get('noise_count', 0):,}</b> | "
                f"Parameters: <b>eps={clust.get('eps', 0.5)}, min_samples={clust.get('min_samples', 3)}</b>",
                body_style,
            )
        )
    else:
        story.append(Paragraph("DBSCAN clustering has not been executed on this dataset.", body_style))
    story.append(Spacer(1, 6))

    # SECTION 9: Deterministic Behavioral Findings
    story.append(Paragraph("9. BEHAVIORAL PATTERN FINDINGS", h1_style))
    beh = intel.get("behavioral_findings", {})
    beh_top = beh.get("top_findings", []) if isinstance(beh, dict) else []
    if beh_top:
        b_headers = ["Pattern Type", "Subject Entity", "Confidence", "Severity", "Description"]
        b_rows = [[Paragraph(f"<b>{h}</b>", body_style) for h in b_headers]]
        for bf in beh_top[:4]:
            sid = bf.get("subject_id", "")
            trunc_s = f"{sid[:8]}...{sid[-6:]}" if len(sid) > 16 else sid
            b_rows.append([
                Paragraph(bf.get("pattern_type", ""), body_bold),
                Paragraph(trunc_s, mono_style),
                Paragraph(f"{bf.get('confidence', 0.0):.2f}", body_style),
                Paragraph(bf.get("severity", "MEDIUM"), body_style),
                Paragraph(bf.get("description", ""), body_style),
            ])
        t_beh = Table(b_rows, colWidths=[120, 110, 55, 55, 200])
        t_beh.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ])
        )
        story.append(t_beh)
    else:
        story.append(Paragraph("No behavioral findings recorded for this dataset.", body_style))
    story.append(Spacer(1, 6))

    # SECTION 10: Multi-Signal Risk Prioritization & Explainability
    story.append(Paragraph("10. MULTI-SIGNAL RISK PRIORITIZATION & EXPLAINABILITY", h1_style))
    risk_data = intel.get("risk_findings", {})
    r_sum = risk_data.get("summary", {}) if isinstance(risk_data, dict) else {}
    if r_sum and isinstance(r_sum, dict) and "scored_entities_count" in r_sum:
        bands = r_sum.get("priority_distribution", {})
        story.append(
            Paragraph(
                f"Scored Entities: <b>{r_sum.get('scored_entities_count', 0):,}</b> | "
                f"CRITICAL: <font color='#dc2626'><b>{bands.get('CRITICAL', 0)}</b></font> | "
                f"HIGH: <font color='#ea580c'><b>{bands.get('HIGH', 0)}</b></font> | "
                f"MODERATE: <font color='#d97706'><b>{bands.get('MODERATE', 0)}</b></font> | "
                f"LOW: <font color='#16a34a'><b>{bands.get('LOW', 0)}</b></font>",
                body_style,
            )
        )
        r_top = risk_data.get("top_findings", [])
        if r_top:
            r_headers = ["Entity ID", "Type", "Risk Score", "Priority", "Contributing Signals"]
            r_rows = [[Paragraph(f"<b>{h}</b>", body_style) for h in r_headers]]
            for rf in r_top[:4]:
                eid = rf.get("entity_id", "")
                trunc_e = f"{eid[:8]}...{eid[-6:]}" if len(eid) > 16 else eid
                signals = [f["rule_name"] for f in rf.get("contributing_factors", [])[:2]]
                sig_str = ", ".join(signals) if signals else "Multi-factor composite"
                r_rows.append([
                    Paragraph(trunc_e, mono_style),
                    Paragraph(str(rf.get("entity_type", "wallet")), body_style),
                    Paragraph(f"{rf.get('risk_score', 0.0):.1f}", body_bold),
                    Paragraph(rf.get("priority_band", "LOW"), body_bold),
                    Paragraph(sig_str, body_style),
                ])
            t_risk = Table(r_rows, colWidths=[120, 55, 65, 65, 235])
            t_risk.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ])
            )
            story.append(t_risk)
    else:
        story.append(Paragraph("Multi-signal risk scoring not yet computed for this dataset.", body_style))
    story.append(Spacer(1, 6))

    # SECTION 11: Cryptographic Integrity & Evidence Package Provenance
    story.append(Paragraph("11. EVIDENCE INTEGRITY & CRYPTOGRAPHIC VERIFICATION", h1_style))
    integrity_text = (
        "This report is sealed cryptographically upon generation. Each artifact generated for this dataset "
        "is stamped with a standard SHA-256 hash stored in the dataset-isolated evidence manifest. "
        "Investigators can verify the provenance of this document or exported JSON packages via the platform verification API "
        "at any point to detect unauthorized modifications, deletions, or data tampering."
    )
    story.append(Paragraph(integrity_text, body_style))
    story.append(Spacer(1, 10))

    # Sign-off block
    sign_block = [
        [
            Paragraph("<b>Report Certified By:</b>", body_style),
            Paragraph(f"{req.investigator_name or 'Forensic System Operator'}", body_style),
        ],
        [
            Paragraph("<b>Forensic Tool Engine:</b>", body_style),
            Paragraph("Bitcoin Transaction Intelligence Forensic Suite v1.0 (Phase 12)", body_style),
        ],
        [
            Paragraph("<b>Operating Mode:</b>", body_style),
            Paragraph("Air-Gapped Offline / Zero-Cloud / Deterministic Pipeline", body_style),
        ],
    ]
    t_sign = Table(sign_block, colWidths=[150, 390])
    t_sign.setStyle(
        TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 1, colors.HexColor("#1e3a8a")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    story.append(t_sign)

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)

    sha256 = _compute_file_sha256(target_file)
    file_size = target_file.stat().st_size

    info = EvidenceArtifactInfo(
        artifact_id=artifact_id,
        dataset_id=dataset_id,
        filename=filename,
        artifact_type="forensic_report_pdf",
        created_at=now_utc.isoformat(),
        file_size_bytes=file_size,
        sha256_hash=sha256,
        case_reference=req.case_reference,
        investigator_name=req.investigator_name,
        description=f"Forensic Investigation PDF Report ({file_size / 1024:.1f} KB, SHA-256: {sha256[:12]}...)",
    )

    manifest = _load_manifest(dataset_id)
    manifest.artifacts.insert(0, info)
    _save_manifest(manifest)

    return info


def verify_artifact_integrity(dataset_id: str, artifact_id: str) -> EvidenceVerificationResult:
    """Recompute SHA-256 of artifact on disk and compare with the recorded manifest fingerprint."""
    manifest = _load_manifest(dataset_id)
    artifact = next((a for a in manifest.artifacts if a.artifact_id == artifact_id), None)
    if not artifact:
        raise FileNotFoundError(f"Artifact '{artifact_id}' not recorded in dataset '{dataset_id}' manifest.")

    file_path = _get_dataset_evidence_dir(dataset_id) / artifact.filename
    now_str = datetime.now(timezone.utc).isoformat()

    if not file_path.is_file():
        return EvidenceVerificationResult(
            artifact_id=artifact_id,
            filename=artifact.filename,
            dataset_id=dataset_id,
            is_valid=False,
            status="missing",
            expected_sha256=artifact.sha256_hash,
            computed_sha256=None,
            verified_at=now_str,
            message="CRITICAL INTEGRITY FAILURE: Evidence file is missing from disk storage.",
        )

    computed = _compute_file_sha256(file_path)
    if computed == artifact.sha256_hash:
        return EvidenceVerificationResult(
            artifact_id=artifact_id,
            filename=artifact.filename,
            dataset_id=dataset_id,
            is_valid=True,
            status="verified",
            expected_sha256=artifact.sha256_hash,
            computed_sha256=computed,
            verified_at=now_str,
            message="VERIFIED: Cryptographic SHA-256 fingerprint matches manifest record perfectly. File is untampered.",
        )
    else:
        return EvidenceVerificationResult(
            artifact_id=artifact_id,
            filename=artifact.filename,
            dataset_id=dataset_id,
            is_valid=False,
            status="tampered",
            expected_sha256=artifact.sha256_hash,
            computed_sha256=computed,
            verified_at=now_str,
            message="TAMPER ALERT: Recomputed SHA-256 hash does not match the manifest fingerprint. File has been modified or corrupted.",
        )


def list_dataset_artifacts(dataset_id: str) -> List[EvidenceArtifactInfo]:
    """Retrieve all generated evidence artifacts for a specific dataset."""
    manifest = _load_manifest(dataset_id)
    return manifest.artifacts


def get_artifact_file(dataset_id: str, artifact_id: str) -> Tuple[Path, str, str]:
    """Locate file path, filename, and media type for export / download."""
    manifest = _load_manifest(dataset_id)
    artifact = next((a for a in manifest.artifacts if a.artifact_id == artifact_id), None)
    if not artifact:
        raise FileNotFoundError(f"Artifact '{artifact_id}' not found in dataset '{dataset_id}'.")

    file_path = _get_dataset_evidence_dir(dataset_id) / artifact.filename
    if not file_path.is_file():
        raise FileNotFoundError(f"Artifact file '{artifact.filename}' missing from disk.")

    if artifact.artifact_type == "forensic_report_pdf":
        media_type = "application/pdf"
    else:
        media_type = "application/json"

    return file_path, artifact.filename, media_type
