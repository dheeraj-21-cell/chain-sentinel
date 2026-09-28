import csv
from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from scripts.generate_synthetic_dataset import generate_synthetic_dataset

client = TestClient(app)


def test_generator_output_size_and_file_creation(tmp_path):
    """Test generator produces requested record count and valid file."""
    out_file = tmp_path / "test_demo.csv"
    generated_path = generate_synthetic_dataset(target_count=150, seed=123, output_path=out_file)
    assert generated_path.exists()
    assert generated_path.is_file()

    with open(generated_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) >= 100
    assert len(reader) <= 150


def test_generator_reproducibility(tmp_path):
    """Test that the same random seed produces bitwise identical CSV outputs."""
    out_file1 = tmp_path / "run1.csv"
    out_file2 = tmp_path / "run2.csv"

    generate_synthetic_dataset(target_count=200, seed=999, output_path=out_file1)
    generate_synthetic_dataset(target_count=200, seed=999, output_path=out_file2)

    content1 = out_file1.read_bytes()
    content2 = out_file2.read_bytes()

    hash1 = hashlib.sha256(content1).hexdigest()
    hash2 = hashlib.sha256(content2).hexdigest()
    assert hash1 == hash2


def test_schema_validity(tmp_path):
    """Test header matches the canonical SIH schema specification."""
    out_file = tmp_path / "schema_test.csv"
    generate_synthetic_dataset(target_count=100, seed=42, output_path=out_file)

    expected_headers = [
        "timestamp",
        "src_ip",
        "dst_ip",
        "src_port",
        "dst_port",
        "txid",
        "input_addresses",
        "input_amounts",
        "output_addresses",
        "output_amounts",
        "fee",
        "script_type",
        "geo_country",
        "asn",
    ]

    with open(out_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)

    assert headers == expected_headers


def test_array_length_alignment(tmp_path):
    """Assert input address count == input amount count, and output count == output amount count."""
    out_file = tmp_path / "array_test.csv"
    generate_synthetic_dataset(target_count=300, seed=42, output_path=out_file)

    with open(out_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            # Inputs
            in_addrs = [a.strip() for a in row["input_addresses"].split(";") if a.strip()]
            in_amts = [float(a.strip()) for a in row["input_amounts"].split(";") if a.strip()]
            assert len(in_addrs) == len(in_amts), (
                f"Row {idx} input mismatch: {len(in_addrs)} addrs vs {len(in_amts)} amounts"
            )

            # Outputs
            out_addrs = [a.strip() for a in row["output_addresses"].split(";") if a.strip()]
            out_amts = [float(a.strip()) for a in row["output_amounts"].split(";") if a.strip()]
            assert len(out_addrs) == len(out_amts), (
                f"Row {idx} output mismatch: {len(out_addrs)} addrs vs {len(out_amts)} amounts"
            )


def test_timestamp_validity(tmp_path):
    """Assert all timestamps parse to valid UTC ISO-8601 strings and are chronological."""
    out_file = tmp_path / "time_test.csv"
    generate_synthetic_dataset(target_count=200, seed=42, output_path=out_file)

    timestamps = []
    with open(out_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            ts_str = row["timestamp"]
            assert ts_str.endswith("Z"), f"Row {idx} timestamp missing Z: {ts_str}"
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            assert dt.tzinfo == timezone.utc
            timestamps.append(dt)

    # Check non-decreasing chronological order
    for i in range(1, len(timestamps)):
        assert timestamps[i] >= timestamps[i - 1], f"Timestamp inversion at index {i}"


def test_unique_txids(tmp_path):
    """Assert all distinct transactions have unique 64-character hex transaction IDs."""
    out_file = tmp_path / "txid_test.csv"
    generate_synthetic_dataset(target_count=300, seed=42, output_path=out_file)

    txids = set()
    with open(out_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            txid = row["txid"]
            assert len(txid) == 64, f"Row {idx} txid length {len(txid)} != 64"
            assert txid not in txids, f"Row {idx} duplicate txid: {txid}"
            txids.add(txid)


def test_behavioral_populations_presence(tmp_path):
    """Verify presence of diverse structural behavioral populations in the dataset."""
    out_file = tmp_path / "pop_test.csv"
    generate_synthetic_dataset(target_count=600, seed=42, output_path=out_file)

    has_fan_in = False
    has_fan_out = False
    has_peeling = False
    has_missing_telemetry = False

    with open(out_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            in_count = len(row["input_addresses"].split(";"))
            out_count = len(row["output_addresses"].split(";"))
            if in_count >= 3 and out_count == 1:
                has_fan_in = True
            if in_count == 1 and out_count >= 4:
                has_fan_out = True
            if in_count == 1 and out_count == 2 and float(row["input_amounts"]) >= 20.0:
                has_peeling = True
            if row["src_ip"] == "" and row["dst_ip"] == "":
                has_missing_telemetry = True

    assert has_fan_in, "Fan-in consolidation population not found in synthetic dataset"
    assert has_fan_out, "Fan-out distribution population not found in synthetic dataset"
    assert has_peeling, "Peeling chain population not found in synthetic dataset"
    assert has_missing_telemetry, "Legitimate missing telemetry records not found in synthetic dataset"


def test_successful_ingestion_of_synthetic_dataset(tmp_path):
    """Verify generated dataset uploads cleanly through /api/v1/datasets/ingest with 100% valid records."""
    out_file = tmp_path / "ingest_demo.csv"
    generate_synthetic_dataset(target_count=100, seed=42, output_path=out_file)

    with open(out_file, "rb") as f:
        content = f.read()

    response = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("demo.csv", io.BytesIO(content), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["records_total"] >= 90
    assert data["records_valid"] == data["records_total"]
    assert data["records_rejected"] == 0
    assert data["dataset_id"] is not None
