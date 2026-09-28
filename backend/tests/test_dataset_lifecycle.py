import io
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_duplicate_dataset_ingestion_idempotence():
    """Verify uploading identical content returns the existing dataset ID without duplicate directories."""
    csv_content = (
        "timestamp,src_ip,dst_ip,src_port,dst_port,txid,input_addresses,input_amounts,output_addresses,output_amounts,fee,script_type,geo_country,asn\n"
        "2026-09-05T12:00:00Z,198.51.100.1,203.0.113.1,8333,8333,tx_dedup_01,1DedupSender11111111111111111,1.0,1DedupRecipient1111111111111111,0.999,0.001,p2pkh,IN,55836\n"
    )

    # First ingestion
    resp1 = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("dedup_test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert resp1.status_code == 201
    id1 = resp1.json()["dataset_id"]
    sha1 = resp1.json()["content_sha256"]
    assert sha1 is not None

    # Second ingestion of exact same content
    resp2 = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("dedup_test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert resp2.status_code == 201
    id2 = resp2.json()["dataset_id"]

    # Must be the exact same dataset ID (no duplicate created)
    assert id1 == id2

    # Clean up test dataset
    del_resp = client.delete(f"/api/v1/datasets/{id1}")
    assert del_resp.status_code == 200


def test_force_reingestion_creates_distinct_dataset():
    """Verify force=True bypasses deduplication when explicitly requested."""
    csv_content = (
        "timestamp,src_ip,dst_ip,src_port,dst_port,txid,input_addresses,input_amounts,output_addresses,output_amounts,fee,script_type,geo_country,asn\n"
        "2026-09-05T12:05:00Z,198.51.100.2,203.0.113.2,8333,8333,tx_force_01,1ForceSender11111111111111111,2.0,1ForceRecipient1111111111111111,1.999,0.001,p2pkh,US,13335\n"
    )

    resp1 = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("force_test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert resp1.status_code == 201
    id1 = resp1.json()["dataset_id"]

    resp2 = client.post(
        "/api/v1/datasets/ingest?force=true",
        files={"file": ("force_test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert resp2.status_code == 201
    id2 = resp2.json()["dataset_id"]

    assert id1 != id2

    # Clean up both
    client.delete(f"/api/v1/datasets/{id1}")
    client.delete(f"/api/v1/datasets/{id2}")


def test_delete_dataset_not_found():
    """Verify 404 is returned when attempting to delete a non-existent dataset."""
    resp = client.delete("/api/v1/datasets/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_list_datasets_excludes_invalid_by_default():
    """Verify failed / 0-valid-record test ingestions are excluded from default listing."""
    # Ingest bad CSV that fails validation
    bad_csv = "txid,src_ip\ntx_bad,999.999.999.999\n"
    resp = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("corrupt.csv", io.BytesIO(bad_csv.encode("utf-8")), "text/csv")},
    )
    bad_id = resp.json()["dataset_id"]

    # Default listing should exclude 0-valid-record datasets
    list_resp = client.get("/api/v1/datasets")
    assert list_resp.status_code == 200
    ids = [d["dataset_id"] for d in list_resp.json()]
    assert bad_id not in ids

    # Clean up
    client.delete(f"/api/v1/datasets/{bad_id}")


def test_showcase_dataset_properties_and_isolation():
    """Verify SIH showcase dataset has 16 records, readable graph, and detected patterns."""
    list_resp = client.get("/api/v1/datasets")
    assert list_resp.status_code == 200
    datasets = list_resp.json()
    showcase = next((d for d in datasets if "showcase" in d["original_filename"].lower()), None)

    assert showcase is not None, "SIH showcase dataset must be present in dataset list"
    assert showcase["records_valid"] == 16
    assert showcase["records_total"] == 16
    assert showcase["validation_status"] == "SUCCESS"

    sid = showcase["dataset_id"]

    # Verify DuckDB summary isolation
    sum_resp = client.get(f"/api/v1/analytics/{sid}/summary")
    assert sum_resp.status_code == 200
    summary = sum_resp.json()
    assert summary["total_records"] == 16
    assert summary["unique_txids"] == 16
    assert summary["unique_ips"] == 4

    # Verify Neo4j readable graph (between 30 and 60 nodes - NOT a spaghetti ball)
    graph_resp = client.get(f"/api/v1/graph/{sid}/summary")
    assert graph_resp.status_code == 200
    g_summary = graph_resp.json()
    assert 30 <= g_summary["total_nodes"] <= 60
    assert 40 <= g_summary["total_relationships"] <= 120

    # Verify behavioral findings
    bh_resp = client.get(f"/api/v1/behavior/{sid}/summary")
    assert bh_resp.status_code == 200
    bh_summary = bh_resp.json()
    assert bh_summary["findings_by_type"]["fan_in"] >= 1
    assert bh_summary["findings_by_type"]["fan_out"] >= 1
    assert bh_summary["findings_by_type"]["rapid_dispersion"] >= 1
    assert bh_summary["findings_by_type"]["transaction_burst"] >= 1
    assert bh_summary["findings_by_type"]["peeling_chain_like"] >= 1
    assert bh_summary["findings_by_type"]["multi_hop_movement"] >= 1
