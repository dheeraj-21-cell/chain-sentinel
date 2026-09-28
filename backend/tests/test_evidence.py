import io
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.services.graph import get_neo4j_driver

client = TestClient(app)

SAMPLE_CSV = """timestamp,txid,source_address,destination_address,amount_btc,fee_btc,ip_address,asn,country
2026-03-01T10:00:00Z,tx001,1WalletA11111111111111111111111111,1WalletB22222222222222222222222222,2.5,0.0001,192.168.1.10,13335,US
2026-03-01T10:05:00Z,tx002,1WalletB22222222222222222222222222,1WalletC33333333333333333333333333,2.49,0.0001,192.168.1.20,13335,US
2026-03-01T10:15:00Z,tx003,1WalletC33333333333333333333333333,1WalletD44444444444444444444444444,1.0,0.00005,10.0.0.5,15169,US
2026-03-01T10:20:00Z,tx004,1WalletC33333333333333333333333333,1WalletE55555555555555555555555555,1.48,0.00005,10.0.0.6,15169,US
"""


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    """Ensure isolated filesystem storage and clean up test data and graph nodes."""
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    features_dir = tmp_path / "features"
    models_dir = tmp_path / "models"
    evidence_dir = tmp_path / "evidence"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    features_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "RAW_DATA_DIR", raw_dir)
    monkeypatch.setattr(config, "PROCESSED_DATA_DIR", processed_dir)
    monkeypatch.setattr(config, "FEATURES_DATA_DIR", features_dir)
    monkeypatch.setattr(config, "MODELS_DIR", models_dir)
    monkeypatch.setattr(config, "EVIDENCE_DATA_DIR", evidence_dir)

    test_dataset_ids = []

    yield test_dataset_ids

    driver = get_neo4j_driver()
    with driver.session() as session:
        for d_id in test_dataset_ids:
            session.run("MATCH (n {dataset_id: $d_id}) DETACH DELETE n", d_id=d_id)


def ingest_test_dataset(csv_content: str = SAMPLE_CSV, filename: str = "test.csv") -> str:
    resp = client.post(
        "/api/v1/datasets/ingest",
        files={"file": (filename, io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert resp.status_code == 201
    return resp.json()["dataset_id"]


def test_invalid_dataset_evidence():
    fake_id = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"/api/v1/evidence/{fake_id}/package").status_code == 404
    assert client.post(f"/api/v1/evidence/{fake_id}/report").status_code == 404
    assert client.get(f"/api/v1/evidence/{fake_id}/artifacts/nonexistent/verify").status_code == 404
    assert client.get(f"/api/v1/evidence/{fake_id}/artifacts/nonexistent/download").status_code == 404


def test_evidence_package_generation(isolated_environment):
    d_id = ingest_test_dataset()
    isolated_environment.append(d_id)

    # Generate evidence package
    req_body = {
        "case_reference": "CASE-2026-BTC-001",
        "investigator_name": "Special Agent Smith",
        "notes": "Suspected peeling chain activity observed across 4 hops.",
        "hypothesis": "Funds originate from single source and disperse across rapid transactions.",
        "include_transactions_limit": 50,
    }
    resp = client.post(f"/api/v1/evidence/{d_id}/package", json=req_body)
    assert resp.status_code == 200
    data = resp.json()

    assert data["dataset_id"] == d_id
    assert data["artifact_type"] == "evidence_package"
    assert data["case_reference"] == "CASE-2026-BTC-001"
    assert len(data["sha256_hash"]) == 64
    assert data["file_size_bytes"] > 0

    # Verify JSON structure on disk
    pkg_file = config.EVIDENCE_DATA_DIR / d_id / data["filename"]
    assert pkg_file.is_file()
    with open(pkg_file, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    assert pkg["artifact_id"] == data["artifact_id"]
    assert "provenance" in pkg
    assert "forensic_classification" in pkg
    assert "observed_facts" in pkg
    assert "algorithmic_findings" in pkg
    assert "limitations_and_methodology" in pkg
    assert pkg["investigator_context"]["case_reference"] == "CASE-2026-BTC-001"


def test_forensic_report_pdf_generation(isolated_environment):
    d_id = ingest_test_dataset()
    isolated_environment.append(d_id)

    req_body = {
        "case_reference": "CASE-2026-BTC-002",
        "investigator_name": "Analyst Jane Doe",
        "organization": "Digital Asset Forensics Lab",
        "notes": "Verified offline forensic export test.",
    }
    resp = client.post(f"/api/v1/evidence/{d_id}/report", json=req_body)
    assert resp.status_code == 200
    data = resp.json()

    assert data["dataset_id"] == d_id
    assert data["artifact_type"] == "forensic_report_pdf"
    assert len(data["sha256_hash"]) == 64
    assert data["file_size_bytes"] > 0

    # Verify PDF on disk
    pdf_file = config.EVIDENCE_DATA_DIR / d_id / data["filename"]
    assert pdf_file.is_file()
    with open(pdf_file, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-"


def test_list_artifacts_and_verification(isolated_environment):
    d_id = ingest_test_dataset()
    isolated_environment.append(d_id)

    # Generate both artifacts
    pkg_res = client.post(f"/api/v1/evidence/{d_id}/package").json()
    rep_res = client.post(f"/api/v1/evidence/{d_id}/report").json()

    # List
    list_res = client.get(f"/api/v1/evidence/{d_id}/artifacts")
    assert list_res.status_code == 200
    artifacts = list_res.json()
    assert len(artifacts) >= 2
    artifact_ids = [a["artifact_id"] for a in artifacts]
    assert pkg_res["artifact_id"] in artifact_ids
    assert rep_res["artifact_id"] in artifact_ids

    # Verify Package
    v_pkg = client.get(f"/api/v1/evidence/{d_id}/artifacts/{pkg_res['artifact_id']}/verify")
    assert v_pkg.status_code == 200
    v_data = v_pkg.json()
    assert v_data["is_valid"] is True
    assert v_data["status"] == "verified"
    assert v_data["expected_sha256"] == pkg_res["sha256_hash"]
    assert v_data["computed_sha256"] == pkg_res["sha256_hash"]

    # Verify Report
    v_rep = client.get(f"/api/v1/evidence/{d_id}/artifacts/{rep_res['artifact_id']}/verify")
    assert v_rep.status_code == 200
    assert v_rep.json()["is_valid"] is True
    assert v_rep.json()["status"] == "verified"


def test_tamper_detection(isolated_environment):
    d_id = ingest_test_dataset()
    isolated_environment.append(d_id)

    pkg_res = client.post(f"/api/v1/evidence/{d_id}/package").json()
    pkg_file = config.EVIDENCE_DATA_DIR / d_id / pkg_res["filename"]

    # Tamper with file: append one byte
    with open(pkg_file, "ab") as f:
        f.write(b" ")

    # Verify again -> must detect tampering
    v_res = client.get(f"/api/v1/evidence/{d_id}/artifacts/{pkg_res['artifact_id']}/verify")
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["is_valid"] is False
    assert v_data["status"] == "tampered"
    assert v_data["expected_sha256"] != v_data["computed_sha256"]
    assert "TAMPER ALERT" in v_data["message"]


def test_missing_file_detection(isolated_environment):
    d_id = ingest_test_dataset()
    isolated_environment.append(d_id)

    pkg_res = client.post(f"/api/v1/evidence/{d_id}/package").json()
    pkg_file = config.EVIDENCE_DATA_DIR / d_id / pkg_res["filename"]
    pkg_file.unlink()  # delete from disk

    v_res = client.get(f"/api/v1/evidence/{d_id}/artifacts/{pkg_res['artifact_id']}/verify")
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["is_valid"] is False
    assert v_data["status"] == "missing"
    assert "missing from disk" in v_data["message"]


def test_dataset_isolation(isolated_environment):
    d_id_1 = ingest_test_dataset(SAMPLE_CSV, "dataset1.csv")
    d_id_2 = ingest_test_dataset(SAMPLE_CSV, "dataset2.csv")
    isolated_environment.extend([d_id_1, d_id_2])

    pkg_1 = client.post(f"/api/v1/evidence/{d_id_1}/package").json()

    # Dataset 2 should have no artifacts
    arts_2 = client.get(f"/api/v1/evidence/{d_id_2}/artifacts").json()
    assert len(arts_2) == 0

    # Dataset 2 cannot verify dataset 1's artifact
    assert client.get(f"/api/v1/evidence/{d_id_2}/artifacts/{pkg_1['artifact_id']}/verify").status_code == 404


def test_download_endpoints(isolated_environment):
    d_id = ingest_test_dataset()
    isolated_environment.append(d_id)

    pkg_res = client.post(f"/api/v1/evidence/{d_id}/package").json()
    rep_res = client.post(f"/api/v1/evidence/{d_id}/report").json()

    # Download Package
    d_pkg = client.get(f"/api/v1/evidence/{d_id}/artifacts/{pkg_res['artifact_id']}/download")
    assert d_pkg.status_code == 200
    assert d_pkg.headers["content-type"] == "application/json"
    assert f'filename="{pkg_res["filename"]}"' in d_pkg.headers.get("content-disposition", "")
    assert len(d_pkg.content) > 0

    # Download Report
    d_rep = client.get(f"/api/v1/evidence/{d_id}/artifacts/{rep_res['artifact_id']}/download")
    assert d_rep.status_code == 200
    assert d_rep.headers["content-type"] == "application/pdf"
    assert f'filename="{rep_res["filename"]}"' in d_rep.headers.get("content-disposition", "")
    assert d_rep.content.startswith(b"%PDF-")


def test_incomplete_pipeline_graceful_handling(isolated_environment):
    """Ensure evidence packaging and report generation succeed even before ML/DBSCAN/Graph are run."""
    d_id = ingest_test_dataset()
    isolated_environment.append(d_id)

    pkg = client.post(f"/api/v1/evidence/{d_id}/package").json()
    assert len(pkg["sha256_hash"]) == 64

    rep = client.post(f"/api/v1/evidence/{d_id}/report").json()
    assert len(rep["sha256_hash"]) == 64
