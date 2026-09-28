import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import polars as pl

from app import config
from app.models.anomaly import FeatureGenerationResponse
from app.services.graph_analysis import load_dataset_networkx_graph
from app.services.storage import load_metadata


# List of numerical feature columns used for transaction anomaly detection
TRANSACTION_FEATURE_COLUMNS = [
    "input_count",
    "output_count",
    "total_input_amount",
    "total_output_amount",
    "amount_transferred",
    "fee",
    "has_fee",
    "fee_ratio",
    "max_input_amount",
    "max_output_amount",
    "avg_output_amount",
    "has_ip",
    "has_country",
    "has_asn",
    "network_peer_degree",
    "max_wallet_degree",
    "max_wallet_fan_in",
    "max_wallet_fan_out",
]

# List of numerical feature columns used for wallet anomaly detection
WALLET_FEATURE_COLUMNS = [
    "tx_count",
    "total_sent_btc",
    "total_received_btc",
    "net_flow_btc",
    "avg_sent_amount",
    "avg_received_amount",
    "max_sent_amount",
    "max_received_amount",
    "degree",
    "fan_in",
    "fan_out",
    "in_degree_centrality",
    "out_degree_centrality",
    "has_network_telemetry",
]

IMPUTED_FIELDS_DOCUMENTATION: Dict[str, str] = {
    "fee": "Imputed missing fee as 0.0; tracked by 'has_fee' binary indicator column.",
    "fee_ratio": "Computed as fee / total_output_amount; defaults to 0.0 when fee or output is missing/zero.",
    "input_amounts": "Missing input amounts sum to 0.0; tracked by 'total_input_amount'.",
    "output_amounts": "Missing output amounts sum to 0.0; tracked by 'total_output_amount'.",
    "network_peer_degree": "Defaults to 0.0 when IP network telemetry is absent from the record.",
    "max_wallet_degree": "Defaults to 0.0 when graph node degrees are unobserved.",
    "max_wallet_fan_in": "Defaults to 0.0 when incoming funding flows are unobserved.",
    "max_wallet_fan_out": "Defaults to 0.0 when outgoing spending flows are unobserved.",
}


def extract_transaction_features(dataset_id: str) -> Tuple[pl.DataFrame, List[str], Dict[str, str]]:
    """Extract tabular numerical features for each transaction in the dataset."""
    metadata = load_metadata(dataset_id)
    if not metadata:
        raise FileNotFoundError(f"Dataset '{dataset_id}' not found.")

    parquet_path = config.PROCESSED_DATA_DIR / dataset_id / "normalized.parquet"
    if not parquet_path.is_file():
        if metadata.records_valid == 0:
            empty_schema = {"dataset_id": pl.Utf8, "txid": pl.Utf8}
            for col in TRANSACTION_FEATURE_COLUMNS:
                empty_schema[col] = pl.Float64
            return pl.DataFrame(schema=empty_schema), TRANSACTION_FEATURE_COLUMNS, IMPUTED_FIELDS_DOCUMENTATION
        raise FileNotFoundError(f"Normalized Parquet file missing for dataset '{dataset_id}'.")

    df_norm = pl.read_parquet(parquet_path)
    if len(df_norm) == 0:
        empty_schema = {"dataset_id": pl.Utf8, "txid": pl.Utf8}
        for col in TRANSACTION_FEATURE_COLUMNS:
            empty_schema[col] = pl.Float64
        return pl.DataFrame(schema=empty_schema), TRANSACTION_FEATURE_COLUMNS, IMPUTED_FIELDS_DOCUMENTATION

    # Load in-memory graph for topological features
    try:
        G = load_dataset_networkx_graph(dataset_id)
    except Exception:
        G = None

    rows = df_norm.to_dicts()
    feature_records = []

    for row in rows:
        txid = row.get("txid") or f"unlabeled_tx_{len(feature_records)}"
        in_addrs = row.get("input_addresses") or []
        in_amts = [float(a) for a in (row.get("input_amounts") or []) if a is not None]
        out_addrs = row.get("output_addresses") or []
        out_amts = [float(a) for a in (row.get("output_amounts") or []) if a is not None]

        input_count = float(len(in_addrs))
        output_count = float(len(out_addrs))
        total_in = float(sum(in_amts)) if in_amts else 0.0
        total_out = float(sum(out_amts)) if out_amts else 0.0
        amount_transferred = total_out

        raw_fee = row.get("fee")
        has_fee = 1.0 if raw_fee is not None else 0.0
        fee = float(raw_fee) if raw_fee is not None else 0.0
        fee_ratio = (fee / total_out) if (has_fee > 0 and total_out > 0) else 0.0

        max_in = float(max(in_amts)) if in_amts else 0.0
        max_out = float(max(out_amts)) if out_amts else 0.0
        avg_out = (total_out / len(out_amts)) if out_amts else 0.0

        src_ip = row.get("src_ip")
        dst_ip = row.get("dst_ip")
        has_ip = 1.0 if (src_ip or dst_ip) else 0.0
        has_country = 1.0 if row.get("geo_country") else 0.0
        has_asn = 1.0 if row.get("asn") is not None else 0.0

        # Graph-derived features
        peer_deg = 0.0
        max_w_deg = 0.0
        max_w_fan_in = 0.0
        max_w_fan_out = 0.0

        if G is not None:
            # IP peer degree
            if src_ip:
                ip_uid = f"{dataset_id}:{src_ip}"
                if ip_uid in G:
                    peer_deg = float(G.degree(ip_uid))

            # Wallet degrees and flows
            all_wallets = in_addrs + out_addrs
            for addr in all_wallets:
                w_uid = f"{dataset_id}:{addr}"
                if w_uid in G:
                    w_deg = float(G.degree(w_uid))
                    if w_deg > max_w_deg:
                        max_w_deg = w_deg

                    # Fan-in and Fan-out
                    in_edges = G.in_edges(w_uid, data=True)
                    f_in = sum(1.0 for _, _, d in in_edges if d.get("type") == "HAS_OUTPUT")
                    f_out = sum(1.0 for _, _, d in in_edges if d.get("type") == "HAS_INPUT")
                    if f_in > max_w_fan_in:
                        max_w_fan_in = f_in
                    if f_out > max_w_fan_out:
                        max_w_fan_out = f_out

        rec = {
            "dataset_id": dataset_id,
            "txid": txid,
            "input_count": input_count,
            "output_count": output_count,
            "total_input_amount": total_in,
            "total_output_amount": total_out,
            "amount_transferred": amount_transferred,
            "fee": fee,
            "has_fee": has_fee,
            "fee_ratio": fee_ratio,
            "max_input_amount": max_in,
            "max_output_amount": max_out,
            "avg_output_amount": avg_out,
            "has_ip": has_ip,
            "has_country": has_country,
            "has_asn": has_asn,
            "network_peer_degree": peer_deg,
            "max_wallet_degree": max_w_deg,
            "max_wallet_fan_in": max_w_fan_in,
            "max_wallet_fan_out": max_w_fan_out,
        }
        feature_records.append(rec)

    df_features = pl.DataFrame(feature_records)
    return df_features, TRANSACTION_FEATURE_COLUMNS, IMPUTED_FIELDS_DOCUMENTATION


def extract_wallet_features(dataset_id: str) -> Tuple[pl.DataFrame, List[str], Dict[str, str]]:
    """Extract tabular numerical features for each wallet address in the dataset."""
    metadata = load_metadata(dataset_id)
    if not metadata:
        raise FileNotFoundError(f"Dataset '{dataset_id}' not found.")

    parquet_path = config.PROCESSED_DATA_DIR / dataset_id / "normalized.parquet"
    if not parquet_path.is_file():
        if metadata.records_valid == 0:
            empty_schema = {"dataset_id": pl.Utf8, "address": pl.Utf8}
            for col in WALLET_FEATURE_COLUMNS:
                empty_schema[col] = pl.Float64
            return pl.DataFrame(schema=empty_schema), WALLET_FEATURE_COLUMNS, IMPUTED_FIELDS_DOCUMENTATION
        raise FileNotFoundError(f"Normalized Parquet file missing for dataset '{dataset_id}'.")

    df_norm = pl.read_parquet(parquet_path)
    if len(df_norm) == 0:
        empty_schema = {"dataset_id": pl.Utf8, "address": pl.Utf8}
        for col in WALLET_FEATURE_COLUMNS:
            empty_schema[col] = pl.Float64
        return pl.DataFrame(schema=empty_schema), WALLET_FEATURE_COLUMNS, IMPUTED_FIELDS_DOCUMENTATION

    try:
        G = load_dataset_networkx_graph(dataset_id)
    except Exception:
        G = None

    wallet_stats: Dict[str, Dict[str, Any]] = {}
    rows = df_norm.to_dicts()

    for row in rows:
        in_addrs = row.get("input_addresses") or []
        in_amts = [float(a) for a in (row.get("input_amounts") or []) if a is not None]
        out_addrs = row.get("output_addresses") or []
        out_amts = [float(a) for a in (row.get("output_amounts") or []) if a is not None]
        has_ip = 1.0 if (row.get("src_ip") or row.get("dst_ip")) else 0.0

        for i, addr in enumerate(in_addrs):
            if not addr:
                continue
            amt = in_amts[i] if i < len(in_amts) else 0.0
            if addr not in wallet_stats:
                wallet_stats[addr] = {
                    "tx_ids": set(),
                    "sent_amounts": [],
                    "recv_amounts": [],
                    "has_telemetry": 0.0,
                }
            if row.get("txid"):
                wallet_stats[addr]["tx_ids"].add(row["txid"])
            wallet_stats[addr]["sent_amounts"].append(amt)
            if has_ip > 0:
                wallet_stats[addr]["has_telemetry"] = 1.0

        for i, addr in enumerate(out_addrs):
            if not addr:
                continue
            amt = out_amts[i] if i < len(out_amts) else 0.0
            if addr not in wallet_stats:
                wallet_stats[addr] = {
                    "tx_ids": set(),
                    "sent_amounts": [],
                    "recv_amounts": [],
                    "has_telemetry": 0.0,
                }
            if row.get("txid"):
                wallet_stats[addr]["tx_ids"].add(row["txid"])
            wallet_stats[addr]["recv_amounts"].append(amt)
            if has_ip > 0:
                wallet_stats[addr]["has_telemetry"] = 1.0

    if not wallet_stats:
        empty_schema = {"dataset_id": pl.Utf8, "address": pl.Utf8}
        for col in WALLET_FEATURE_COLUMNS:
            empty_schema[col] = pl.Float64
        return pl.DataFrame(schema=empty_schema), WALLET_FEATURE_COLUMNS, IMPUTED_FIELDS_DOCUMENTATION

    # Centralities from graph if available
    in_centrality = {}
    out_centrality = {}
    if G is not None:
        import networkx as nx
        try:
            in_centrality = nx.in_degree_centrality(G)
            out_centrality = nx.out_degree_centrality(G)
        except Exception:
            pass

    records = []
    for addr, stats in wallet_stats.items():
        w_uid = f"{dataset_id}:{addr}"
        sent_amts = stats["sent_amounts"]
        recv_amts = stats["recv_amounts"]

        total_sent = float(sum(sent_amts))
        total_recv = float(sum(recv_amts))
        net_flow = total_recv - total_sent

        avg_sent = (total_sent / len(sent_amts)) if sent_amts else 0.0
        avg_recv = (total_recv / len(recv_amts)) if recv_amts else 0.0
        max_sent = float(max(sent_amts)) if sent_amts else 0.0
        max_recv = float(max(recv_amts)) if recv_amts else 0.0

        # Graph metrics
        deg = 0.0
        fan_in = 0.0
        fan_out = 0.0
        in_c = 0.0
        out_c = 0.0

        if G is not None and w_uid in G:
            deg = float(G.degree(w_uid))
            in_edges = G.in_edges(w_uid, data=True)
            fan_in = float(sum(1 for _, _, d in in_edges if d.get("type") == "HAS_OUTPUT"))
            fan_out = float(sum(1 for _, _, d in in_edges if d.get("type") == "HAS_INPUT"))
            in_c = float(in_centrality.get(w_uid, 0.0))
            out_c = float(out_centrality.get(w_uid, 0.0))

        records.append({
            "dataset_id": dataset_id,
            "address": addr,
            "tx_count": float(len(stats["tx_ids"])),
            "total_sent_btc": total_sent,
            "total_received_btc": total_recv,
            "net_flow_btc": net_flow,
            "avg_sent_amount": avg_sent,
            "avg_received_amount": avg_recv,
            "max_sent_amount": max_sent,
            "max_received_amount": max_recv,
            "degree": deg,
            "fan_in": fan_in,
            "fan_out": fan_out,
            "in_degree_centrality": in_c,
            "out_degree_centrality": out_c,
            "has_network_telemetry": stats["has_telemetry"],
        })

    df_wallet_features = pl.DataFrame(records)
    return df_wallet_features, WALLET_FEATURE_COLUMNS, IMPUTED_FIELDS_DOCUMENTATION


def generate_and_persist_features(
    dataset_id: str,
    entity_type: str = "transaction",
) -> FeatureGenerationResponse:
    """Extract and persist features to data/features/{dataset_id}/{entity_type}_features.parquet."""
    if entity_type == "wallet":
        df_features, feature_names, imputed_docs = extract_wallet_features(dataset_id)
    else:
        df_features, feature_names, imputed_docs = extract_transaction_features(dataset_id)

    dest_dir = config.FEATURES_DATA_DIR / dataset_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / f"{entity_type}_features.parquet"
    df_features.write_parquet(out_path)

    return FeatureGenerationResponse(
        dataset_id=dataset_id,
        entity_type=entity_type,
        feature_count=len(feature_names),
        feature_names=feature_names,
        record_count=len(df_features),
        imputed_fields=imputed_docs,
        feature_file_path=str(out_path),
    )
