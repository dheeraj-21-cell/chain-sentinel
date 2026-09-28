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
    """Test 404 response when querying risk scoring endpoints for a non-existent dataset."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/api/v1/risk/{fake_id}/score").status_code == 404
    assert client.get(f"/api/v1/risk/{fake_id}/summary").status_code == 404
    assert client.get(f"/api/v1/risk/{fake_id}/findings").status_code == 404
    assert client.get(f"/api/v1/risk/{fake_id}/metadata").status_code == 404


def test_score_calculation_and_weights(isolated_environment):
    """Verify that the total score equals the sum of evidence contribution points."""
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_calc_1,2026-09-04T12:00:00Z,192.168.1.50,\"['1InA', '1InB']\",\"['1DestCollector']\",\"[1.5, 2.0]\",\"[3.49]\",0.01\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    res = client.post(f"/api/v1/risk/{d_id}/score")
    assert res.status_code == 200
    data = res.json()

    assert data["dataset_id"] == d_id
    assert len(data["findings"]) > 0

    for finding in data["findings"]:
        contribs = finding["evidence_contributions"]
        points_sum = sum(c["points"] for c in contribs.values())
        assert abs(finding["score"] - round(points_sum, 1)) <= 0.1
        assert finding["score"] >= 0.0
        assert finding["score"] <= 100.0


def test_priority_band_assignment(isolated_environment):
    """Verify correct priority band assignment based on score ranges."""
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_p1,2026-09-04T12:00:00Z,192.168.1.1,\"['1SoloA']\",\"['1SoloB']\",\"[0.05]\",\"[0.049]\",0.001\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    res = client.post(f"/api/v1/risk/{d_id}/score")
    assert res.status_code == 200
    findings = res.json()["findings"]

    for f in findings:
        score = f["score"]
        priority = f["priority"]
        if score >= 75.0:
            assert priority == "CRITICAL"
        elif score >= 50.0:
            assert priority == "HIGH"
        elif score >= 25.0:
            assert priority == "MODERATE"
        else:
            assert priority == "LOW"


def test_behavioral_evidence_integration(isolated_environment):
    """Verify that Phase 8 behavioral findings contribute points to the behavioral category."""
    # Fan-in setup: 3 sources fund 1 collector wallet
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_bhv_1,2026-09-04T12:00:00Z,192.168.1.10,"
        "\"['1Src1', '1Src2', '1Src3']\",\"['1TargetCollector']\",\"[1.0, 1.0, 1.0]\",\"[2.99]\",0.01\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    res = client.post(f"/api/v1/risk/{d_id}/score")
    assert res.status_code == 200
    findings = res.json()["findings"]

    collector_finding = [f for f in findings if f["entity_id"] == "1TargetCollector"][0]
    bhv_contrib = collector_finding["evidence_contributions"]["behavioral"]
    assert bhv_contrib["status"] == "present"
    assert bhv_contrib["points"] > 0.0
    assert len(collector_finding["supporting_behavior_findings"]) > 0


def test_clustering_evidence_integration(isolated_environment):
    """Verify that isolated DBSCAN noise points receive clustering points while clustered members receive 0."""
    # 3 identical small wallets (Cluster 0) and 1 extreme outlier (Noise)
    csv_data = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "tx_c1,1NormalA,1.0,1DestCommon,0.99\n"
        "tx_c2,1NormalB,1.0,1DestCommon,0.99\n"
        "tx_c3,1NormalC,1.0,1DestCommon,0.99\n"
        "tx_out,1OutlierWhale,500.0,1WhaleDest,499.0\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    # Pre-run graph and clustering with eps=1.5
    client.post(f"/api/v1/graph/{d_id}/build")
    client.post(f"/api/v1/clustering/{d_id}/run?eps=1.5&min_samples=2")

    res = client.post(f"/api/v1/risk/{d_id}/score")
    assert res.status_code == 200
    findings = res.json()["findings"]

    whale_finding = [f for f in findings if f["entity_id"] == "1OutlierWhale"][0]
    whale_clu = whale_finding["evidence_contributions"]["clustering"]
    assert whale_clu["points"] > 0.0
    assert "noise point" in whale_clu["rationale"]


def test_graph_evidence_integration(isolated_environment):
    """Verify that graph degree and centrality elevate graph_topology contribution."""
    csv_data = (
        "txid,input_addresses,output_addresses\n"
        "tx_hub_1,1HubWallet,1Dest1\n"
        "tx_hub_2,1HubWallet,1Dest2\n"
        "tx_hub_3,1HubWallet,1Dest3\n"
        "tx_hub_4,1HubWallet,1Dest4\n"
        "tx_hub_5,1HubWallet,1Dest5\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)
    client.post(f"/api/v1/graph/{d_id}/build")

    res = client.post(f"/api/v1/risk/{d_id}/score")
    assert res.status_code == 200
    findings = res.json()["findings"]

    hub_finding = [f for f in findings if f["entity_id"] == "1HubWallet"][0]
    graph_contrib = hub_finding["evidence_contributions"]["graph_topology"]
    assert graph_contrib["status"] == "present"
    assert graph_contrib["points"] >= 10.0


def test_deterministic_reproducibility(isolated_environment):
    """Confirm repeated execution produces identical scores, explanations, and rankings."""
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_det,2026-09-04T12:00:00Z,192.168.1.1,\"['1In1', '1In2']\",\"['1Out1']\",\"[1.0, 1.0]\",\"[1.99]\",0.01\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    res1 = client.post(f"/api/v1/risk/{d_id}/score").json()
    res2 = client.post(f"/api/v1/risk/{d_id}/score").json()

    assert len(res1["findings"]) == len(res2["findings"])
    for f1, f2 in zip(res1["findings"], res2["findings"]):
        assert f1["risk_id"] == f2["risk_id"]
        assert f1["entity_id"] == f2["entity_id"]
        assert f1["score"] == f2["score"]
        assert f1["priority"] == f2["priority"]
        assert f1["explanation"] == f2["explanation"]


def test_dataset_isolation_in_risk(isolated_environment):
    """Ensure risk scoring strictly isolates datasets without cross-contamination."""
    csv_a = "txid,input_addresses,output_addresses\ntx_a,1WalletA_1,1WalletA_2\n"
    csv_b = "txid,input_addresses,output_addresses\ntx_b,1WalletB_1,1WalletB_2\n"

    id_a = ingest_test_dataset(csv_a, "dataset_a.csv")
    id_b = ingest_test_dataset(csv_b, "dataset_b.csv")
    isolated_environment.extend([id_a, id_b])

    res_a = client.post(f"/api/v1/risk/{id_a}/score").json()
    res_b = client.post(f"/api/v1/risk/{id_b}/score").json()

    addrs_a = [f["entity_id"] for f in res_a["findings"]]
    addrs_b = [f["entity_id"] for f in res_b["findings"]]

    assert "1WalletA_1" in addrs_a
    assert "1WalletB_1" not in addrs_a
    assert "1WalletB_1" in addrs_b
    assert "1WalletA_1" not in addrs_b


def test_empty_dataset_handling(isolated_environment):
    """Handle empty dataset with 0 records cleanly without errors."""
    csv_data = "txid,input_addresses,output_addresses\n"
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    res = client.post(f"/api/v1/risk/{d_id}/score")
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["total_scored_entities"] == 0
    assert len(data["findings"]) == 0


def test_neutral_explainability(isolated_environment):
    """Verify explanations never contain prohibited criminal accusation terms."""
    csv_data = (
        "txid,timestamp,src_ip,input_addresses,output_addresses,input_amounts,output_amounts,fee\n"
        "tx_neutral,2026-09-04T12:00:00Z,192.168.1.1,\"['1In1', '1In2']\",\"['1Out1']\",\"[1.0, 1.0]\",\"[1.99]\",0.01\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    res = client.post(f"/api/v1/risk/{d_id}/score").json()
    prohibited = ["criminal", "malicious", "ransomware", "laundering", "illegal", "mixer"]

    for finding in res["findings"]:
        full_text = (finding["explanation"] + " ".join(finding["limitations"])).lower()
        for term in prohibited:
            assert f"is a {term}" not in full_text
            assert f"is an {term}" not in full_text
            assert f"belongs to a {term}" not in full_text


def test_api_endpoints(isolated_environment):
    """Verify summary, findings filtering, and metadata endpoints."""
    csv_data = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "tx_ep_1,1AddrA,10.0,1AddrB,9.99\n"
        "tx_ep_2,1AddrC,0.1,1AddrD,0.09\n"
    )
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    # 1. POST /score
    client.post(f"/api/v1/risk/{d_id}/score")

    # 2. GET /summary
    sum_res = client.get(f"/api/v1/risk/{d_id}/summary")
    assert sum_res.status_code == 200
    summary = sum_res.json()
    assert summary["dataset_id"] == d_id
    assert summary["total_scored_entities"] >= 2

    # 3. GET /findings with filter
    find_res = client.get(f"/api/v1/risk/{d_id}/findings?priority=LOW&limit=2")
    assert find_res.status_code == 200
    findings = find_res.json()
    for f in findings:
        assert f["priority"] == "LOW"

    # 4. GET /metadata
    meta_res = client.get(f"/api/v1/risk/{d_id}/metadata")
    assert meta_res.status_code == 200
    meta = meta_res.json()
    assert meta["dataset_id"] == d_id
    assert "behavioral" in meta["weights"]
    assert "LOW" in meta["priority_bands"]


def test_artifact_persistence(isolated_environment):
    """Verify risk_scores.parquet and risk_metadata.json are persisted to disk."""
    csv_data = "txid,input_addresses,output_addresses\ntx_p,1InP,1OutP\n"
    d_id = ingest_test_dataset(csv_data)
    isolated_environment.append(d_id)

    client.post(f"/api/v1/risk/{d_id}/score")

    parquet_file = config.FEATURES_DATA_DIR / d_id / "risk_scores.parquet"
    metadata_file = config.MODELS_DIR / d_id / "risk_metadata.json"

    assert parquet_file.is_file(), f"Expected {parquet_file} to exist"
    assert metadata_file.is_file(), f"Expected {metadata_file} to exist"

    with open(metadata_file, "r") as f:
        meta_data = json.load(f)
    assert meta_data["dataset_id"] == d_id
    assert "behavioral" in meta_data["weights"]
