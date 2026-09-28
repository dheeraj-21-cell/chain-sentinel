import json
from pathlib import Path
from typing import List, Optional

import polars as pl

from app import config
from app.models.dataset import IngestionMetadata, RejectedRecord
from app.models.transaction import NormalizedTransaction


def save_raw_file(dataset_id: str, filename: str, content: bytes) -> str:
    """Save raw uploaded file under data/raw/{dataset_id}/{filename} for provenance."""
    target_dir = config.RAW_DATA_DIR / dataset_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / filename
    with open(target_path, "wb") as f:
        f.write(content)
    return str(target_path)


def save_normalized_parquet(dataset_id: str, records: List[NormalizedTransaction]) -> Optional[str]:
    """Persist normalized records to a Parquet file using Polars."""
    if not records:
        return None

    target_dir = config.PROCESSED_DATA_DIR / dataset_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / "normalized.parquet"

    data_dicts = [r.model_dump() for r in records]
    df = pl.DataFrame(data_dicts)
    df.write_parquet(target_path)

    return str(target_path)


def save_rejected_records(dataset_id: str, rejected: List[RejectedRecord]) -> Optional[str]:
    """Save rejected records and error details to JSON under data/processed/{dataset_id}/."""
    if not rejected:
        return None

    target_dir = config.PROCESSED_DATA_DIR / dataset_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / "rejected_records.json"

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump([r.model_dump() for r in rejected], f, indent=2)

    return str(target_path)


def save_metadata(metadata: IngestionMetadata) -> str:
    """Save dataset ingestion metadata to data/processed/{dataset_id}/metadata.json."""
    target_dir = config.PROCESSED_DATA_DIR / metadata.dataset_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / "metadata.json"

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(metadata.model_dump_json(indent=2))

    return str(target_path)


def load_metadata(dataset_id: str) -> Optional[IngestionMetadata]:
    """Load metadata for a given dataset_id."""
    meta_path = config.PROCESSED_DATA_DIR / dataset_id / "metadata.json"
    if not meta_path.is_file():
        return None
    with open(meta_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return IngestionMetadata(**data)


def load_rejected_records(dataset_id: str) -> List[RejectedRecord]:
    """Load rejected records for a given dataset_id."""
    reject_path = config.PROCESSED_DATA_DIR / dataset_id / "rejected_records.json"
    if not reject_path.is_file():
        return []
    with open(reject_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [RejectedRecord(**item) for item in data]


def find_dataset_by_content_hash(content_sha256: str) -> Optional[IngestionMetadata]:
    """Find an existing successfully ingested dataset with matching content SHA-256."""
    if not config.PROCESSED_DATA_DIR.is_dir() or not content_sha256:
        return None
    for dataset_folder in config.PROCESSED_DATA_DIR.iterdir():
        if dataset_folder.is_dir():
            meta_path = dataset_folder / "metadata.json"
            if meta_path.is_file():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    meta = IngestionMetadata(**data)
                    if meta.content_sha256 == content_sha256 and meta.records_valid > 0:
                        return meta
                except Exception:
                    continue
    return None


def delete_dataset_storage(dataset_id: str) -> bool:
    """Delete all filesystem storage for a dataset across raw, processed, features, evidence, models."""
    import shutil
    deleted = False
    dirs_to_clean = [
        config.PROCESSED_DATA_DIR / dataset_id,
        config.RAW_DATA_DIR / dataset_id,
        config.FEATURES_DATA_DIR / dataset_id,
        config.EVIDENCE_DATA_DIR / dataset_id,
        config.MODELS_DIR / dataset_id,
    ]
    for d in dirs_to_clean:
        if d.exists() and d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            deleted = True
    return deleted


def list_all_metadata(include_invalid: bool = False) -> List[IngestionMetadata]:
    """List all ingestion metadata records across processed datasets, filtering 0-valid/failed test runs."""
    results: List[IngestionMetadata] = []
    if not config.PROCESSED_DATA_DIR.is_dir():
        return results

    for dataset_folder in config.PROCESSED_DATA_DIR.iterdir():
        if dataset_folder.is_dir():
            meta_path = dataset_folder / "metadata.json"
            if meta_path.is_file():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    meta = IngestionMetadata(**data)
                    # Filter out failed / 0-valid-record datasets unless explicitly requested
                    if not include_invalid and (meta.records_valid == 0 or meta.validation_status == "FAILED"):
                        continue
                    results.append(meta)
                except Exception:
                    continue
    results.sort(key=lambda m: m.ingestion_timestamp, reverse=True)
    return results
