from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx
import polars as pl

from app import config
from app.models.behavior import (
    BehaviorSummary,
    BehavioralDetectionRequest,
    BehavioralDetectionResult,
    BehavioralFinding,
    BehavioralMetadata,
    DetectorSummary,
)
from app.services.storage import load_metadata


DETECTOR_VERSION = "1.0.0"

FEATURE_DEFINITIONS: Dict[str, str] = {
    "fan_in": "Identifies wallets receiving funding from multiple distinct input addresses across transactions.",
    "fan_out": "Identifies wallets distributing funds to multiple distinct output destinations across transactions.",
    "rapid_dispersion": "Detects transactions or sequences disbursing funds to multiple destinations within a short observed time window.",
    "transaction_burst": "Identifies high-density clusters of transactions for an entity within a sliding time window.",
    "dormant_to_active": "Detects entities with prolonged inactivity followed by renewed transaction activity over sufficient historical time spans.",
    "multi_hop_movement": "Identifies directed multi-hop transaction flow paths between wallets via intermediate transactions.",
    "peeling_chain_like": "Identifies sequential transaction chains with asymmetric split outputs and continuation change addresses.",
}

SYSTEM_LIMITATIONS: List[str] = [
    "Behavioral indicators are investigative leads and do NOT prove criminal activity, intentional obfuscation, or entity attribution.",
    "Off-chain data, lighting network channels, CoinJoin collaboration, and batch payouts may exhibit identical behavioral topologies.",
    "Analysis is strictly scoped to the observed records within the specific dataset and lacks global blockchain visibility.",
    "Temporal indicators depend strictly on recorded timestamps, which may exhibit block timestamp variance (up to 2 hours).",
]


def _make_detection_id(dataset_id: str, detection_type: str, entity_id: str, suffix: str = "") -> str:
    """Generate a deterministic finding identifier."""
    raw = f"{dataset_id}:{detection_type}:{entity_id}:{suffix}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()
    return f"BHV-{digest}"


def _parse_iso_timestamp(ts_str: Optional[str]) -> Optional[float]:
    """Parse ISO-8601 timestamp string into UTC unix epoch seconds."""
    if not ts_str:
        return None
    try:
        clean_ts = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_ts)
        return dt.timestamp()
    except Exception:
        return None


def _load_dataset_df(dataset_id: str) -> pl.DataFrame:
    """Load normalized parquet file for a dataset, validating existence."""
    metadata = load_metadata(dataset_id)
    if not metadata:
        raise FileNotFoundError(f"Dataset with ID '{dataset_id}' not found.")
    
    parquet_path = config.PROCESSED_DATA_DIR / dataset_id / "normalized.parquet"
    if not parquet_path.is_file():
        if getattr(metadata, "records_valid", None) == 0:
            return pl.DataFrame(
                schema={
                    "dataset_id": pl.Utf8,
                    "timestamp": pl.Utf8,
                    "src_ip": pl.Utf8,
                    "dst_ip": pl.Utf8,
                    "src_port": pl.Int64,
                    "dst_port": pl.Int64,
                    "txid": pl.Utf8,
                    "input_addresses": pl.List(pl.Utf8),
                    "output_addresses": pl.List(pl.Utf8),
                    "input_amounts": pl.List(pl.Float64),
                    "output_amounts": pl.List(pl.Float64),
                    "fee": pl.Float64,
                    "script_type": pl.Utf8,
                    "geo_country": pl.Utf8,
                    "asn": pl.Int64,
                }
            )
        raise FileNotFoundError(f"Normalized parquet file not found for dataset '{dataset_id}'.")
    
    return pl.read_parquet(parquet_path)


# ==============================================================================
# Detector 1: Fan-In Indicator
# ==============================================================================
def detect_fan_in(
    df: pl.DataFrame, dataset_id: str, min_sources: int = 2
) -> Tuple[List[BehavioralFinding], DetectorSummary]:
    """Detect wallets receiving funds from multiple distinct input sources."""
    if len(df) == 0:
        return [], DetectorSummary(
            detector_name="fan_in",
            status="insufficient_data",
            findings_count=0,
            message="Dataset contains 0 records.",
        )

    # Aggregate incoming sources per recipient wallet
    wallet_sources: Dict[str, Set[str]] = {}
    wallet_txids: Dict[str, Set[str]] = {}
    wallet_ips: Dict[str, Set[str]] = {}
    wallet_amounts: Dict[str, float] = {}
    wallet_timestamps: Dict[str, List[str]] = {}

    for row in df.to_dicts():
        txid = row.get("txid") or "unspecified_txid"
        ts = row.get("timestamp")
        src_ip = row.get("src_ip")
        inputs = [a for a in (row.get("input_addresses") or []) if a]
        outputs = row.get("output_addresses") or []
        output_amts = row.get("output_amounts") or []

        for idx, out_addr in enumerate(outputs):
            if not out_addr:
                continue
            if out_addr not in wallet_sources:
                wallet_sources[out_addr] = set()
                wallet_txids[out_addr] = set()
                wallet_ips[out_addr] = set()
                wallet_amounts[out_addr] = 0.0
                wallet_timestamps[out_addr] = []

            # Add input addresses that are distinct from the recipient
            for in_addr in inputs:
                if in_addr != out_addr:
                    wallet_sources[out_addr].add(in_addr)

            wallet_txids[out_addr].add(txid)
            if src_ip:
                wallet_ips[out_addr].add(src_ip)
            if idx < len(output_amts) and output_amts[idx] is not None:
                wallet_amounts[out_addr] += float(output_amts[idx])
            if ts:
                wallet_timestamps[out_addr].append(ts)

    findings: List[BehavioralFinding] = []
    for address in sorted(wallet_sources.keys()):
        sources = sorted(list(wallet_sources[address]))
        source_count = len(sources)
        if source_count >= min_sources:
            txids = sorted(list(wallet_txids[address]))
            ips = sorted(list(wallet_ips[address]))
            total_amt = round(wallet_amounts[address], 8)
            timestamps = sorted(wallet_timestamps[address])
            first_seen = timestamps[0] if timestamps else None
            last_seen = timestamps[-1] if timestamps else None

            det_id = _make_detection_id(dataset_id, "fan_in", address, str(source_count))
            severity = "medium" if source_count >= 5 else "low"
            confidence = 0.9 if total_amt > 0 else 0.8

            explanation = (
                f"Observed {source_count} distinct input source addresses funding wallet {address} "
                f"across {len(txids)} transaction(s) (totaling {total_amt:.4f} BTC). "
                f"This matches the fan-in indicator threshold of >={min_sources} distinct sources."
            )
            limitations = [
                "Multi-input funding may represent wallet consolidation, payment processor aggregation, or CoinJoin participation.",
                "Indicator demonstrates incoming flow concentration only; does not infer common control or illicit origin.",
            ]

            findings.append(
                BehavioralFinding(
                    detection_id=det_id,
                    dataset_id=dataset_id,
                    detection_type="fan_in",
                    entity_type="wallet",
                    entity_id=address,
                    severity_indicator=severity,
                    confidence=confidence,
                    observed_facts={
                        "distinct_source_count": source_count,
                        "source_addresses": sources[:10],
                        "related_transaction_count": len(txids),
                        "total_received_btc": total_amt,
                    },
                    supporting_transaction_ids=txids,
                    supporting_ips=ips,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    parameters={"min_sources": min_sources},
                    explanation=explanation,
                    limitations=limitations,
                )
            )

    return findings, DetectorSummary(
        detector_name="fan_in",
        status="completed",
        findings_count=len(findings),
        message=f"Evaluated {len(wallet_sources)} recipient wallets.",
    )


# ==============================================================================
# Detector 2: Fan-Out Indicator
# ==============================================================================
def detect_fan_out(
    df: pl.DataFrame, dataset_id: str, min_destinations: int = 2
) -> Tuple[List[BehavioralFinding], DetectorSummary]:
    """Detect wallets sending funds toward multiple distinct output destinations."""
    if len(df) == 0:
        return [], DetectorSummary(
            detector_name="fan_out",
            status="insufficient_data",
            findings_count=0,
            message="Dataset contains 0 records.",
        )

    wallet_destinations: Dict[str, Set[str]] = {}
    wallet_txids: Dict[str, Set[str]] = {}
    wallet_ips: Dict[str, Set[str]] = {}
    wallet_amounts: Dict[str, float] = {}
    wallet_timestamps: Dict[str, List[str]] = {}

    for row in df.to_dicts():
        txid = row.get("txid") or "unspecified_txid"
        ts = row.get("timestamp")
        src_ip = row.get("src_ip")
        inputs = [a for a in (row.get("input_addresses") or []) if a]
        input_amts = row.get("input_amounts") or []
        outputs = [a for a in (row.get("output_addresses") or []) if a]

        for idx, in_addr in enumerate(inputs):
            if not in_addr:
                continue
            if in_addr not in wallet_destinations:
                wallet_destinations[in_addr] = set()
                wallet_txids[in_addr] = set()
                wallet_ips[in_addr] = set()
                wallet_amounts[in_addr] = 0.0
                wallet_timestamps[in_addr] = []

            for out_addr in outputs:
                if out_addr != in_addr:
                    wallet_destinations[in_addr].add(out_addr)

            wallet_txids[in_addr].add(txid)
            if src_ip:
                wallet_ips[in_addr].add(src_ip)
            if idx < len(input_amts) and input_amts[idx] is not None:
                wallet_amounts[in_addr] += float(input_amts[idx])
            if ts:
                wallet_timestamps[in_addr].append(ts)

    findings: List[BehavioralFinding] = []
    for address in sorted(wallet_destinations.keys()):
        dests = sorted(list(wallet_destinations[address]))
        dest_count = len(dests)
        if dest_count >= min_destinations:
            txids = sorted(list(wallet_txids[address]))
            ips = sorted(list(wallet_ips[address]))
            total_amt = round(wallet_amounts[address], 8)
            timestamps = sorted(wallet_timestamps[address])
            first_seen = timestamps[0] if timestamps else None
            last_seen = timestamps[-1] if timestamps else None

            det_id = _make_detection_id(dataset_id, "fan_out", address, str(dest_count))
            severity = "medium" if dest_count >= 5 else "low"
            confidence = 0.9 if total_amt > 0 else 0.8

            explanation = (
                f"Observed wallet {address} distributing funds toward {dest_count} distinct output destinations "
                f"across {len(txids)} transaction(s) (observed input total: {total_amt:.4f} BTC). "
                f"This meets the fan-out indicator threshold of >={min_destinations} destinations."
            )
            limitations = [
                "Multi-destination disbursements commonly occur in exchange customer withdrawals, merchant batching, and payroll.",
                "Indicator denotes distribution fan-out structure only; no malicious dispersion or money laundering is asserted.",
            ]

            findings.append(
                BehavioralFinding(
                    detection_id=det_id,
                    dataset_id=dataset_id,
                    detection_type="fan_out",
                    entity_type="wallet",
                    entity_id=address,
                    severity_indicator=severity,
                    confidence=confidence,
                    observed_facts={
                        "distinct_destination_count": dest_count,
                        "destination_addresses": dests[:10],
                        "related_transaction_count": len(txids),
                        "total_sent_btc": total_amt,
                    },
                    supporting_transaction_ids=txids,
                    supporting_ips=ips,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    parameters={"min_destinations": min_destinations},
                    explanation=explanation,
                    limitations=limitations,
                )
            )

    return findings, DetectorSummary(
        detector_name="fan_out",
        status="completed",
        findings_count=len(findings),
        message=f"Evaluated {len(wallet_destinations)} sender wallets.",
    )


# ==============================================================================
# Detector 3: Rapid Dispersion Indicator
# ==============================================================================
def detect_rapid_dispersion(
    df: pl.DataFrame,
    dataset_id: str,
    time_window_seconds: int = 1800,
    min_destinations: int = 2,
) -> Tuple[List[BehavioralFinding], DetectorSummary]:
    """Detect transactions where funds are distributed to multiple destinations within a short observed time window."""
    if len(df) == 0:
        return [], DetectorSummary(
            detector_name="rapid_dispersion",
            status="insufficient_data",
            findings_count=0,
            message="Dataset contains 0 records.",
        )

    findings: List[BehavioralFinding] = []
    missing_timestamp_count = 0

    # 1. Single-transaction batch dispersion (elapsed time = 0s)
    for idx, row in enumerate(df.to_dicts()):
        ts_str = row.get("timestamp")
        if not ts_str:
            missing_timestamp_count += 1
            continue

        txid = row.get("txid") or f"tx_idx_{idx}"
        outputs = [a for a in (row.get("output_addresses") or []) if a]
        distinct_dests = sorted(list(set(outputs)))
        dest_count = len(distinct_dests)

        if dest_count >= min_destinations:
            src_ip = row.get("src_ip")
            ips = [src_ip] if src_ip else []
            out_amts = row.get("output_amounts") or []
            total_out = round(sum(float(a) for a in out_amts if a is not None), 8)

            det_id = _make_detection_id(dataset_id, "rapid_dispersion", txid, str(dest_count))
            explanation = (
                f"Observed transaction {txid} rapidly dispersing funds across {dest_count} distinct output destinations "
                f"in a single transaction event at {ts_str} (threshold: >={min_destinations} destinations within {time_window_seconds}s)."
            )
            limitations = [
                "Single-transaction multi-output disbursements are common in exchange hot wallets, pool payouts, and UTXO splitting.",
                "Timing is bounded by recorded block/telemetry timestamps.",
            ]

            findings.append(
                BehavioralFinding(
                    detection_id=det_id,
                    dataset_id=dataset_id,
                    detection_type="rapid_dispersion",
                    entity_type="transaction",
                    entity_id=txid,
                    severity_indicator="medium" if dest_count >= 5 else "low",
                    confidence=0.85,
                    observed_facts={
                        "destination_count": dest_count,
                        "destination_addresses": distinct_dests[:10],
                        "window_seconds": 0,
                        "threshold_seconds": time_window_seconds,
                        "total_disbursed_btc": total_out,
                    },
                    supporting_transaction_ids=[txid],
                    supporting_ips=ips,
                    first_seen=ts_str,
                    last_seen=ts_str,
                    parameters={
                        "time_window_seconds": time_window_seconds,
                        "min_destinations": min_destinations,
                    },
                    explanation=explanation,
                    limitations=limitations,
                )
            )

    msg = f"Evaluated {len(df)} transactions."
    if missing_timestamp_count > 0:
        msg += f" {missing_timestamp_count} records lacked timestamps and were skipped for temporal analysis."

    return findings, DetectorSummary(
        detector_name="rapid_dispersion",
        status="completed",
        findings_count=len(findings),
        message=msg,
    )


# ==============================================================================
# Detector 4: Transaction Burst Indicator
# ==============================================================================
def detect_transaction_burst(
    df: pl.DataFrame,
    dataset_id: str,
    burst_window_seconds: int = 3600,
    burst_min_tx_count: int = 3,
) -> Tuple[List[BehavioralFinding], DetectorSummary]:
    """Detect unusually dense transaction activity for the same wallet or IP within a configurable time window."""
    if len(df) == 0:
        return [], DetectorSummary(
            detector_name="transaction_burst",
            status="insufficient_data",
            findings_count=0,
            message="Dataset contains 0 records.",
        )

    # Collect timestamped events per entity (wallet and IP)
    entity_events: Dict[Tuple[str, str], List[Tuple[float, str, str, Optional[str]]]] = {}

    for idx, row in enumerate(df.to_dicts()):
        ts_str = row.get("timestamp")
        epoch_ts = _parse_iso_timestamp(ts_str)
        if epoch_ts is None or not ts_str:
            continue

        txid = row.get("txid") or f"tx_idx_{idx}"
        src_ip = row.get("src_ip")
        inputs = [a for a in (row.get("input_addresses") or []) if a]
        outputs = [a for a in (row.get("output_addresses") or []) if a]

        # Register wallet entities
        for w in set(inputs + outputs):
            key = ("wallet", w)
            if key not in entity_events:
                entity_events[key] = []
            entity_events[key].append((epoch_ts, ts_str, txid, src_ip))

        # Register IP entity
        if src_ip:
            key = ("ip", src_ip)
            if key not in entity_events:
                entity_events[key] = []
            entity_events[key].append((epoch_ts, ts_str, txid, src_ip))

    findings: List[BehavioralFinding] = []

    for (ent_type, ent_id), events in sorted(entity_events.items()):
        if len(events) < burst_min_tx_count:
            continue

        # Sort events by timestamp
        events.sort(key=lambda x: x[0])

        # Sliding window search for bursts
        best_burst: Optional[Tuple[int, int, List[Tuple[float, str, str, Optional[str]]]]] = None
        n = len(events)
        i = 0
        while i < n:
            j = i
            while j < n and (events[j][0] - events[i][0]) <= burst_window_seconds:
                j += 1
            count = j - i
            if count >= burst_min_tx_count:
                if best_burst is None or count > best_burst[0]:
                    best_burst = (count, i, events[i:j])
            i += 1

        if best_burst:
            count, start_idx, burst_events = best_burst
            elapsed = int(burst_events[-1][0] - burst_events[0][0])
            txids = sorted(list(set(e[2] for e in burst_events)))
            ips = sorted(list(set(e[3] for e in burst_events if e[3])))
            first_seen = burst_events[0][1]
            last_seen = burst_events[-1][1]

            det_id = _make_detection_id(dataset_id, "transaction_burst", ent_id, str(count))
            severity = "high" if count >= (burst_min_tx_count * 2) else "medium"

            explanation = (
                f"Observed burst of {count} transactions for {ent_type} '{ent_id}' within an elapsed duration "
                f"of {elapsed}s (threshold: >={burst_min_tx_count} txs within {burst_window_seconds}s window)."
            )
            limitations = [
                "Automated services, algorithmic trading agents, and mining pools exhibit high transaction frequencies under normal conditions.",
                "Indicator identifies temporal clustering only; no illicit activity is implied.",
            ]

            findings.append(
                BehavioralFinding(
                    detection_id=det_id,
                    dataset_id=dataset_id,
                    detection_type="transaction_burst",
                    entity_type=ent_type,
                    entity_id=ent_id,
                    severity_indicator=severity,
                    confidence=0.85,
                    observed_facts={
                        "burst_transaction_count": count,
                        "elapsed_seconds": elapsed,
                        "threshold_seconds": burst_window_seconds,
                        "threshold_tx_count": burst_min_tx_count,
                    },
                    supporting_transaction_ids=txids,
                    supporting_ips=ips,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    parameters={
                        "burst_window_seconds": burst_window_seconds,
                        "burst_min_tx_count": burst_min_tx_count,
                    },
                    explanation=explanation,
                    limitations=limitations,
                )
            )

    return findings, DetectorSummary(
        detector_name="transaction_burst",
        status="completed",
        findings_count=len(findings),
        message=f"Analyzed activity across {len(entity_events)} distinct entities.",
    )


# ==============================================================================
# Detector 5: Dormant-to-Active Indicator
# ==============================================================================
def detect_dormant_to_active(
    df: pl.DataFrame,
    dataset_id: str,
    dormancy_threshold_seconds: int = 86400 * 30,
) -> Tuple[List[BehavioralFinding], DetectorSummary]:
    """Detect entities with a prolonged inactivity period followed by renewed transaction activity."""
    if len(df) == 0:
        return [], DetectorSummary(
            detector_name="dormant_to_active",
            status="insufficient_data",
            findings_count=0,
            message="Dataset contains 0 records.",
        )

    # Collect valid timestamps across dataset
    all_timestamps: List[Tuple[float, str]] = []
    wallet_timestamps: Dict[str, List[Tuple[float, str, str, Optional[str]]]] = {}

    for idx, row in enumerate(df.to_dicts()):
        ts_str = row.get("timestamp")
        epoch_ts = _parse_iso_timestamp(ts_str)
        if epoch_ts is None or not ts_str:
            continue

        all_timestamps.append((epoch_ts, ts_str))
        txid = row.get("txid") or f"tx_idx_{idx}"
        src_ip = row.get("src_ip")
        inputs = [a for a in (row.get("input_addresses") or []) if a]
        outputs = [a for a in (row.get("output_addresses") or []) if a]

        for w in set(inputs + outputs):
            if w not in wallet_timestamps:
                wallet_timestamps[w] = []
            wallet_timestamps[w].append((epoch_ts, ts_str, txid, src_ip))

    if len(all_timestamps) < 2:
        return [], DetectorSummary(
            detector_name="dormant_to_active",
            status="insufficient_temporal_history",
            findings_count=0,
            message="Dataset contains fewer than 2 valid timestamped records; temporal dormancy cannot be determined.",
        )

    all_timestamps.sort(key=lambda x: x[0])
    total_span_seconds = all_timestamps[-1][0] - all_timestamps[0][0]

    # Explicit insufficient temporal history check
    if total_span_seconds < dormancy_threshold_seconds:
        span_days = round(total_span_seconds / 86400.0, 2)
        thresh_days = round(dormancy_threshold_seconds / 86400.0, 1)
        return [], DetectorSummary(
            detector_name="dormant_to_active",
            status="insufficient_temporal_history",
            findings_count=0,
            message=(
                f"Dataset observation span ({int(total_span_seconds)}s / {span_days} days) is less than "
                f"the required dormancy threshold ({dormancy_threshold_seconds}s / {thresh_days} days); "
                f"dormant-to-active evaluation requires broader longitudinal history."
            ),
        )

    findings: List[BehavioralFinding] = []
    for address, events in sorted(wallet_timestamps.items()):
        if len(events) < 2:
            continue

        events.sort(key=lambda x: x[0])
        for k in range(len(events) - 1):
            t1, ts1_str, txid1, ip1 = events[k]
            t2, ts2_str, txid2, ip2 = events[k + 1]
            gap = t2 - t1

            if gap >= dormancy_threshold_seconds:
                gap_days = round(gap / 86400.0, 1)
                thresh_days = round(dormancy_threshold_seconds / 86400.0, 1)
                det_id = _make_detection_id(dataset_id, "dormant_to_active", address, str(int(gap)))
                txids = sorted(list(set([txid1, txid2])))
                ips = sorted(list(set([ip for ip in (ip1, ip2) if ip])))

                explanation = (
                    f"Observed wallet {address} become active on {ts2_str} after a dormant period of {gap_days} days "
                    f"following prior activity on {ts1_str} (threshold: >={thresh_days} days)."
                )
                limitations = [
                    "Long-term cold storage retention and hodling are standard personal custody behaviors in Bitcoin.",
                    "Dormancy indicates inactive intervals only; no illicit dormancy or reactivation purpose is asserted.",
                ]

                findings.append(
                    BehavioralFinding(
                        detection_id=det_id,
                        dataset_id=dataset_id,
                        detection_type="dormant_to_active",
                        entity_type="wallet",
                        entity_id=address,
                        severity_indicator="low",
                        confidence=0.8,
                        observed_facts={
                            "dormant_duration_seconds": int(gap),
                            "dormant_days": gap_days,
                            "prior_activity_timestamp": ts1_str,
                            "reactivation_timestamp": ts2_str,
                            "threshold_days": thresh_days,
                        },
                        supporting_transaction_ids=txids,
                        supporting_ips=ips,
                        first_seen=ts1_str,
                        last_seen=ts2_str,
                        parameters={"dormancy_threshold_seconds": dormancy_threshold_seconds},
                        explanation=explanation,
                        limitations=limitations,
                    )
                )

    return findings, DetectorSummary(
        detector_name="dormant_to_active",
        status="completed",
        findings_count=len(findings),
        message=f"Evaluated {len(wallet_timestamps)} wallets over {round(total_span_seconds / 86400, 1)} days of observation.",
    )


# ==============================================================================
# Detector 6: Multi-Hop Movement Indicator
# ==============================================================================
def detect_multi_hop_movement(
    df: pl.DataFrame,
    dataset_id: str,
    min_hops: int = 2,
    max_hops: int = 4,
) -> Tuple[List[BehavioralFinding], DetectorSummary]:
    """Use directed wallet-to-wallet transfer graph to identify short multi-hop transaction paths."""
    if len(df) == 0:
        return [], DetectorSummary(
            detector_name="multi_hop_movement",
            status="insufficient_data",
            findings_count=0,
            message="Dataset contains 0 records.",
        )

    # Build directed wallet transfer graph: W_in -> W_out via txid
    G = nx.DiGraph()
    tx_lookup: Dict[Tuple[str, str], Set[str]] = {}

    for idx, row in enumerate(df.to_dicts()):
        txid = row.get("txid") or f"tx_idx_{idx}"
        inputs = [a for a in (row.get("input_addresses") or []) if a]
        outputs = [a for a in (row.get("output_addresses") or []) if a]

        for u in inputs:
            for v in outputs:
                if u != v:
                    G.add_edge(u, v)
                    pair = (u, v)
                    if pair not in tx_lookup:
                        tx_lookup[pair] = set()
                    tx_lookup[pair].add(txid)

    findings: List[BehavioralFinding] = []
    seen_paths: Set[Tuple[str, ...]] = set()

    for src in sorted(G.nodes()):
        # Simple paths up to max_hops from this source
        for dst in sorted(G.nodes()):
            if src == dst:
                continue
            try:
                for path in nx.all_simple_paths(G, source=src, target=dst, cutoff=max_hops):
                    hop_count = len(path) - 1
                    if hop_count < min_hops:
                        continue

                    path_tuple = tuple(path)
                    if path_tuple in seen_paths:
                        continue
                    seen_paths.add(path_tuple)

                    # Gather transaction IDs along the path edges
                    path_txids: List[str] = []
                    for i in range(len(path) - 1):
                        u, v = path[i], path[i + 1]
                        txs = sorted(list(tx_lookup.get((u, v), set())))
                        path_txids.extend(txs)
                    path_txids = sorted(list(set(path_txids)))

                    det_id = _make_detection_id(
                        dataset_id, "multi_hop_movement", f"{src}->{dst}", str(hop_count)
                    )
                    intermediates = path[1:-1]
                    explanation = (
                        f"Identified directed {hop_count}-hop movement path from wallet {src} to {dst} "
                        f"through {len(intermediates)} intermediate wallet(s) across transaction(s) "
                        f"({', '.join(path_txids[:5])}). This represents an indirect fund transfer path."
                    )
                    limitations = [
                        "Graph path connectivity does not demonstrate continuous fund ownership or intentional layering.",
                        "Intermediate addresses may belong to third-party payment services, exchanges, or independent counterparties.",
                    ]

                    findings.append(
                        BehavioralFinding(
                            detection_id=det_id,
                            dataset_id=dataset_id,
                            detection_type="multi_hop_movement",
                            entity_type="wallet",
                            entity_id=src,
                            severity_indicator="low",
                            confidence=0.85,
                            observed_facts={
                                "source_wallet": src,
                                "destination_wallet": dst,
                                "hop_count": hop_count,
                                "path_addresses": path,
                                "intermediate_wallets": intermediates,
                            },
                            supporting_transaction_ids=path_txids,
                            supporting_ips=[],
                            first_seen=None,
                            last_seen=None,
                            parameters={"min_hops": min_hops, "max_hops": max_hops},
                            explanation=explanation,
                            limitations=limitations,
                        )
                    )
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue

    return findings, DetectorSummary(
        detector_name="multi_hop_movement",
        status="completed",
        findings_count=len(findings),
        message=f"Evaluated transfer graph containing {G.number_of_nodes()} wallet nodes and {G.number_of_edges()} transfer edges.",
    )


# ==============================================================================
# Detector 7: Peeling-Chain-Like Structure Indicator
# ==============================================================================
def detect_peeling_chains(
    df: pl.DataFrame,
    dataset_id: str,
    min_peel_length: int = 2,
) -> Tuple[List[BehavioralFinding], DetectorSummary]:
    """Detect graph/transaction structures that resemble repeated transfer patterns with a continuing output."""
    if len(df) == 0:
        return [], DetectorSummary(
            detector_name="peeling_chain_like",
            status="insufficient_data",
            findings_count=0,
            message="Dataset contains 0 records.",
        )

    # Build index of transactions having 2 outputs (peeled payment + change continuation)
    # Map input address -> list of (txid, row)
    addr_to_spending_txs: Dict[str, List[Dict[str, Any]]] = {}
    tx_by_id: Dict[str, Dict[str, Any]] = {}

    for idx, row in enumerate(df.to_dicts()):
        txid = row.get("txid") or f"tx_idx_{idx}"
        row["_resolved_txid"] = txid
        tx_by_id[txid] = row
        inputs = [a for a in (row.get("input_addresses") or []) if a]
        for in_addr in inputs:
            if in_addr not in addr_to_spending_txs:
                addr_to_spending_txs[in_addr] = []
            addr_to_spending_txs[in_addr].append(row)

    findings: List[BehavioralFinding] = []
    visited_in_chains: Set[str] = set()

    for txid, row in sorted(tx_by_id.items()):
        if txid in visited_in_chains:
            continue

        outputs = [a for a in (row.get("output_addresses") or []) if a]
        out_amts = [float(a) for a in (row.get("output_amounts") or []) if a is not None]

        # Peeling candidate transactions typically have exactly 2 outputs
        if len(outputs) != 2:
            continue

        # Try building a chain forward from both outputs
        for out_idx, candidate_continuation in enumerate(outputs):
            current_txid = txid
            chain_txids = [current_txid]
            continuation_addrs = [candidate_continuation]
            curr_addr = candidate_continuation

            while True:
                # Find subsequent transaction spending curr_addr
                next_candidates = addr_to_spending_txs.get(curr_addr, [])
                # Filter to transactions with 2 outputs that haven't looped
                valid_next = None
                for nxt in next_candidates:
                    nxt_id = nxt["_resolved_txid"]
                    nxt_outs = [a for a in (nxt.get("output_addresses") or []) if a]
                    if nxt_id not in chain_txids and len(nxt_outs) == 2:
                        valid_next = nxt
                        break

                if not valid_next:
                    break

                nxt_id = valid_next["_resolved_txid"]
                chain_txids.append(nxt_id)
                nxt_outs = [a for a in (valid_next.get("output_addresses") or []) if a]
                # Pick continuation output (e.g. the one that spends into another tx or larger amount)
                # If neither spends forward, take first output
                next_continuation = nxt_outs[0]
                for o in nxt_outs:
                    if o in addr_to_spending_txs and o not in continuation_addrs:
                        next_continuation = o
                        break

                continuation_addrs.append(next_continuation)
                curr_addr = next_continuation

            if len(chain_txids) >= min_peel_length:
                for c_id in chain_txids:
                    visited_in_chains.add(c_id)

                det_id = _make_detection_id(
                    dataset_id, "peeling_chain_like", chain_txids[0], str(len(chain_txids))
                )
                explanation = (
                    f"Observed peeling-chain-like behavioral pattern spanning {len(chain_txids)} sequential transactions "
                    f"({', '.join(chain_txids)}), where an output is sequentially spent into subsequent 2-output transactions."
                )
                limitations = [
                    "Merchant change handling, automated payment processors, and repeated personal payments frequently generate peeling-chain-like structures.",
                    "Pattern indicates structural topological similarity only; do NOT classify as mixer, ransomware, or laundering activity.",
                ]

                findings.append(
                    BehavioralFinding(
                        detection_id=det_id,
                        dataset_id=dataset_id,
                        detection_type="peeling_chain_like",
                        entity_type="transaction",
                        entity_id=chain_txids[0],
                        severity_indicator="medium",
                        confidence=0.85,
                        observed_facts={
                            "chain_length": len(chain_txids),
                            "transaction_sequence": chain_txids,
                            "continuation_addresses": continuation_addrs,
                        },
                        supporting_transaction_ids=chain_txids,
                        supporting_ips=[],
                        first_seen=row.get("timestamp"),
                        last_seen=None,
                        parameters={"min_peel_length": min_peel_length},
                        explanation=explanation,
                        limitations=limitations,
                    )
                )
                break

    return findings, DetectorSummary(
        detector_name="peeling_chain_like",
        status="completed",
        findings_count=len(findings),
        message=f"Evaluated 2-output sequential transfer structures across {len(tx_by_id)} transactions.",
    )


# ==============================================================================
# Pipeline Coordinator & Persistence
# ==============================================================================
def run_behavioral_detection(
    dataset_id: str, request: Optional[BehavioralDetectionRequest] = None
) -> BehavioralDetectionResult:
    """Execute all 7 behavioral detectors on the dataset, persist outputs, and return results."""
    req = request or BehavioralDetectionRequest()
    df = _load_dataset_df(dataset_id)

    all_findings: List[BehavioralFinding] = []
    detector_summaries: List[DetectorSummary] = []

    # 1. Fan-In
    f_in, s_in = detect_fan_in(df, dataset_id, min_sources=req.min_fan_in_sources)
    all_findings.extend(f_in)
    detector_summaries.append(s_in)

    # 2. Fan-Out
    f_out, s_out = detect_fan_out(df, dataset_id, min_destinations=req.min_fan_out_destinations)
    all_findings.extend(f_out)
    detector_summaries.append(s_out)

    # 3. Rapid Dispersion
    f_disp, s_disp = detect_rapid_dispersion(
        df,
        dataset_id,
        time_window_seconds=req.rapid_dispersion_window_seconds,
        min_destinations=req.rapid_dispersion_min_destinations,
    )
    all_findings.extend(f_disp)
    detector_summaries.append(s_disp)

    # 4. Transaction Burst
    f_burst, s_burst = detect_transaction_burst(
        df,
        dataset_id,
        burst_window_seconds=req.burst_window_seconds,
        burst_min_tx_count=req.burst_min_tx_count,
    )
    all_findings.extend(f_burst)
    detector_summaries.append(s_burst)

    # 5. Dormant-to-Active
    f_dorm, s_dorm = detect_dormant_to_active(
        df,
        dataset_id,
        dormancy_threshold_seconds=req.dormancy_threshold_seconds,
    )
    all_findings.extend(f_dorm)
    detector_summaries.append(s_dorm)

    # 6. Multi-Hop Movement
    f_hop, s_hop = detect_multi_hop_movement(
        df,
        dataset_id,
        min_hops=req.min_multi_hop_depth,
        max_hops=req.max_multi_hop_depth,
    )
    all_findings.extend(f_hop)
    detector_summaries.append(s_hop)

    # 7. Peeling-Chain-Like Structure
    f_peel, s_peel = detect_peeling_chains(
        df,
        dataset_id,
        min_peel_length=req.min_peel_length,
    )
    all_findings.extend(f_peel)
    detector_summaries.append(s_peel)

    # Deterministic sorting
    all_findings.sort(key=lambda x: (x.detection_type, x.entity_type, x.entity_id, x.detection_id))

    # Aggregations
    by_type = dict(Counter(f.detection_type for f in all_findings))
    by_sev = dict(Counter(f.severity_indicator for f in all_findings))
    flagged_entities = len(set(f.entity_id for f in all_findings))

    summary = BehaviorSummary(
        dataset_id=dataset_id,
        total_findings=len(all_findings),
        findings_by_type=by_type,
        findings_by_severity=by_sev,
        entities_flagged_count=flagged_entities,
        detector_summaries=detector_summaries,
    )

    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Persist findings to Parquet
    features_dir = config.FEATURES_DATA_DIR / dataset_id
    features_dir.mkdir(parents=True, exist_ok=True)
    parquet_file = features_dir / "behavioral_findings.parquet"

    if all_findings:
        findings_df = pl.DataFrame({
            "detection_id": [f.detection_id for f in all_findings],
            "dataset_id": [f.dataset_id for f in all_findings],
            "detection_type": [f.detection_type for f in all_findings],
            "entity_type": [f.entity_type for f in all_findings],
            "entity_id": [f.entity_id for f in all_findings],
            "severity_indicator": [f.severity_indicator for f in all_findings],
            "confidence": [f.confidence for f in all_findings],
            "explanation": [f.explanation for f in all_findings],
            "first_seen": [f.first_seen for f in all_findings],
            "last_seen": [f.last_seen for f in all_findings],
        })
    else:
        findings_df = pl.DataFrame(
            schema={
                "detection_id": pl.Utf8,
                "dataset_id": pl.Utf8,
                "detection_type": pl.Utf8,
                "entity_type": pl.Utf8,
                "entity_id": pl.Utf8,
                "severity_indicator": pl.Utf8,
                "confidence": pl.Float64,
                "explanation": pl.Utf8,
                "first_seen": pl.Utf8,
                "last_seen": pl.Utf8,
            }
        )
    findings_df.write_parquet(parquet_file)

    # 2. Persist metadata to JSON
    metadata = BehavioralMetadata(
        dataset_id=dataset_id,
        detector_version=DETECTOR_VERSION,
        enabled_detectors=[
            "fan_in",
            "fan_out",
            "rapid_dispersion",
            "transaction_burst",
            "dormant_to_active",
            "multi_hop_movement",
            "peeling_chain_like",
        ],
        configurable_thresholds=req.model_dump(),
        feature_definitions=FEATURE_DEFINITIONS,
        limitations=SYSTEM_LIMITATIONS,
        created_at=now_iso,
    )

    models_dir = config.MODELS_DIR / dataset_id
    models_dir.mkdir(parents=True, exist_ok=True)
    with open(models_dir / "behavioral_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata.model_dump(), f, indent=2)

    return BehavioralDetectionResult(
        dataset_id=dataset_id,
        summary=summary,
        findings=all_findings,
    )


def get_behavior_summary(dataset_id: str) -> BehaviorSummary:
    """Retrieve behavioral summary for a dataset, running detection if not yet performed."""
    # Ensure dataset exists
    _load_dataset_df(dataset_id)
    res = run_behavioral_detection(dataset_id)
    return res.summary


def get_behavior_findings(
    dataset_id: str,
    detection_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    minimum_confidence: Optional[float] = None,
    limit: int = 50,
) -> List[BehavioralFinding]:
    """Retrieve filtered behavioral findings for a dataset."""
    res = run_behavioral_detection(dataset_id)
    findings = res.findings

    if detection_type:
        findings = [f for f in findings if f.detection_type == detection_type]
    if entity_type:
        findings = [f for f in findings if f.entity_type == entity_type]
    if minimum_confidence is not None:
        findings = [f for f in findings if f.confidence >= minimum_confidence]

    return findings[:limit]


def get_behavior_metadata(dataset_id: str) -> BehavioralMetadata:
    """Retrieve behavioral detector configuration and metadata."""
    metadata = load_metadata(dataset_id)
    if not metadata:
        raise FileNotFoundError(f"Dataset with ID '{dataset_id}' not found.")

    meta_file = config.MODELS_DIR / dataset_id / "behavioral_metadata.json"
    if meta_file.is_file():
        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return BehavioralMetadata(**data)

    res = run_behavioral_detection(dataset_id)
    return BehavioralMetadata(
        dataset_id=dataset_id,
        detector_version=DETECTOR_VERSION,
        enabled_detectors=[
            "fan_in",
            "fan_out",
            "rapid_dispersion",
            "transaction_burst",
            "dormant_to_active",
            "multi_hop_movement",
            "peeling_chain_like",
        ],
        configurable_thresholds=BehavioralDetectionRequest().model_dump(),
        feature_definitions=FEATURE_DEFINITIONS,
        limitations=SYSTEM_LIMITATIONS,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
