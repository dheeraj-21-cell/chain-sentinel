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
    """Test 404 response when querying clustering endpoints for a non-existent dataset."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    res_r = client.post(f"/api/v1/clustering/{fake_id}/run")
    assert res_r.status_code == 404

    res_s = client.get(f"/api/v1/clustering/{fake_id}/summary")
    assert res_s.status_code == 404

    res_e = client.get(f"/api/v1/clustering/{fake_id}/entities")
    assert res_e.status_code == 404

    res_m = client.get(f"/api/v1/clustering/{fake_id}/metadata")
    assert res_m.status_code == 404


def test_parameter_validation(isolated_environment):
    """Test validation errors on invalid eps (<=0) or min_samples (<1)."""
    csv = "txid,input_addresses,output_addresses\ntx1,w1,w2\n"
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    res_eps = client.post(f"/api/v1/clustering/{dataset_id}/run?eps=0.0")
    assert res_eps.status_code == 422

    res_min = client.post(f"/api/v1/clustering/{dataset_id}/run?min_samples=0")
    assert res_min.status_code == 422


def test_dbscan_clustering_flow(isolated_environment):
    """Verify DBSCAN groups wallets with similar behavior into clusters."""
    # Group A: 3 wallets with identical small payments (consolidation group)
    # Group B: 1 extreme outlier wallet with massive flow
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "tx_g1,w_g1_a,1.0,w_recv_1,0.99\n"
        "tx_g2,w_g1_b,1.0,w_recv_1,0.99\n"
        "tx_g3,w_g1_c,1.0,w_recv_1,0.99\n"
        "tx_outlier,w_whale,500.0,w_dest,499.0\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)
    client.post(f"/api/v1/graph/{dataset_id}/build")

    res = client.post(f"/api/v1/clustering/{dataset_id}/run?eps=1.5&min_samples=2")
    assert res.status_code == 200
    data = res.json()

    assert data["dataset_id"] == dataset_id
    assert data["total_entities"] > 0
    assert data["eps"] == 1.5
    assert data["min_samples"] == 2
    assert "clusters" in data
    assert "entities" in data


def test_noise_handling(isolated_environment):
    """Verify distinct behavioral outliers are classified as noise (-1)."""
    # 3 identical normal wallets and 1 extreme outlier
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "tx1,norm_1,0.1,shared_recv,0.09\n"
        "tx2,norm_2,0.1,shared_recv,0.09\n"
        "tx3,norm_3,0.1,shared_recv,0.09\n"
        "tx_solo,extreme_outlier,1000.0,solo_recv,999.0\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    res = client.post(f"/api/v1/clustering/{dataset_id}/run?eps=0.8&min_samples=2")
    assert res.status_code == 200
    data = res.json()

    assert data["noise_count"] >= 1
    # Check noise_only entity query
    noise_res = client.get(f"/api/v1/clustering/{dataset_id}/entities?noise_only=true")
    assert noise_res.status_code == 200
    noise_items = noise_res.json()
    assert len(noise_items) == data["noise_count"]
    for item in noise_items:
        assert item["is_noise"] is True
        assert item["cluster_id"] == -1


def test_repeatability_and_determinism(isolated_environment):
    """Verify repeated clustering with identical parameters produces deterministic cluster assignments."""
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "tx1,w1,1.0,w2,0.99\n"
        "tx2,w2,1.0,w3,0.99\n"
        "tx3,w3,1.0,w4,0.99\n"
        "tx4,w4,1.0,w5,0.99\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    res1 = client.post(f"/api/v1/clustering/{dataset_id}/run?eps=1.0&min_samples=2")
    res2 = client.post(f"/api/v1/clustering/{dataset_id}/run?eps=1.0&min_samples=2")

    assert res1.status_code == 200
    assert res2.status_code == 200

    data1 = res1.json()
    data2 = res2.json()

    assert data1["cluster_count"] == data2["cluster_count"]
    assert data1["noise_count"] == data2["noise_count"]

    ent1 = {e["address"]: e["cluster_id"] for e in data1["entities"]}
    ent2 = {e["address"]: e["cluster_id"] for e in data2["entities"]}
    assert ent1 == ent2


def test_dataset_isolation_in_clustering(isolated_environment):
    """Verify clustering between two different datasets remains strictly isolated."""
    csv1 = "txid,input_addresses,input_amounts,output_addresses,output_amounts\ntx_d1,w_d1_a,1.0,w_d1_b,0.99\n"
    csv2 = "txid,input_addresses,input_amounts,output_addresses,output_amounts\ntx_d2,w_d2_a,5.0,w_d2_b,4.99\n"

    d1 = ingest_test_dataset(csv1, "d1.csv")
    d2 = ingest_test_dataset(csv2, "d2.csv")
    isolated_environment.extend([d1, d2])

    res1 = client.post(f"/api/v1/clustering/{d1}/run")
    res2 = client.post(f"/api/v1/clustering/{d2}/run")

    assert res1.status_code == 200
    assert res2.status_code == 200

    d1_addrs = {e["address"] for e in res1.json()["entities"]}
    d2_addrs = {e["address"] for e in res2.json()["entities"]}

    assert "w_d1_a" in d1_addrs
    assert "w_d2_a" not in d1_addrs

    assert "w_d2_a" in d2_addrs
    assert "w_d1_a" not in d2_addrs


def test_empty_dataset_handling(isolated_environment):
    """Verify empty dataset (0 valid records) is handled cleanly without errors."""
    csv = "txid,input_addresses,output_addresses\n"
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    res = client.post(f"/api/v1/clustering/{dataset_id}/run")
    assert res.status_code == 200
    data = res.json()
    assert data["total_entities"] == 0
    assert data["cluster_count"] == 0
    assert data["noise_count"] == 0
    assert data["clusters"] == []
    assert data["entities"] == []


def test_small_dataset_handling(isolated_environment):
    """Verify single-wallet dataset where count < min_samples is classified as noise without error."""
    csv = "txid,input_addresses,input_amounts,output_addresses,output_amounts\ntx1,w_solo,1.0,w_solo,1.0\n"
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    res = client.post(f"/api/v1/clustering/{dataset_id}/run?min_samples=2")
    assert res.status_code == 200
    data = res.json()
    assert data["total_entities"] == 1
    assert data["noise_count"] == 1
    assert data["entities"][0]["is_noise"] is True


def test_artifact_persistence(isolated_environment):
    """Verify clustered entities Parquet and metadata JSON are persisted to disk."""
    csv = "txid,input_addresses,input_amounts,output_addresses,output_amounts\ntx1,w1,1.0,w2,0.99\n"
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    client.post(f"/api/v1/clustering/{dataset_id}/run")

    cluster_file = config.FEATURES_DATA_DIR / dataset_id / "wallet_clusters.parquet"
    assert cluster_file.is_file()

    meta_file = config.MODELS_DIR / dataset_id / "dbscan_wallet_metadata.json"
    assert meta_file.is_file()
    with open(meta_file, "r") as f:
        meta_dict = json.load(f)
    assert meta_dict["model_name"] == "scikit-learn DBSCAN"
    assert meta_dict["total_entities"] == 2


def test_api_endpoints(isolated_environment):
    """Test /summary, /entities, and /metadata endpoints."""
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "tx1,w1,1.0,w2,0.99\n"
        "tx2,w2,1.0,w3,0.99\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    client.post(f"/api/v1/clustering/{dataset_id}/run")

    # 1. Summary
    res_s = client.get(f"/api/v1/clustering/{dataset_id}/summary")
    assert res_s.status_code == 200
    assert res_s.json()["dataset_id"] == dataset_id

    # 2. Entities
    res_e = client.get(f"/api/v1/clustering/{dataset_id}/entities?limit=2")
    assert res_e.status_code == 200
    assert len(res_e.json()) <= 2

    # 3. Metadata
    res_m = client.get(f"/api/v1/clustering/{dataset_id}/metadata")
    assert res_m.status_code == 200
    assert res_m.json()["dataset_id"] == dataset_id
    assert "features_used" in res_m.json()
