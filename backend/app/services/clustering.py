from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import polars as pl
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

from app import config
from app.models.clustering import (
    ClusteringMetadata,
    ClusterSummary,
    DBSCANClusteringResult,
    WalletClusterItem,
)
from app.services.ml_features import (
    WALLET_FEATURE_COLUMNS,
    extract_wallet_features,
    generate_and_persist_features,
)
from app.services.storage import load_metadata


def _generate_cluster_description(
    avg_sent: float,
    avg_recv: float,
    avg_deg: float,
    avg_fan_in: float,
    avg_fan_out: float,
) -> str:
    """Generate a neutral, objective forensic behavioral description for a cluster."""
    if avg_fan_in >= 2.0 and avg_fan_out <= 1.0:
        return "Inbound consolidation profile (elevated fan-in, minimal funding fan-out)."
    elif avg_fan_out >= 2.0 and avg_fan_in <= 1.0:
        return "Outbound distribution profile (elevated funding fan-out, minimal consolidation)."
    elif avg_deg >= 4.0:
        return "High-connectivity network node profile (elevated topological degree)."
    elif avg_sent > 10.0 or avg_recv > 10.0:
        return "High-volume transfer profile (notable BTC throughput)."
    elif avg_sent == 0.0 and avg_recv > 0.0:
        return "Accumulation / holding profile (funds received, zero observed spending)."
    elif avg_recv == 0.0 and avg_sent > 0.0:
        return "Originating funding profile (funds spent, zero observed incoming outputs)."
    else:
        return "Standard transactional exchange profile."


def run_dbscan_clustering(
    dataset_id: str,
    eps: float = 0.5,
    min_samples: int = 2,
) -> DBSCANClusteringResult:
    """Execute real DBSCAN behavioral clustering over dataset-isolated wallet features."""
    if eps <= 0.0:
        raise ValueError("Parameter 'eps' must be strictly greater than 0.0.")
    if min_samples < 1:
        raise ValueError("Parameter 'min_samples' must be at least 1.")

    meta = load_metadata(dataset_id)
    if not meta:
        raise FileNotFoundError(f"Dataset '{dataset_id}' not found.")

    feature_file = config.FEATURES_DATA_DIR / dataset_id / "wallet_features.parquet"
    if not feature_file.is_file():
        generate_and_persist_features(dataset_id, "wallet")

    df_wallets = pl.read_parquet(feature_file)
    now_iso = datetime.now(timezone.utc).isoformat()

    # Empty dataset handling
    if len(df_wallets) == 0:
        return DBSCANClusteringResult(
            dataset_id=dataset_id,
            entity_type="wallet",
            eps=eps,
            min_samples=min_samples,
            total_entities=0,
            cluster_count=0,
            noise_count=0,
            clustered_count=0,
            clusters=[],
            entities=[],
        )

    # Prepare feature matrix X
    X = df_wallets.select(WALLET_FEATURE_COLUMNS).to_numpy().astype(np.float64)

    # Scale features using StandardScaler for balanced distance metrics
    if len(df_wallets) > 1:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        # Fallback if any NaNs arose from zero-variance columns
        X_scaled = np.nan_to_num(X_scaled, nan=0.0)
    else:
        X_scaled = np.zeros_like(X)

    # Fit DBSCAN
    dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean", n_jobs=1)
    labels = dbscan.fit_predict(X_scaled)

    addresses = df_wallets["address"].to_list()
    cluster_ids = [int(lbl) for lbl in labels]

    # Partition clusters
    unique_cluster_ids = sorted(list(set(cluster_ids) - {-1}))
    clusters: List[ClusterSummary] = []

    for cid in unique_cluster_ids:
        indices = [idx for idx, c in enumerate(cluster_ids) if c == cid]
        sub_df = df_wallets[indices]

        avg_sent = float(sub_df["total_sent_btc"].mean()) if len(sub_df) > 0 else 0.0
        avg_recv = float(sub_df["total_received_btc"].mean()) if len(sub_df) > 0 else 0.0
        avg_deg = float(sub_df["degree"].mean()) if len(sub_df) > 0 else 0.0
        avg_fin = float(sub_df["fan_in"].mean()) if len(sub_df) > 0 else 0.0
        avg_fout = float(sub_df["fan_out"].mean()) if len(sub_df) > 0 else 0.0

        desc = _generate_cluster_description(avg_sent, avg_recv, avg_deg, avg_fin, avg_fout)
        sample_addrs = [addresses[i] for i in indices[:5]]

        clusters.append(
            ClusterSummary(
                cluster_id=cid,
                member_count=len(indices),
                sample_addresses=sample_addrs,
                avg_sent_btc=round(avg_sent, 4),
                avg_received_btc=round(avg_recv, 4),
                avg_degree=round(avg_deg, 2),
                avg_fan_in=round(avg_fin, 2),
                avg_fan_out=round(avg_fout, 2),
                description=desc,
            )
        )

    # Construct individual entity items
    entities: List[WalletClusterItem] = []
    for i in range(len(df_wallets)):
        addr = addresses[i]
        cid = cluster_ids[i]
        feat_dict = {col: float(df_wallets[col][i]) for col in WALLET_FEATURE_COLUMNS}
        entities.append(
            WalletClusterItem(
                address=addr,
                cluster_id=cid,
                is_noise=bool(cid == -1),
                features=feat_dict,
            )
        )

    noise_count = sum(1 for cid in cluster_ids if cid == -1)
    clustered_count = len(cluster_ids) - noise_count

    # 1. Persist clustered entities to Parquet
    res_df = pl.DataFrame({
        "dataset_id": [dataset_id] * len(entities),
        "address": [e.address for e in entities],
        "cluster_id": [e.cluster_id for e in entities],
        "is_noise": [e.is_noise for e in entities],
    })
    dest_dir = config.FEATURES_DATA_DIR / dataset_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    res_df.write_parquet(dest_dir / "wallet_clusters.parquet")

    # 2. Persist metadata to JSON
    metadata_obj = ClusteringMetadata(
        dataset_id=dataset_id,
        entity_type="wallet",
        model_name="scikit-learn DBSCAN",
        eps=eps,
        min_samples=min_samples,
        metric="euclidean",
        total_entities=len(entities),
        cluster_count=len(clusters),
        noise_count=noise_count,
        features_used=WALLET_FEATURE_COLUMNS,
        cluster_summaries=clusters,
        created_at=now_iso,
    )
    models_dir = config.MODELS_DIR / dataset_id
    models_dir.mkdir(parents=True, exist_ok=True)
    with open(models_dir / "dbscan_wallet_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata_obj.model_dump(), f, indent=2)

    return DBSCANClusteringResult(
        dataset_id=dataset_id,
        entity_type="wallet",
        eps=eps,
        min_samples=min_samples,
        total_entities=len(entities),
        cluster_count=len(clusters),
        noise_count=noise_count,
        clustered_count=clustered_count,
        clusters=clusters,
        entities=entities,
    )


def get_clustering_summary(dataset_id: str) -> DBSCANClusteringResult:
    """Retrieve existing clustering result or run clustering with default parameters."""
    meta_path = config.MODELS_DIR / dataset_id / "dbscan_wallet_metadata.json"
    if not meta_path.is_file():
        return run_dbscan_clustering(dataset_id)

    with open(meta_path, "r", encoding="utf-8") as f:
        meta_dict = json.load(f)

    eps = meta_dict.get("eps", 0.5)
    min_samples = meta_dict.get("min_samples", 2)
    return run_dbscan_clustering(dataset_id, eps=eps, min_samples=min_samples)


def get_clustered_entities(
    dataset_id: str,
    cluster_id: Optional[int] = None,
    noise_only: bool = False,
    limit: int = 100,
) -> List[WalletClusterItem]:
    """Retrieve clustered wallet items with optional filtering by cluster or noise flag."""
    clusters_file = config.FEATURES_DATA_DIR / dataset_id / "wallet_clusters.parquet"
    if not clusters_file.is_file():
        res = run_dbscan_clustering(dataset_id)
        items = res.entities
    else:
        # Load features and clusters together
        feature_file = config.FEATURES_DATA_DIR / dataset_id / "wallet_features.parquet"
        df_feat = pl.read_parquet(feature_file)
        df_clust = pl.read_parquet(clusters_file)

        joined = df_clust.join(df_feat, on="address")
        items = []
        for i in range(len(joined)):
            addr = joined["address"][i]
            cid = int(joined["cluster_id"][i])
            feat_dict = {col: float(joined[col][i]) for col in WALLET_FEATURE_COLUMNS}
            items.append(
                WalletClusterItem(
                    address=addr,
                    cluster_id=cid,
                    is_noise=bool(cid == -1),
                    features=feat_dict,
                )
            )

    if noise_only:
        items = [it for it in items if it.is_noise]
    elif cluster_id is not None:
        items = [it for it in items if it.cluster_id == cluster_id]

    return items[:limit]


def get_clustering_metadata(dataset_id: str) -> ClusteringMetadata:
    """Retrieve configuration, hyperparameters, and profiles for DBSCAN clustering."""
    meta_path = config.MODELS_DIR / dataset_id / "dbscan_wallet_metadata.json"
    if not meta_path.is_file():
        run_dbscan_clustering(dataset_id)

    if not meta_path.is_file():
        raise FileNotFoundError(f"Clustering metadata not found for dataset '{dataset_id}'.")

    with open(meta_path, "r", encoding="utf-8") as f:
        meta_dict = json.load(f)

    return ClusteringMetadata(**meta_dict)
