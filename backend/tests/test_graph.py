import io
import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.services.graph import get_neo4j_driver

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    """Ensure isolated filesystem storage and clean up test graph data after every test."""
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "RAW_DATA_DIR", raw_dir)
    monkeypatch.setattr(config, "PROCESSED_DATA_DIR", processed_dir)

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


def test_empty_neo4j_for_new_dataset(isolated_environment):
    # Verifies Neo4j returns 0 nodes for a non-existent dataset
    summary_resp = client.get("/api/v1/graph/non-existent-dataset-id/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["total_nodes"] == 0
    assert summary["total_relationships"] == 0


def test_build_graph_from_dataset(isolated_environment):
    csv = (
        "timestamp,src_ip,dst_ip,src_port,dst_port,txid,input_addresses,input_amounts,output_addresses,output_amounts,fee,script_type,geo_country,asn\n"
        "2026-09-04T12:00:00Z,10.0.0.1,10.0.0.2,8333,8333,tx_graph_01,addr_in1;addr_in2,1.0;2.0,addr_out1,2.99,0.01,p2pkh,US,13335\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    build_resp = client.post(f"/api/v1/graph/{dataset_id}/build")
    assert build_resp.status_code == 201
    res = build_resp.json()
    assert res["status"] == "SUCCESS"
    assert res["transactions_created_or_matched"] == 1
    assert res["wallets_created_or_matched"] == 3
    assert res["ips_created_or_matched"] == 2
    assert res["countries_created_or_matched"] == 1
    assert res["asns_created_or_matched"] == 1


def test_transaction_node_properties(isolated_environment):
    csv = "timestamp,txid,fee,script_type\n2026-09-04T12:00:00Z,tx_prop_test,0.0005,p2wpkh\n"
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    client.post(f"/api/v1/graph/{dataset_id}/build")

    driver = get_neo4j_driver()
    with driver.session() as session:
        record = session.run(
            "MATCH (t:Transaction {txid: 'tx_prop_test', dataset_id: $d_id}) RETURN t",
            d_id=dataset_id,
        ).single()
        assert record is not None
        node = record["t"]
        assert node["txid"] == "tx_prop_test"
        assert node["fee"] == 0.0005
        assert node["script_type"] == "p2wpkh"
        assert node["timestamp"] == "2026-09-04T12:00:00Z"
        assert node["dataset_id"] == dataset_id


def test_wallet_input_output_relationships(isolated_environment):
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "tx_flow,in_wallet_1;in_wallet_2,1.5;2.5,out_wallet_1,3.99\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    client.post(f"/api/v1/graph/{dataset_id}/build")

    driver = get_neo4j_driver()
    with driver.session() as session:
        # Check input edges
        in_edges = session.run(
            """
            MATCH (t:Transaction {txid: 'tx_flow', dataset_id: $d_id})-[r:HAS_INPUT]->(w:Wallet)
            RETURN w.address AS address, r.amount AS amount, r.position AS pos
            ORDER BY r.position ASC
            """,
            d_id=dataset_id,
        ).data()
        assert len(in_edges) == 2
        assert in_edges[0]["address"] == "in_wallet_1"
        assert in_edges[0]["amount"] == 1.5
        assert in_edges[0]["pos"] == 0
        assert in_edges[1]["address"] == "in_wallet_2"
        assert in_edges[1]["amount"] == 2.5
        assert in_edges[1]["pos"] == 1

        # Check output edge
        out_edges = session.run(
            """
            MATCH (t:Transaction {txid: 'tx_flow', dataset_id: $d_id})-[r:HAS_OUTPUT]->(w:Wallet)
            RETURN w.address AS address, r.amount AS amount, r.position AS pos
            """,
            d_id=dataset_id,
        ).data()
        assert len(out_edges) == 1
        assert out_edges[0]["address"] == "out_wallet_1"
        assert out_edges[0]["amount"] == 3.99
        assert out_edges[0]["pos"] == 0


def test_ip_and_telemetry_relationships(isolated_environment):
    csv = (
        "txid,src_ip,dst_ip,src_port,dst_port,geo_country,asn\n"
        "tx_telemetry,192.168.1.1,10.0.0.1,8333,8333,US,13335\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    client.post(f"/api/v1/graph/{dataset_id}/build")

    driver = get_neo4j_driver()
    with driver.session() as session:
        # Check OBSERVED_TRANSACTION
        obs = session.run(
            """
            MATCH (i:IP {address: '192.168.1.1', dataset_id: $d_id})-[r:OBSERVED_TRANSACTION]->(t:Transaction {txid: 'tx_telemetry'})
            RETURN r.src_port AS port
            """,
            d_id=dataset_id,
        ).single()
        assert obs is not None
        assert obs["port"] == 8333

        # Check CONNECTED_TO
        conn = session.run(
            """
            MATCH (src:IP {address: '192.168.1.1', dataset_id: $d_id})-[r:CONNECTED_TO]->(dst:IP {address: '10.0.0.1'})
            RETURN r.src_port AS sport, r.dst_port AS dport
            """,
            d_id=dataset_id,
        ).single()
        assert conn is not None
        assert conn["sport"] == 8333
        assert conn["dport"] == 8333

        # Check Country and ASN
        country = session.run(
            "MATCH (i:IP {address: '192.168.1.1', dataset_id: $d_id})-[:LOCATED_IN]->(c:Country) RETURN c.code AS code",
            d_id=dataset_id,
        ).single()
        assert country is not None
        assert country["code"] == "US"

        asn = session.run(
            "MATCH (i:IP {address: '192.168.1.1', dataset_id: $d_id})-[:BELONGS_TO]->(a:ASN) RETURN a.value AS asn",
            d_id=dataset_id,
        ).single()
        assert asn is not None
        assert asn["asn"] == 13335


def test_dataset_isolation(isolated_environment):
    # Two datasets sharing identical wallet address string
    csv_a = "txid,output_addresses\ntx_in_A,shared_wallet_address\n"
    csv_b = "txid,output_addresses\ntx_in_B,shared_wallet_address\n"

    id_a = ingest_test_dataset(csv_a, "a.csv")
    id_b = ingest_test_dataset(csv_b, "b.csv")
    isolated_environment.extend([id_a, id_b])

    client.post(f"/api/v1/graph/{id_a}/build")
    client.post(f"/api/v1/graph/{id_b}/build")

    driver = get_neo4j_driver()
    with driver.session() as session:
        # Confirm two distinct Wallet nodes exist
        wallets = session.run(
            "MATCH (w:Wallet {address: 'shared_wallet_address'}) RETURN w.dataset_id AS d_id",
        ).data()
        assert len(wallets) == 2
        d_ids = {w["d_id"] for w in wallets}
        assert id_a in d_ids
        assert id_b in d_ids

        # Confirm NO cross-dataset relationship between tx_in_A and Wallet in dataset B
        cross = session.run(
            """
            MATCH (t:Transaction {txid: 'tx_in_A', dataset_id: $id_a})-[r]->(w:Wallet {dataset_id: $id_b})
            RETURN count(r) AS cross_cnt
            """,
            id_a=id_a,
            id_b=id_b,
        ).single()
        assert cross["cross_cnt"] == 0


def test_missing_optional_fields_handling(isolated_environment):
    csv = "txid,input_addresses\ntx_sparse,addr_only\n"
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    client.post(f"/api/v1/graph/{dataset_id}/build")

    summary = client.get(f"/api/v1/graph/{dataset_id}/summary").json()
    assert summary["nodes_by_label"]["Transaction"] == 1
    assert summary["nodes_by_label"]["Wallet"] == 1
    # Ensure no phantom IP, Country, or ASN nodes were fabricated
    assert "IP" not in summary["nodes_by_label"]
    assert "Country" not in summary["nodes_by_label"]
    assert "ASN" not in summary["nodes_by_label"]


def test_idempotent_repeated_construction(isolated_environment):
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts,src_ip\n"
        "tx_idempotent,in1,1.0,out1,0.99,192.168.1.100\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    # First build
    res1 = client.post(f"/api/v1/graph/{dataset_id}/build").json()
    summary1 = client.get(f"/api/v1/graph/{dataset_id}/summary").json()

    # Second build (re-run)
    res2 = client.post(f"/api/v1/graph/{dataset_id}/build").json()
    summary2 = client.get(f"/api/v1/graph/{dataset_id}/summary").json()

    assert summary1["total_nodes"] == summary2["total_nodes"]
    assert summary1["total_relationships"] == summary2["total_relationships"]
    assert summary1["nodes_by_label"] == summary2["nodes_by_label"]
    assert summary1["relationships_by_type"] == summary2["relationships_by_type"]


def test_delete_graph_endpoint(isolated_environment):
    csv = "txid,output_addresses\ntx_del,del_wallet\n"
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    client.post(f"/api/v1/graph/{dataset_id}/build")
    summary_before = client.get(f"/api/v1/graph/{dataset_id}/summary").json()
    assert summary_before["total_nodes"] > 0

    del_resp = client.delete(f"/api/v1/graph/{dataset_id}")
    assert del_resp.status_code == 200

    summary_after = client.get(f"/api/v1/graph/{dataset_id}/summary").json()
    assert summary_after["total_nodes"] == 0
    assert summary_after["total_relationships"] == 0
