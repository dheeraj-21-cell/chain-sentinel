import io
import json
from pathlib import Path
import polars as pl
import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    """Ensure all test storage paths operate within an isolated temporary directory."""
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "RAW_DATA_DIR", raw_dir)
    monkeypatch.setattr(config, "PROCESSED_DATA_DIR", processed_dir)
    return tmp_path


client = TestClient(app)


def test_valid_csv_ingestion():
    csv_content = (
        "timestamp,src_ip,dst_ip,src_port,dst_port,txid,input_addresses,input_amounts,output_addresses,output_amounts,fee,script_type,geo_country,asn\n"
        "2026-09-04T10:00:00Z,192.168.1.10,10.0.0.1,8333,8333,tx_hash_001,addr1;addr2,0.5;1.2,out1,1.69,0.01,p2pkh,US,AS13335\n"
    )
    response = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["records_total"] == 1
    assert data["records_valid"] == 1
    assert data["records_rejected"] == 0
    assert data["normalized_output_path"] is not None


def test_valid_json_ingestion():
    json_data = [
        {
            "timestamp": "2026-09-04T11:00:00Z",
            "src_ip": "1.1.1.1",
            "dst_ip": "8.8.8.8",
            "src_port": 18333,
            "dst_port": 18333,
            "txid": "json_tx_001",
            "input_addresses": ["bc1qtest1", "bc1qtest2"],
            "input_amounts": [0.1, 0.4],
            "output_addresses": ["bc1qdest1"],
            "output_amounts": [0.49],
            "fee": 0.01,
            "script_type": "p2wpkh",
            "geo_country": "DE",
            "asn": 15169,
        }
    ]
    json_bytes = json.dumps(json_data).encode("utf-8")
    response = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("test.json", io.BytesIO(json_bytes), "application/json")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["records_total"] == 1
    assert data["records_valid"] == 1
    assert data["records_rejected"] == 0


def test_valid_xml_ingestion():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <transactions>
        <transaction>
            <timestamp>2026-09-04T12:00:00Z</timestamp>
            <src_ip>172.16.0.5</src_ip>
            <dst_ip>172.16.0.6</dst_ip>
            <src_port>8333</src_port>
            <dst_port>8333</dst_port>
            <txid>xml_tx_001</txid>
            <input_addresses>addr_xml_in</input_addresses>
            <input_amounts>2.0</input_amounts>
            <output_addresses>addr_xml_out</output_addresses>
            <output_amounts>1.99</output_amounts>
            <fee>0.01</fee>
            <script_type>p2sh</script_type>
            <geo_country>CA</geo_country>
            <asn>812</asn>
        </transaction>
    </transactions>
    """
    response = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("test.xml", io.BytesIO(xml_content.encode("utf-8")), "application/xml")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["records_total"] == 1
    assert data["records_valid"] == 1
    assert data["records_rejected"] == 0


def test_missing_optional_fields():
    # Only minimal fields present; missing country, ASN, fee, ports, IPs
    csv_content = (
        "txid,input_addresses,input_amounts\n"
        "tx_minimal,addr_min_1,1.5\n"
    )
    response = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("minimal.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["records_valid"] == 1

    # Verify Parquet preserves missing fields as null
    df = pl.read_parquet(data["normalized_output_path"])
    assert df["geo_country"][0] is None
    assert df["asn"][0] is None
    assert df["fee"][0] is None
    assert df["src_ip"][0] is None
    assert df["src_port"][0] is None


def test_invalid_ip_address():
    csv_content = (
        "txid,src_ip\n"
        "tx_bad_ip,999.999.999.999\n"
    )
    response = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("bad_ip.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "FAILED"
    assert data["records_total"] == 1
    assert data["records_valid"] == 0
    assert data["records_rejected"] == 1

    errors_resp = client.get(f"/api/v1/datasets/{data['dataset_id']}/errors")
    errors = errors_resp.json()
    assert len(errors) == 1
    assert any("Invalid source IP" in err for err in errors[0]["errors"])


def test_invalid_port():
    csv_content = (
        "txid,src_port\n"
        "tx_bad_port,70000\n"
    )
    response = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("bad_port.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["records_rejected"] == 1

    errors_resp = client.get(f"/api/v1/datasets/{data['dataset_id']}/errors")
    errors = errors_resp.json()
    assert any("out of valid range" in err for err in errors[0]["errors"])


def test_invalid_numeric_amount():
    csv_content = (
        "txid,input_addresses,input_amounts\n"
        "tx_bad_amt,addr1,one_hundred_btc\n"
    )
    response = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("bad_amt.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["records_rejected"] == 1

    errors_resp = client.get(f"/api/v1/datasets/{data['dataset_id']}/errors")
    errors = errors_resp.json()
    assert any("Invalid numeric value" in err for err in errors[0]["errors"])


def test_malformed_array_fields():
    # Negative amount in array
    csv_content = (
        "txid,input_addresses,input_amounts\n"
        "tx_neg_amt,addr1,-0.5\n"
    )
    response = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("neg_amt.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["records_rejected"] == 1

    errors_resp = client.get(f"/api/v1/datasets/{data['dataset_id']}/errors")
    errors = errors_resp.json()
    assert any("Negative input amount" in err for err in errors[0]["errors"])


def test_inconsistent_array_lengths():
    # 2 input addresses but only 1 input amount
    csv_content = (
        "txid,input_addresses,input_amounts\n"
        "tx_mismatch,addr1;addr2,5.0\n"
    )
    response = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("mismatch.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["records_rejected"] == 1

    errors_resp = client.get(f"/api/v1/datasets/{data['dataset_id']}/errors")
    errors = errors_resp.json()
    assert any("Inconsistent input array lengths" in err for err in errors[0]["errors"])


def test_dataset_id_uniqueness():
    csv_a = "txid\ntx_a\n"
    csv_b = "txid\ntx_b\n"

    resp_a = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("a.csv", io.BytesIO(csv_a.encode("utf-8")), "text/csv")},
    )
    resp_b = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("b.csv", io.BytesIO(csv_b.encode("utf-8")), "text/csv")},
    )
    assert resp_a.status_code == 201
    assert resp_b.status_code == 201
    id_a = resp_a.json()["dataset_id"]
    id_b = resp_b.json()["dataset_id"]
    assert id_a != id_b


def test_raw_file_preservation():
    raw_content = b"txid,fee\ntx_preservation_test,0.0005\n"
    response = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("prov.csv", io.BytesIO(raw_content), "text/csv")},
    )
    assert response.status_code == 201
    dataset_id = response.json()["dataset_id"]

    # Check that the raw file was saved and is byte-identical
    raw_file_path = config.RAW_DATA_DIR / dataset_id / "prov.csv"
    assert raw_file_path.is_file()
    assert raw_file_path.read_bytes() == raw_content


def test_normalized_parquet_creation():
    csv_content = (
        "txid,fee,script_type\n"
        "tx_parquet_test,0.002,p2wpkh\n"
    )
    response = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("parquet.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert response.status_code == 201
    parquet_path = response.json()["normalized_output_path"]
    assert Path(parquet_path).is_file()

    df = pl.read_parquet(parquet_path)
    assert len(df) == 1
    assert df["txid"][0] == "tx_parquet_test"
    assert df["fee"][0] == 0.002
    assert df["script_type"][0] == "p2wpkh"


def test_rejected_record_reporting():
    # Mixed CSV: 1 valid, 1 invalid port
    csv_content = (
        "txid,src_port\n"
        "tx_ok,8333\n"
        "tx_fail,99999\n"
    )
    response = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("mixed.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PARTIAL"
    assert data["records_total"] == 2
    assert data["records_valid"] == 1
    assert data["records_rejected"] == 1

    errors_resp = client.get(f"/api/v1/datasets/{data['dataset_id']}/errors")
    assert errors_resp.status_code == 200
    errors = errors_resp.json()
    assert len(errors) == 1
    assert errors[0]["record_index"] == 1
    assert errors[0]["raw_data"]["txid"] == "tx_fail"


def test_dataset_isolation():
    csv_1 = "txid\ntx_dataset_1\n"
    csv_2 = "txid\ntx_dataset_2\n"

    resp_1 = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("d1.csv", io.BytesIO(csv_1.encode("utf-8")), "text/csv")},
    )
    resp_2 = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("d2.csv", io.BytesIO(csv_2.encode("utf-8")), "text/csv")},
    )
    id_1 = resp_1.json()["dataset_id"]
    id_2 = resp_2.json()["dataset_id"]

    df_1 = pl.read_parquet(resp_1.json()["normalized_output_path"])
    df_2 = pl.read_parquet(resp_2.json()["normalized_output_path"])

    assert all(df_1["dataset_id"] == id_1)
    assert all(df_2["dataset_id"] == id_2)
    assert "tx_dataset_2" not in df_1["txid"].to_list()
    assert "tx_dataset_1" not in df_2["txid"].to_list()
