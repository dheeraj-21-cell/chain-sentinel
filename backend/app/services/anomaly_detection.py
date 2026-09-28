from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import numpy as np
import polars as pl
from sklearn.ensemble import IsolationForest

from app import config
from app.models.anomaly import (
    AnomalyDetectionResult,
    AnomalyScoreItem,
    ModelMetadata,
)
from app.services.ml_features import (
    IMPUTED_FIELDS_DOCUMENTATION,
    TRANSACTION_FEATURE_COLUMNS,
    WALLET_FEATURE_COLUMNS,
    generate_and_persist_features,
)
from app.services.storage import load_metadata

MODEL_NAME = "scikit-learn IsolationForest"
MODEL_VERSION = "1.0.0"


def _generate_explanations(
    feature_dict: Dict[str, float],
    medians: Dict[str, float],
    stds: Dict[str, float],
    entity_type: str,
) -> List[str]:
    """Generate neutral forensic explanations for feature values deviating from the dataset distribution."""
    reasons = []

    if entity_type == "transaction":
        amt = feature_dict.get("amount_transferred", 0.0)
        med_amt = medians.get("amount_transferred", 0.0)
        if amt > 0 and (amt > med_amt * 2.0 or (stds.get("amount_transferred", 0.0) > 0 and amt > med_amt + stds.get("amount_transferred", 0.0))):
            reasons.append(f"Transfer volume ({amt:.4f} BTC) deviates notably above dataset median ({med_amt:.4f} BTC).")

        fee = feature_dict.get("fee", 0.0)
        med_fee = medians.get("fee", 0.0)
        if fee > 0 and fee > med_fee * 2.0:
            reasons.append(f"Recorded transaction fee ({fee:.6f} BTC) is elevated relative to dataset median ({med_fee:.6f} BTC).")

        in_cnt = feature_dict.get("input_count", 0.0)
        med_in = medians.get("input_count", 0.0)
        if in_cnt > 3 and in_cnt > med_in:
            reasons.append(f"Transaction aggregates multiple inputs ({int(in_cnt)} distinct UTXO sources).")

        out_cnt = feature_dict.get("output_count", 0.0)
        med_out = medians.get("output_count", 0.0)
        if out_cnt > 3 and out_cnt > med_out:
            reasons.append(f"Transaction fans out to multiple outputs ({int(out_cnt)} distinct destinations).")

        deg = feature_dict.get("max_wallet_degree", 0.0)
        if deg > 5:
            reasons.append(f"Involves a high-connectivity graph wallet node (degree {int(deg)}).")

        if feature_dict.get("has_ip", 0.0) > 0 and feature_dict.get("network_peer_degree", 0.0) > 2:
            reasons.append(f"Associated network peer has elevated connection density (degree {int(feature_dict['network_peer_degree'])}).")

    else:  # wallet
        sent = feature_dict.get("total_sent_btc", 0.0)
        recv = feature_dict.get("total_received_btc", 0.0)
        med_sent = medians.get("total_sent_btc", 0.0)
        med_recv = medians.get("total_received_btc", 0.0)

        if sent > med_sent * 2.0 and sent > 0:
            reasons.append(f"Total sent volume ({sent:.4f} BTC) is elevated above wallet median ({med_sent:.4f} BTC).")
        if recv > med_recv * 2.0 and recv > 0:
            reasons.append(f"Total received volume ({recv:.4f} BTC) is elevated above wallet median ({med_recv:.4f} BTC).")

        fan_out = feature_dict.get("fan_out", 0.0)
        if fan_out > 3:
            reasons.append(f"Wallet exhibits notable fan-out flow ({int(fan_out)} transactions funded).")

        fan_in = feature_dict.get("fan_in", 0.0)
        if fan_in > 3:
            reasons.append(f"Wallet exhibits notable fan-in consolidation ({int(fan_in)} payments received).")

        deg = feature_dict.get("degree", 0.0)
        if deg > 5:
            reasons.append(f"High-degree topological node (degree {int(deg)}).")

    if not reasons:
        reasons.append("Multi-dimensional feature combination deviates from the central empirical cluster.")

    return reasons


def train_isolation_forest(
    dataset_id: str,
    entity_type: str = "transaction",
    contamination: float = 0.1,
    n_estimators: int = 100,
    random_state: int = 42,
) -> AnomalyDetectionResult:
    """Train scikit-learn IsolationForest on genuine dataset features and persist model and predictions."""
    meta = load_metadata(dataset_id)
    if not meta:
        raise FileNotFoundError(f"Dataset '{dataset_id}' not found.")

    # 1. Load or extract features
    feature_file = config.FEATURES_DATA_DIR / dataset_id / f"{entity_type}_features.parquet"
    if not feature_file.is_file():
        generate_and_persist_features(dataset_id, entity_type)

    df_features = pl.read_parquet(feature_file)
    feature_columns = TRANSACTION_FEATURE_COLUMNS if entity_type == "transaction" else WALLET_FEATURE_COLUMNS
    id_column = "txid" if entity_type == "transaction" else "address"

    now_iso = datetime.now(timezone.utc).isoformat()

    # Empty dataset handling
    if len(df_features) == 0:
        return AnomalyDetectionResult(
            dataset_id=dataset_id,
            entity_type=entity_type,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            timestamp=now_iso,
            total_entities=0,
            anomaly_count=0,
            contamination=contamination,
            random_state=random_state,
            anomalies=[],
        )

    # 2. Extract feature matrix X
    X = df_features.select(feature_columns).to_numpy()

    # Calculate column medians and stds for neutral explainability
    medians = {col: float(np.median(df_features[col].to_numpy())) for col in feature_columns}
    stds = {col: float(np.std(df_features[col].to_numpy())) for col in feature_columns}

    # 3. Fit Isolation Forest
    # If single sample, fitting IsolationForest produces trivial output; handle deterministically
    if len(df_features) == 1:
        raw_scores = np.array([0.0])
        labels = np.array([1])
        norm_scores = np.array([0.5])
    else:
        # Constrain contamination to valid range
        actual_contam = min(max(contamination, 0.001), 0.5)
        model = IsolationForest(
            n_estimators=n_estimators,
            contamination=actual_contam,
            random_state=random_state,
            n_jobs=1,
        )
        model.fit(X)
        raw_scores = model.decision_function(X)
        labels = model.predict(X)

        # Normalize score to [0.0, 1.0]:
        # raw_score < 0 is anomaly (maps to > 0.5)
        # raw_score > 0 is normal (maps to < 0.5)
        norm_scores = np.clip(0.5 - (raw_scores * 0.5), 0.0, 1.0)

        # 4. Persist model artifact
        model_dir = config.MODELS_DIR / dataset_id
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / f"isolation_forest_{entity_type}.joblib"
        joblib.dump(model, model_path)

        # 5. Persist model metadata
        metadata_obj = ModelMetadata(
            dataset_id=dataset_id,
            entity_type=entity_type,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            n_estimators=n_estimators,
            contamination=actual_contam,
            random_state=random_state,
            feature_names=feature_columns,
            imputed_fields=IMPUTED_FIELDS_DOCUMENTATION,
            training_samples=len(df_features),
            anomaly_samples=int(np.sum(labels == -1)),
            model_path=str(model_path),
            created_at=now_iso,
        )
        meta_file = model_dir / f"metadata_{entity_type}.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata_obj.model_dump(), f, indent=2)

    # 6. Build structured results
    id_list = df_features[id_column].to_list()
    items: List[AnomalyScoreItem] = []

    for i in range(len(df_features)):
        entity_id = str(id_list[i])
        lbl = int(labels[i])
        raw_s = float(raw_scores[i])
        norm_s = float(norm_scores[i])
        is_anom = bool(lbl == -1)

        row_feat = {col: float(df_features[col][i]) for col in feature_columns}
        expl = _generate_explanations(row_feat, medians, stds, entity_type) if is_anom else []

        items.append(
            AnomalyScoreItem(
                entity_id=entity_id,
                entity_type=entity_type,
                anomaly_label=lbl,
                is_anomaly=is_anom,
                raw_score=round(raw_s, 6),
                anomaly_score=round(norm_s, 4),
                features=row_feat,
                explanation=expl,
            )
        )

    # Sort descending by anomaly score (most anomalous investigative leads first)
    items.sort(key=lambda x: x.anomaly_score, reverse=True)

    # 7. Persist anomaly scoring table to Parquet
    df_results = pl.DataFrame({
        "dataset_id": [dataset_id] * len(items),
        "entity_id": [item.entity_id for item in items],
        "entity_type": [item.entity_type for item in items],
        "anomaly_label": [item.anomaly_label for item in items],
        "is_anomaly": [item.is_anomaly for item in items],
        "raw_score": [item.raw_score for item in items],
        "anomaly_score": [item.anomaly_score for item in items],
    })
    res_dest = config.FEATURES_DATA_DIR / dataset_id / f"{entity_type}_anomalies.parquet"
    df_results.write_parquet(res_dest)

    return AnomalyDetectionResult(
        dataset_id=dataset_id,
        entity_type=entity_type,
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        timestamp=now_iso,
        total_entities=len(items),
        anomaly_count=sum(1 for it in items if it.is_anomaly),
        contamination=contamination,
        random_state=random_state,
        anomalies=items,
    )


def get_anomalies(
    dataset_id: str,
    entity_type: str = "transaction",
    limit: int = 100,
    anomalies_only: bool = False,
) -> AnomalyDetectionResult:
    """Retrieve anomaly detection results for a dataset, training model on demand if not present."""
    anom_file = config.FEATURES_DATA_DIR / dataset_id / f"{entity_type}_anomalies.parquet"
    if not anom_file.is_file():
        # Train on-demand
        result = train_isolation_forest(dataset_id=dataset_id, entity_type=entity_type)
    else:
        # Load from disk and reconstruct full response
        meta_file = config.MODELS_DIR / dataset_id / f"metadata_{entity_type}.json"
        if meta_file.is_file():
            with open(meta_file, "r", encoding="utf-8") as f:
                meta_dict = json.load(f)
            contam = meta_dict.get("contamination", 0.1)
            r_state = meta_dict.get("random_state", 42)
            ts = meta_dict.get("created_at", datetime.now(timezone.utc).isoformat())
        else:
            contam = 0.1
            r_state = 42
            ts = datetime.now(timezone.utc).isoformat()

        # Re-run lightweight or load items
        # To guarantee identical full feature snapshots and explanations, running train_isolation_forest
        # with stored hyperparameters is deterministic and fast
        result = train_isolation_forest(
            dataset_id=dataset_id,
            entity_type=entity_type,
            contamination=contam,
            random_state=r_state,
        )

    # Filter
    filtered_items = result.anomalies
    if anomalies_only:
        filtered_items = [it for it in filtered_items if it.is_anomaly]

    return AnomalyDetectionResult(
        dataset_id=result.dataset_id,
        entity_type=result.entity_type,
        model_name=result.model_name,
        model_version=result.model_version,
        timestamp=result.timestamp,
        total_entities=result.total_entities,
        anomaly_count=result.anomaly_count,
        contamination=result.contamination,
        random_state=result.random_state,
        anomalies=filtered_items[:limit],
    )


def get_model_metadata(dataset_id: str, entity_type: str = "transaction") -> ModelMetadata:
    """Retrieve model training parameters, feature definitions, and missingness records."""
    meta_file = config.MODELS_DIR / dataset_id / f"metadata_{entity_type}.json"
    if not meta_file.is_file():
        # Auto-train to establish model metadata
        train_isolation_forest(dataset_id, entity_type=entity_type)

    if not meta_file.is_file():
        raise FileNotFoundError(f"Model metadata not found for dataset '{dataset_id}'.")

    with open(meta_file, "r", encoding="utf-8") as f:
        meta_dict = json.load(f)

    return ModelMetadata(**meta_dict)
