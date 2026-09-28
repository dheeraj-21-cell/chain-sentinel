import io
import json
import pytest
import joblib
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
    """Test 404 response when querying ML endpoints for a non-existent dataset."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    res_f = client.post(f"/api/v1/ml/{fake_id}/features/generate")
    assert res_f.status_code == 404

    res_t = client.post(f"/api/v1/ml/{fake_id}/train")
    assert res_t.status_code == 404

    res_a = client.get(f"/api/v1/ml/{fake_id}/anomalies")
    assert res_a.status_code == 404

    res_m = client.get(f"/api/v1/ml/{fake_id}/metadata")
    assert res_m.status_code == 404


def test_feature_generation_transaction(isolated_environment):
    """Verify transaction feature extraction schema, calculations, and persistence."""
    csv = (
        "timestamp,src_ip,dst_ip,src_port,dst_port,txid,input_addresses,input_amounts,output_addresses,output_amounts,fee,script_type,geo_country,asn\n"
        "2026-09-04T12:00:00Z,10.0.0.1,10.0.0.2,8333,8333,tx_feat_01,in1;in2,1.5;2.5,out1,3.99,0.01,p2pkh,US,13335\n"
        "2026-09-04T12:05:00Z,10.0.0.3,10.0.0.4,8333,8333,tx_feat_02,in3,5.0,out2;out3,2.0;2.99,0.01,p2wpkh,DE,24940\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)
    client.post(f"/api/v1/graph/{dataset_id}/build")

    res = client.post(f"/api/v1/ml/{dataset_id}/features/generate?entity_type=transaction")
    assert res.status_code == 201
    data = res.json()

    assert data["dataset_id"] == dataset_id
    assert data["entity_type"] == "transaction"
    assert data["record_count"] == 2
    assert data["feature_count"] == 18
    assert "total_output_amount" in data["feature_names"]
    assert "fee" in data["feature_names"]
    assert "network_peer_degree" in data["feature_names"]


def test_feature_generation_wallet(isolated_environment):
    """Verify wallet feature extraction schema and graph flow calculations."""
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "tx_w1,w_sender,2.0,w_receiver,1.99\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)
    client.post(f"/api/v1/graph/{dataset_id}/build")

    res = client.post(f"/api/v1/ml/{dataset_id}/features/generate?entity_type=wallet")
    assert res.status_code == 201
    data = res.json()

    assert data["dataset_id"] == dataset_id
    assert data["entity_type"] == "wallet"
    assert data["record_count"] == 2  # w_sender and w_receiver
    assert "total_sent_btc" in data["feature_names"]
    assert "total_received_btc" in data["feature_names"]
    assert "fan_in" in data["feature_names"]
    assert "fan_out" in data["feature_names"]


def test_missing_value_handling(isolated_environment):
    """Verify missing fees, telemetry, and amounts are deterministically imputed with indicator flags."""
    csv = (
        "txid,input_addresses,output_addresses\n"
        "tx_missing,in_addr,out_addr\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    res = client.post(f"/api/v1/ml/{dataset_id}/features/generate?entity_type=transaction")
    assert res.status_code == 201
    data = res.json()
    assert "fee" in data["imputed_fields"]
    assert "fee_ratio" in data["imputed_fields"]

    # Check training and scoring with missing values
    train_res = client.post(f"/api/v1/ml/{dataset_id}/train")
    assert train_res.status_code == 200
    res_data = train_res.json()
    assert res_data["total_entities"] == 1
    item = res_data["anomalies"][0]
    assert item["features"]["fee"] == 0.0
    assert item["features"]["has_fee"] == 0.0
    assert item["features"]["has_ip"] == 0.0


def test_dataset_isolation_in_ml(isolated_environment):
    """Ensure models and feature datasets for different dataset_ids remain completely isolated."""
    csv1 = "txid,input_addresses,input_amounts,output_addresses,output_amounts\ntx_d1,addr1,1.0,addr2,0.99\n"
    csv2 = "txid,input_addresses,input_amounts,output_addresses,output_amounts\ntx_d2,addr3,2.0,addr4,1.99\n"

    d1 = ingest_test_dataset(csv1, "d1.csv")
    d2 = ingest_test_dataset(csv2, "d2.csv")
    isolated_environment.extend([d1, d2])

    res1 = client.post(f"/api/v1/ml/{d1}/train")
    assert res1.status_code == 200

    res2 = client.post(f"/api/v1/ml/{d2}/train")
    assert res2.status_code == 200

    d1_entities = {a["entity_id"] for a in res1.json()["anomalies"]}
    d2_entities = {a["entity_id"] for a in res2.json()["anomalies"]}

    assert "tx_d1" in d1_entities
    assert "tx_d2" not in d1_entities

    assert "tx_d2" in d2_entities
    assert "tx_d1" not in d2_entities


def test_deterministic_reproducibility(isolated_environment):
    """Ensure repeated training with explicit random_state produces identical anomaly scores."""
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts,fee\n"
        "tx_1,w1,1.0,w2,0.99,0.01\n"
        "tx_2,w2,0.99,w3,0.98,0.01\n"
        "tx_3,w3,0.98,w4,0.97,0.01\n"
        "tx_4,w4,0.97,w5,0.96,0.01\n"
        "tx_5,w_whale,100.0,w_mule1;w_mule2,50.0;49.9,0.1\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    res1 = client.post(f"/api/v1/ml/{dataset_id}/train?random_state=42&n_estimators=100")
    res2 = client.post(f"/api/v1/ml/{dataset_id}/train?random_state=42&n_estimators=100")

    assert res1.status_code == 200
    assert res2.status_code == 200

    items1 = res1.json()["anomalies"]
    items2 = res2.json()["anomalies"]

    assert len(items1) == len(items2)
    for i in range(len(items1)):
        assert items1[i]["entity_id"] == items2[i]["entity_id"]
        assert items1[i]["raw_score"] == items2[i]["raw_score"]
        assert items1[i]["anomaly_score"] == items2[i]["anomaly_score"]
        assert items1[i]["anomaly_label"] == items2[i]["anomaly_label"]


def test_isolation_forest_training_and_inference(isolated_environment):
    """Verify Isolation Forest flags significant transactional deviations as anomalous leads."""
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts,fee\n"
        "tx_norm_1,w1,0.1,w2,0.09,0.01\n"
        "tx_norm_2,w2,0.1,w3,0.09,0.01\n"
        "tx_norm_3,w3,0.1,w4,0.09,0.01\n"
        "tx_norm_4,w4,0.1,w5,0.09,0.01\n"
        "tx_norm_5,w5,0.1,w6,0.09,0.01\n"
        "tx_norm_6,w6,0.1,w7,0.09,0.01\n"
        "tx_norm_7,w7,0.1,w8,0.09,0.01\n"
        "tx_norm_8,w8,0.1,w9,0.09,0.01\n"
        "tx_outlier,w_in1;w_in2;w_in3;w_in4;w_in5,10.0;10.0;10.0;10.0;10.0,w_out1;w_out2;w_out3;w_out4,12.0;12.0;12.0;13.9,0.1\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    res = client.post(f"/api/v1/ml/{dataset_id}/train?contamination=0.15&random_state=42")
    assert res.status_code == 200
    data = res.json()

    assert data["total_entities"] == 9
    assert data["anomaly_count"] >= 1

    # Outlier transaction must be flagged as an anomalous lead
    top_lead = data["anomalies"][0]
    assert top_lead["entity_id"] == "tx_outlier"
    assert top_lead["is_anomaly"] is True
    assert top_lead["anomaly_label"] == -1
    assert top_lead["anomaly_score"] > 0.5


def test_neutral_explainability(isolated_environment):
    """Verify explainability requirement: use neutral forensic terms; strictly avoid criminal labels."""
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts,fee\n"
        "tx_1,w1,1.0,w2,0.99,0.01\n"
        "tx_2,w2,1.0,w3,0.99,0.01\n"
        "tx_extreme,w1,1000.0,w2,999.0,1.0\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    res = client.post(f"/api/v1/ml/{dataset_id}/train?contamination=0.33")
    assert res.status_code == 200
    data = res.json()

    prohibited_words = ["criminal", "malicious", "ransomware", "laundering", "illegal", "fraud"]

    for anom in data["anomalies"]:
        for expl in anom["explanation"]:
            text_lower = expl.lower()
            for bad_word in prohibited_words:
                assert bad_word not in text_lower, f"Prohibited word '{bad_word}' found in explanation: '{expl}'"


def test_model_artifact_persistence(isolated_environment):
    """Verify serialized .joblib model and metadata JSON are saved on the filesystem."""
    csv = "txid,input_addresses,input_amounts,output_addresses,output_amounts\ntx_art_1,a1,1.0,a2,0.99\ntx_art_2,a2,2.0,a3,1.99\n"
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    client.post(f"/api/v1/ml/{dataset_id}/train")

    model_file = config.MODELS_DIR / dataset_id / "isolation_forest_transaction.joblib"
    assert model_file.is_file()
    # Verify model is loadable with joblib
    loaded_model = joblib.load(model_file)
    assert hasattr(loaded_model, "decision_function")

    meta_file = config.MODELS_DIR / dataset_id / "metadata_transaction.json"
    assert meta_file.is_file()
    with open(meta_file, "r") as f:
        meta_json = json.load(f)
    assert meta_json["model_name"] == "scikit-learn IsolationForest"
    assert meta_json["training_samples"] == 2


def test_api_endpoints(isolated_environment):
    """Test /anomalies and /metadata retrieval endpoints."""
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "tx_api_1,a1,1.0,a2,0.99\n"
        "tx_api_2,a2,2.0,a3,1.99\n"
        "tx_api_3,a3,3.0,a4,2.99\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    # 1. Train model
    client.post(f"/api/v1/ml/{dataset_id}/train")

    # 2. Query /anomalies
    res_anom = client.get(f"/api/v1/ml/{dataset_id}/anomalies?limit=2")
    assert res_anom.status_code == 200
    assert len(res_anom.json()["anomalies"]) <= 2

    # 3. Query /metadata
    res_meta = client.get(f"/api/v1/ml/{dataset_id}/metadata")
    assert res_meta.status_code == 200
    meta = res_meta.json()
    assert meta["dataset_id"] == dataset_id
    assert meta["training_samples"] == 3


def test_empty_dataset_handling(isolated_environment):
    """Verify ML anomaly detection handles datasets with 0 valid records gracefully."""
    # A CSV with header only (0 valid records)
    csv = "txid,input_addresses,output_addresses\n"
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    res_feat = client.post(f"/api/v1/ml/{dataset_id}/features/generate")
    assert res_feat.status_code == 201
    assert res_feat.json()["record_count"] == 0

    res_train = client.post(f"/api/v1/ml/{dataset_id}/train")
    assert res_train.status_code == 200
    data = res_train.json()
    assert data["total_entities"] == 0
    assert data["anomaly_count"] == 0
    assert data["anomalies"] == []


def test_small_dataset_single_transaction(isolated_environment):
    """Verify Isolation Forest handles a single-record dataset deterministically without error."""
    csv = "txid,input_addresses,input_amounts,output_addresses,output_amounts\ntx_single,w1,1.0,w2,0.99\n"
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    res_train = client.post(f"/api/v1/ml/{dataset_id}/train")
    assert res_train.status_code == 200
    data = res_train.json()
    assert data["total_entities"] == 1
    assert len(data["anomalies"]) == 1
    item = data["anomalies"][0]
    assert item["entity_id"] == "tx_single"
    assert item["anomaly_score"] == 0.5

