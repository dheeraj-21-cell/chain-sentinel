import io
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


def test_analytics_dataset_summary():
    csv_content = (
        "timestamp,src_ip,dst_ip,src_port,dst_port,txid,input_addresses,input_amounts,output_addresses,output_amounts,fee,script_type,geo_country,asn\n"
        "2026-09-04T10:00:00Z,1.1.1.1,2.2.2.2,8333,8333,tx_01,addr1;addr2,1.0;2.0,addr3,2.99,0.01,p2pkh,US,AS13335\n"
        "2026-09-04T10:15:00Z,3.3.3.3,2.2.2.2,18333,18333,tx_02,addr3,2.0,addr4,1.98,0.02,p2wpkh,CA,AS15169\n"
    )
    ingest_resp = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("analytics_sample.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert ingest_resp.status_code == 201
    dataset_id = ingest_resp.json()["dataset_id"]

    # Query summary
    summary_resp = client.get(f"/api/v1/analytics/{dataset_id}/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()

    assert summary["dataset_id"] == dataset_id
    assert summary["total_records"] == 2
    assert summary["unique_txids"] == 2
    assert summary["unique_wallets"] == 4  # addr1, addr2, addr3, addr4
    assert summary["unique_ips"] == 3      # 1.1.1.1, 2.2.2.2, 3.3.3.3
    assert summary["volume_stats"]["total_input_btc"] == 5.0
    assert summary["volume_stats"]["total_output_btc"] == 4.97
    assert summary["fee_stats"]["total_fee_btc"] == 0.03
    assert summary["fee_stats"]["avg_fee_btc"] == 0.015
    assert summary["fee_stats"]["fee_recorded_count"] == 2
    assert summary["countries"] == {"US": 1, "CA": 1}
    assert summary["asns"] == {"13335": 1, "15169": 1}
    assert summary["ports"] == {"8333": 2, "18333": 2}


def test_wallet_analytics_flow():
    csv_content = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "tx_w1,addrA,5.0,addrB;addrC,3.0;1.99\n"
        "tx_w2,addrB,2.0,addrA,1.99\n"
    )
    ingest_resp = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("wallets.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert ingest_resp.status_code == 201
    dataset_id = ingest_resp.json()["dataset_id"]

    resp = client.get(f"/api/v1/analytics/{dataset_id}/wallets")
    assert resp.status_code == 200
    wallet_list = resp.json()

    wallet_map = {w["address"]: w for w in wallet_list}
    assert "addrA" in wallet_map
    assert "addrB" in wallet_map
    assert "addrC" in wallet_map

    # addrA sent 5.0, received 1.99 -> net_flow = -3.01
    assert wallet_map["addrA"]["total_sent"] == 5.0
    assert wallet_map["addrA"]["total_received"] == 1.99
    assert abs(wallet_map["addrA"]["net_flow"] - (-3.01)) < 1e-6

    # addrB sent 2.0, received 3.0 -> net_flow = 1.0
    assert wallet_map["addrB"]["total_sent"] == 2.0
    assert wallet_map["addrB"]["total_received"] == 3.0
    assert abs(wallet_map["addrB"]["net_flow"] - 1.0) < 1e-6


def test_time_series_analytics():
    csv_content = (
        "timestamp,txid,output_addresses,output_amounts\n"
        "2026-09-04T08:10:00Z,tx_t1,addr1,1.5\n"
        "2026-09-04T08:50:00Z,tx_t2,addr2,2.5\n"
        "2026-09-04T09:15:00Z,tx_t3,addr3,0.5\n"
    )
    ingest_resp = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("timeseries.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    dataset_id = ingest_resp.json()["dataset_id"]

    resp = client.get(f"/api/v1/analytics/{dataset_id}/time-series")
    assert resp.status_code == 200
    buckets = resp.json()
    assert len(buckets) == 2

    # Hour 08:00 has 2 transactions, total volume 4.0
    b08 = [b for b in buckets if "08:00:00Z" in b["timestamp_bucket"]][0]
    assert b08["tx_count"] == 2
    assert b08["volume"] == 4.0

    # Hour 09:00 has 1 transaction, volume 0.5
    b09 = [b for b in buckets if "09:00:00Z" in b["timestamp_bucket"]][0]
    assert b09["tx_count"] == 1
    assert b09["volume"] == 0.5


def test_network_analytics():
    csv_content = (
        "src_ip,dst_ip,src_port,dst_port,geo_country,asn\n"
        "10.0.0.1,10.0.0.2,8333,8333,US,13335\n"
        "10.0.0.1,10.0.0.2,8333,8333,US,13335\n"
        "192.168.1.1,10.0.0.2,18333,8333,DE,24940\n"
    )
    ingest_resp = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("network.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    dataset_id = ingest_resp.json()["dataset_id"]

    resp = client.get(f"/api/v1/analytics/{dataset_id}/network")
    assert resp.status_code == 200
    data = resp.json()
    assert "10.0.0.1" in data["unique_source_ips"]
    assert "192.168.1.1" in data["unique_source_ips"]
    assert "10.0.0.2" in data["unique_destination_ips"]

    obs = data["observations"]
    assert len(obs) == 2
    top_obs = obs[0]
    assert top_obs["src_ip"] == "10.0.0.1"
    assert top_obs["observation_count"] == 2


def test_correlation_records():
    csv_content = (
        "txid,src_ip,dst_ip,input_addresses,input_amounts,output_addresses,output_amounts,fee\n"
        "tx_corr_1,1.1.1.1,2.2.2.2,addr_in,1.0,addr_out,0.99,0.01\n"
    )
    ingest_resp = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("corr.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    dataset_id = ingest_resp.json()["dataset_id"]

    resp = client.get(f"/api/v1/analytics/{dataset_id}/correlations")
    assert resp.status_code == 200
    corrs = resp.json()
    assert len(corrs) == 1
    c = corrs[0]
    assert c["txid"] == "tx_corr_1"
    assert c["src_ip"] == "1.1.1.1"
    assert c["input_addresses"] == ["addr_in"]
    assert c["output_amounts"] == [0.99]
    assert c["fee"] == 0.01


def test_missing_values_in_analytics():
    # Only minimal txid and address; fee and country are null
    csv_content = (
        "txid,input_addresses,input_amounts\n"
        "tx_sparse,addr1,2.5\n"
    )
    ingest_resp = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("sparse.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    dataset_id = ingest_resp.json()["dataset_id"]

    resp = client.get(f"/api/v1/analytics/{dataset_id}/summary")
    assert resp.status_code == 200
    summary = resp.json()

    assert summary["fee_stats"]["fee_recorded_count"] == 0
    assert summary["fee_stats"]["avg_fee_btc"] is None
    assert summary["countries"] == {}
    assert summary["asns"] == {}
    assert summary["volume_stats"]["total_input_btc"] == 2.5
    assert summary["volume_stats"]["total_output_btc"] == 0.0


def test_dataset_isolation_in_analytics():
    csv_a = "txid,src_ip,input_addresses,input_amounts\ntx_alpha,1.1.1.1,addrA,1.0\n"
    csv_b = "txid,src_ip,input_addresses,input_amounts\ntx_beta,2.2.2.2,addrB,2.0\n"

    resp_a = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("a.csv", io.BytesIO(csv_a.encode("utf-8")), "text/csv")},
    )
    resp_b = client.post(
        "/api/v1/datasets/ingest",
        files={"file": ("b.csv", io.BytesIO(csv_b.encode("utf-8")), "text/csv")},
    )
    id_a = resp_a.json()["dataset_id"]
    id_b = resp_b.json()["dataset_id"]

    summary_a = client.get(f"/api/v1/analytics/{id_a}/summary").json()
    summary_b = client.get(f"/api/v1/analytics/{id_b}/summary").json()

    assert summary_a["total_records"] == 1
    assert summary_b["total_records"] == 1
    assert summary_a["unique_ips"] == 1
    assert summary_b["unique_ips"] == 1

    wallets_a = [w["address"] for w in client.get(f"/api/v1/analytics/{id_a}/wallets").json()]
    wallets_b = [w["address"] for w in client.get(f"/api/v1/analytics/{id_b}/wallets").json()]

    assert wallets_a == ["addrA"]
    assert wallets_b == ["addrB"]
    assert "addrB" not in wallets_a
    assert "addrA" not in wallets_b


def test_analytics_not_found():
    resp = client.get("/api/v1/analytics/00000000-0000-0000-0000-000000000000/summary")
    assert resp.status_code == 404
