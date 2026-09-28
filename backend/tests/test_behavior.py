import io
import json
import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.services.graph import get_neo4j_driver

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    """Ensure isolated filesystem storage and clean up test data and graph nodes."""
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    features_dir = tmp_path / "features"
    models_dir = tmp_path / "models"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    features_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "RAW_DATA_DIR", raw_dir)
    monkeypatch.setattr(config, "PROCESSED_DATA_DIR", processed_dir)
    monkeypatch.setattr(config, "FEATURES_DATA_DIR", features_dir)
    monkeypatch.setattr(config, "MODELS_DIR", models_dir)

    test_dataset_ids = []

    yield test_dataset_ids

    # Teardown: Remove all test-created nodes and relationships from Neo4j
    driver = get_neo4j_driver()
    with driver.session() as session:
        for d_id in test_dataset_ids:
            session.run("MATCH (n {dataset_id: $d_id}) DETACH DELETE n", d_id=d_id)


def ingest_test_dataset(csv_content: str, filename: str = "test.csv") -> str:
    """Helper to ingest a test CSV and return dataset_id."""
    resp = client.post(
        "/api/v1/datasets/ingest",
        files={"file": (filename, io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert resp.status_code == 201
    return resp.json()["dataset_id"]


def test_invalid_dataset_handling(isolated_environment):
    """Test 404 response when querying behavioral endpoints for a non-existent dataset."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/api/v1/behavior/{fake_id}/detect").status_code == 404
    assert client.get(f"/api/v1/behavior/{fake_id}/summary").status_code == 404
    assert client.get(f"/api/v1/behavior/{fake_id}/findings").status_code == 404
    assert client.get(f"/api/v1/behavior/{fake_id}/metadata").status_code == 404


def test_fan_in_detection(isolated_environment):
    """Test fan-in indicator detects wallets receiving funds from multiple distinct sources."""
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_fan_in_1,2026-09-04T12:00:00Z,192.168.1.100,"
        "\"['1SrcA11111111111111111111111111111', '1SrcB22222222222222222222222222222', '1SrcC33333333333333333333333333333']\","
        "\"['1CollectorWallet999999999999999999']\",\"[1.0, 2.0, 3.0]\",\"[5.99]\",0.01\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    res = client.post(f"/api/v1/behavior/{d_id}/detect", json={"min_fan_in_sources": 2})
    assert res.status_code == 200
    data = res.json()

    fan_in_findings = [f for f in data["findings"] if f["detection_type"] == "fan_in"]
    assert len(fan_in_findings) == 1
    finding = fan_in_findings[0]
    assert finding["entity_id"] == "1CollectorWallet999999999999999999"
    assert finding["entity_type"] == "wallet"
    assert finding["observed_facts"]["distinct_source_count"] == 3
    assert finding["observed_facts"]["total_received_btc"] == 5.99
    assert "fan-in indicator threshold" in finding["explanation"]
    assert len(finding["limitations"]) > 0


def test_fan_out_detection(isolated_environment):
    """Test fan-out indicator detects wallets distributing funds to multiple distinct destinations."""
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_fan_out_1,2026-09-04T12:00:00Z,192.168.1.101,"
        "\"['1DistributorWallet111111111111111']\","
        "\"['1DestA1111111111111111111111111111', '1DestB2222222222222222222222222222', '1DestC3333333333333333333333333333']\","
        "\"[10.0]\",\"[3.0, 3.0, 3.99]\",0.01\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    res = client.post(f"/api/v1/behavior/{d_id}/detect", json={"min_fan_out_destinations": 2})
    assert res.status_code == 200
    data = res.json()

    fan_out_findings = [f for f in data["findings"] if f["detection_type"] == "fan_out"]
    assert len(fan_out_findings) == 1
    finding = fan_out_findings[0]
    assert finding["entity_id"] == "1DistributorWallet111111111111111"
    assert finding["entity_type"] == "wallet"
    assert finding["observed_facts"]["distinct_destination_count"] == 3
    assert "fan-out indicator threshold" in finding["explanation"]


def test_rapid_dispersion_detection(isolated_environment):
    """Test rapid dispersion indicator detects multi-destination disbursement in short time window."""
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_disp_1,2026-09-04T12:00:00Z,192.168.1.102,"
        "\"['1Sender1111111111111111111111111111']\","
        "\"['1RecvA1111111111111111111111111111', '1RecvB2222222222222222222222222222', '1RecvC3333333333333333333333333333']\","
        "\"[5.0]\",\"[1.5, 1.5, 1.99]\",0.01\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    res = client.post(
        f"/api/v1/behavior/{d_id}/detect",
        json={"rapid_dispersion_window_seconds": 1800, "rapid_dispersion_min_destinations": 2},
    )
    assert res.status_code == 200
    data = res.json()

    disp_findings = [f for f in data["findings"] if f["detection_type"] == "rapid_dispersion"]
    assert len(disp_findings) == 1
    finding = disp_findings[0]
    assert finding["entity_id"] == "tx_disp_1"
    assert finding["entity_type"] == "transaction"
    assert finding["observed_facts"]["destination_count"] == 3


def test_transaction_burst_detection(isolated_environment):
    """Test transaction burst indicator detects dense transaction clusters within sliding window."""
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_b1,2026-09-04T12:00:00Z,192.168.1.50,\"['1BurstWallet111111111111111111111']\",\"['1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa']\",\"[1.0]\",\"[0.99]\",0.01\n"
        "tx_b2,2026-09-04T12:02:00Z,192.168.1.50,\"['1BurstWallet111111111111111111111']\",\"['12c6DSiU4Rq3P4ZxziKxzrL5LmMBrzjrJX']\",\"[1.0]\",\"[0.99]\",0.01\n"
        "tx_b3,2026-09-04T12:04:00Z,192.168.1.50,\"['1BurstWallet111111111111111111111']\",\"['1HLoD9E4SDFFPDiYfNYnkBLQmm5505MDS']\",\"[1.0]\",\"[0.99]\",0.01\n"
        "tx_b4,2026-09-04T12:06:00Z,192.168.1.50,\"['1BurstWallet111111111111111111111']\",\"['1dice8EMZmqKvrGE4Qc9bUFf9PX3xaYDp']\",\"[1.0]\",\"[0.99]\",0.01\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    res = client.post(
        f"/api/v1/behavior/{d_id}/detect",
        json={"burst_window_seconds": 1800, "burst_min_tx_count": 3},
    )
    assert res.status_code == 200
    data = res.json()

    burst_findings = [f for f in data["findings"] if f["detection_type"] == "transaction_burst"]
    assert len(burst_findings) >= 1
    w_burst = [f for f in burst_findings if f["entity_id"] == "1BurstWallet111111111111111111111"]
    assert len(w_burst) == 1
    assert w_burst[0]["observed_facts"]["burst_transaction_count"] == 4


def test_dormant_to_active_insufficient_history(isolated_environment):
    """Test dormant-to-active reports insufficient temporal history when observation span is too short."""
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_d1,2026-09-04T12:00:00Z,192.168.1.1,\"['1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa']\",\"['12c6DSiU4Rq3P4ZxziKxzrL5LmMBrzjrJX']\",\"[1.0]\",\"[0.99]\",0.01\n"
        "tx_d2,2026-09-04T12:15:00Z,192.168.1.1,\"['1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa']\",\"['1HLoD9E4SDFFPDiYfNYnkBLQmm5505MDS']\",\"[1.0]\",\"[0.99]\",0.01\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    res = client.post(f"/api/v1/behavior/{d_id}/detect")
    assert res.status_code == 200
    data = res.json()

    # Dormant findings must be 0
    dormant_findings = [f for f in data["findings"] if f["detection_type"] == "dormant_to_active"]
    assert len(dormant_findings) == 0

    # Summary must explicitly note insufficient temporal history
    dorm_summary = [s for s in data["summary"]["detector_summaries"] if s["detector_name"] == "dormant_to_active"][0]
    assert dorm_summary["status"] == "insufficient_temporal_history"
    assert "less than the required dormancy threshold" in dorm_summary["message"]


def test_dormant_to_active_detection(isolated_environment):
    """Test dormant-to-active detects prolonged dormancy followed by renewed activity."""
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_early,2026-01-01T12:00:00Z,192.168.1.1,\"['1DormantWallet1111111111111111111']\",\"['1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa']\",\"[1.0]\",\"[0.99]\",0.01\n"
        "tx_reactivated,2026-03-01T12:00:00Z,192.168.1.1,\"['1DormantWallet1111111111111111111']\",\"['12c6DSiU4Rq3P4ZxziKxzrL5LmMBrzjrJX']\",\"[1.0]\",\"[0.99]\",0.01\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    # Threshold: 30 days (86400 * 30), span between Jan 1 and Mar 1 is ~59 days
    res = client.post(f"/api/v1/behavior/{d_id}/detect", json={"dormancy_threshold_seconds": 86400 * 30})
    assert res.status_code == 200
    data = res.json()

    dormant_findings = [f for f in data["findings"] if f["detection_type"] == "dormant_to_active"]
    assert len(dormant_findings) == 1
    finding = dormant_findings[0]
    assert finding["entity_id"] == "1DormantWallet1111111111111111111"
    assert finding["observed_facts"]["dormant_days"] > 50


def test_multi_hop_movement_detection(isolated_environment):
    """Test multi-hop movement detects directed indirect transaction paths."""
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_hop_1,2026-09-04T12:00:00Z,192.168.1.1,\"['1HopOrigin1111111111111111111111']\",\"['1HopIntermediary222222222222222']\",\"[5.0]\",\"[4.99]\",0.01\n"
        "tx_hop_2,2026-09-04T12:10:00Z,192.168.1.1,\"['1HopIntermediary222222222222222']\",\"['1HopDest33333333333333333333333']\",\"[4.99]\",\"[4.98]\",0.01\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    res = client.post(f"/api/v1/behavior/{d_id}/detect", json={"min_multi_hop_depth": 2, "max_multi_hop_depth": 3})
    assert res.status_code == 200
    data = res.json()

    hop_findings = [f for f in data["findings"] if f["detection_type"] == "multi_hop_movement"]
    assert len(hop_findings) >= 1
    finding = hop_findings[0]
    assert finding["observed_facts"]["source_wallet"] == "1HopOrigin1111111111111111111111"
    assert finding["observed_facts"]["destination_wallet"] == "1HopDest33333333333333333333333"
    assert finding["observed_facts"]["hop_count"] == 2
    assert "tx_hop_1" in finding["supporting_transaction_ids"]
    assert "tx_hop_2" in finding["supporting_transaction_ids"]


def test_peeling_chain_detection(isolated_environment):
    """Test peeling-chain-like structure detector identifies sequential change chains without criminal terms."""
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_peel_1,2026-09-04T12:00:00Z,192.168.1.1,\"['1OriginFunder000000000000000000']\",\"['1PeelPayment111111111111111111', '1ChangeContinuation111111111111']\",\"[10.0]\",\"[0.5, 9.49]\",0.01\n"
        "tx_peel_2,2026-09-04T12:10:00Z,192.168.1.1,\"['1ChangeContinuation111111111111']\",\"['1PeelPayment222222222222222222', '1ChangeContinuation222222222222']\",\"[9.49]\",\"[0.5, 8.98]\",0.01\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    res = client.post(f"/api/v1/behavior/{d_id}/detect", json={"min_peel_length": 2})
    assert res.status_code == 200
    data = res.json()

    peel_findings = [f for f in data["findings"] if f["detection_type"] == "peeling_chain_like"]
    assert len(peel_findings) == 1
    finding = peel_findings[0]
    assert finding["observed_facts"]["chain_length"] == 2
    assert "peeling-chain-like behavioral pattern" in finding["explanation"]

    # Neutrality verification: Prohibited criminal terms must never appear
    prohibited_terms = ["criminal", "malicious", "ransomware", "laundering", "illegal", "mixer"]
    text_to_check = (finding["explanation"] + " ".join(finding["limitations"])).lower()
    for term in prohibited_terms:
        assert f"is a {term}" not in text_to_check
        assert f"is an {term}" not in text_to_check


def test_dataset_isolation_in_behavior(isolated_environment):
    """Ensure behavioral detection maintains strict dataset isolation across datasets."""
    csv_a = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_a_1,2026-09-04T12:00:00Z,10.0.0.1,\"['1SrcA_111111', '1SrcA_222222']\",\"['1DestA_333333']\",\"[1.0, 1.0]\",\"[1.99]\",0.01\n"
    )
    csv_b = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_b_1,2026-09-04T12:00:00Z,10.0.0.2,\"['1SrcB_111111', '1SrcB_222222']\",\"['1DestB_333333']\",\"[2.0, 2.0]\",\"[3.99]\",0.01\n"
    )
    id_a = ingest_test_dataset(csv_a, "dataset_a.csv")
    id_b = ingest_test_dataset(csv_b, "dataset_b.csv")
    isolated_environment.extend([id_a, id_b])

    res_a = client.post(f"/api/v1/behavior/{id_a}/detect")
    res_b = client.post(f"/api/v1/behavior/{id_b}/detect")

    findings_a = res_a.json()["findings"]
    findings_b = res_b.json()["findings"]

    for f in findings_a:
        assert f["dataset_id"] == id_a
        assert "SrcB" not in f["entity_id"]
        assert "DestB" not in f["entity_id"]

    for f in findings_b:
        assert f["dataset_id"] == id_b
        assert "SrcA" not in f["entity_id"]
        assert "DestA" not in f["entity_id"]


def test_deterministic_reproducibility(isolated_environment):
    """Confirm repeated execution of behavioral detection yields bitwise identical results."""
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_det_1,2026-09-04T12:00:00Z,192.168.1.1,\"['1In1', '1In2']\",\"['1Out1']\",\"[1.0, 1.0]\",\"[1.99]\",0.01\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    res1 = client.post(f"/api/v1/behavior/{d_id}/detect").json()
    res2 = client.post(f"/api/v1/behavior/{d_id}/detect").json()

    assert len(res1["findings"]) == len(res2["findings"])
    for f1, f2 in zip(res1["findings"], res2["findings"]):
        assert f1["detection_id"] == f2["detection_id"]
        assert f1["detection_type"] == f2["detection_type"]
        assert f1["entity_id"] == f2["entity_id"]
        assert f1["explanation"] == f2["explanation"]


def test_empty_dataset_handling(isolated_environment):
    """Handle empty dataset with 0 valid records gracefully without exceptions."""
    csv_data = "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    res = client.post(f"/api/v1/behavior/{d_id}/detect")
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["total_findings"] == 0
    assert len(data["findings"]) == 0


def test_api_endpoints(isolated_environment):
    """Verify summary, findings filtering, and metadata endpoints."""
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_api_1,2026-09-04T12:00:00Z,192.168.1.10,\"['1InA', '1InB']\",\"['1DestM', '1DestN']\",\"[1.0, 2.0]\",\"[1.5, 1.49]\",0.01\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    # 1. POST /detect
    client.post(f"/api/v1/behavior/{d_id}/detect")

    # 2. GET /summary
    sum_res = client.get(f"/api/v1/behavior/{d_id}/summary")
    assert sum_res.status_code == 200
    summary = sum_res.json()
    assert summary["dataset_id"] == d_id
    assert summary["total_findings"] >= 1

    # 3. GET /findings with filter
    find_res = client.get(f"/api/v1/behavior/{d_id}/findings?detection_type=fan_in")
    assert find_res.status_code == 200
    findings = find_res.json()
    for f in findings:
        assert f["detection_type"] == "fan_in"

    # 4. GET /metadata
    meta_res = client.get(f"/api/v1/behavior/{d_id}/metadata")
    assert meta_res.status_code == 200
    meta = meta_res.json()
    assert meta["dataset_id"] == d_id
    assert "fan_in" in meta["enabled_detectors"]
    assert len(meta["limitations"]) > 0


def test_artifact_persistence(isolated_environment):
    """Verify behavioral findings parquet and metadata json are persisted to disk."""
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_persist,2026-09-04T12:00:00Z,192.168.1.1,\"['1In1', '1In2']\",\"['1Out1']\",\"[1.0, 1.0]\",\"[1.99]\",0.01\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    client.post(f"/api/v1/behavior/{d_id}/detect")

    parquet_file = config.FEATURES_DATA_DIR / d_id / "behavioral_findings.parquet"
    metadata_file = config.MODELS_DIR / d_id / "behavioral_metadata.json"

    assert parquet_file.is_file(), f"Expected {parquet_file} to exist"
    assert metadata_file.is_file(), f"Expected {metadata_file} to exist"

    with open(metadata_file, "r") as f:
        meta_data = json.load(f)
    assert meta_data["dataset_id"] == d_id
    assert "fan_in" in meta_data["enabled_detectors"]
