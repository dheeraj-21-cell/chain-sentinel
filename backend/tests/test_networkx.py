import io
import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.services.graph import get_neo4j_driver
from app.services.graph_analysis import load_dataset_networkx_graph

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


def test_invalid_dataset_handling(isolated_environment):
    """Test 404 response when querying NetworkX endpoints for a non-existent dataset."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    res_m = client.get(f"/api/v1/networkx/{fake_id}/metrics")
    assert res_m.status_code == 404

    res_w = client.get(f"/api/v1/networkx/{fake_id}/wallets")
    assert res_w.status_code == 404

    res_c = client.get(f"/api/v1/networkx/{fake_id}/components")
    assert res_c.status_code == 404

    res_p = client.get(f"/api/v1/networkx/{fake_id}/paths?source=a&target=b")
    assert res_p.status_code == 404


def test_empty_dataset_handling(isolated_environment):
    """Test NetworkX analysis when dataset is valid but Neo4j graph has not been built."""
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "tx_unbuilt,addr_in,1.0,addr_out,0.99\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    # Query metrics without building graph
    res_m = client.get(f"/api/v1/networkx/{dataset_id}/metrics")
    assert res_m.status_code == 200
    metrics = res_m.json()
    assert metrics["node_count"] == 0
    assert metrics["edge_count"] == 0
    assert metrics["density"] == 0.0
    assert metrics["connected_components_count"] == 0
    assert metrics["largest_component_size"] == 0

    res_w = client.get(f"/api/v1/networkx/{dataset_id}/wallets")
    assert res_w.status_code == 200
    assert res_w.json() == []

    res_c = client.get(f"/api/v1/networkx/{dataset_id}/components")
    assert res_c.status_code == 200
    assert res_c.json() == []

    res_p = client.get(f"/api/v1/networkx/{dataset_id}/paths?source=addr_in&target=addr_out")
    assert res_p.status_code == 200
    path = res_p.json()
    assert path["path_exists"] is False


def test_networkx_graph_construction(isolated_environment):
    """Test loading Neo4j graph into NetworkX MultiDiGraph with correct nodes, edges and types."""
    csv = (
        "timestamp,src_ip,dst_ip,src_port,dst_port,txid,input_addresses,input_amounts,output_addresses,output_amounts,fee,script_type,geo_country,asn\n"
        "2026-09-04T12:00:00Z,10.0.0.1,10.0.0.2,8333,8333,tx_nx_01,in_addr1;in_addr2,2.0;3.0,out_addr1,4.99,0.01,p2pkh,US,13335\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)

    # Build Neo4j graph
    b_resp = client.post(f"/api/v1/graph/{dataset_id}/build")
    assert b_resp.status_code == 201

    # Load in-memory NetworkX graph
    G = load_dataset_networkx_graph(dataset_id)
    assert G.graph["dataset_id"] == dataset_id
    assert G.is_directed()

    # Verify nodes
    # Expected: 1 Transaction, 3 Wallets (2 in, 1 out), 2 IPs, 1 Country, 1 ASN, 1 Dataset = 9 nodes
    assert G.number_of_nodes() == 9
    labels = {data.get("label") for _, data in G.nodes(data=True)}
    assert labels == {"Dataset", "Transaction", "Wallet", "IP", "Country", "ASN"}

    # Verify edges
    # Expected: 2 HAS_INPUT, 1 HAS_OUTPUT, 1 OBSERVED_TRANSACTION, 1 CONNECTED_TO, 1 LOCATED_IN, 1 BELONGS_TO, 1 CONTAINS = 8 edges
    assert G.number_of_edges() == 8


def test_dataset_isolation_in_networkx(isolated_environment):
    """Ensure two separate datasets sharing identical wallet addresses and txids remain completely isolated in NetworkX."""
    csv1 = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "shared_tx,shared_addr_1,1.0,shared_addr_2,0.99\n"
    )
    csv2 = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "shared_tx,shared_addr_1,5.0,shared_addr_3,4.99\n"
    )

    d1 = ingest_test_dataset(csv1, "d1.csv")
    d2 = ingest_test_dataset(csv2, "d2.csv")
    isolated_environment.extend([d1, d2])

    client.post(f"/api/v1/graph/{d1}/build")
    client.post(f"/api/v1/graph/{d2}/build")

    # Load both graphs into NetworkX
    G1 = load_dataset_networkx_graph(d1)
    G2 = load_dataset_networkx_graph(d2)

    # G1 must have shared_addr_2 and NOT shared_addr_3
    canonical_nodes_1 = {d.get("canonical_id") for _, d in G1.nodes(data=True)}
    assert "shared_addr_1" in canonical_nodes_1
    assert "shared_addr_2" in canonical_nodes_1
    assert "shared_addr_3" not in canonical_nodes_1

    # G2 must have shared_addr_3 and NOT shared_addr_2
    canonical_nodes_2 = {d.get("canonical_id") for _, d in G2.nodes(data=True)}
    assert "shared_addr_1" in canonical_nodes_2
    assert "shared_addr_3" in canonical_nodes_2
    assert "shared_addr_2" not in canonical_nodes_2

    # Verify no edge or node uids leak across graphs
    for n in G1.nodes():
        assert n.startswith(d1)
    for n in G2.nodes():
        assert n.startswith(d2)


def test_graph_metrics_calculation(isolated_environment):
    """Test /metrics endpoint returns correct topological metrics."""
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "tx_metrics,in_w,1.0,out_w,0.99\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)
    client.post(f"/api/v1/graph/{dataset_id}/build")

    res = client.get(f"/api/v1/networkx/{dataset_id}/metrics")
    assert res.status_code == 200
    data = res.json()

    # 1 Dataset, 1 Transaction, 2 Wallets = 4 nodes
    assert data["node_count"] == 4
    # 1 CONTAINS (Dataset->Tx), 1 HAS_INPUT (Tx->in_w), 1 HAS_OUTPUT (Tx->out_w) = 3 edges
    assert data["edge_count"] == 3
    assert data["density"] > 0.0
    assert data["connected_components_count"] == 1
    assert data["largest_component_size"] == 4
    assert data["nodes_by_type"]["Transaction"] == 1
    assert data["nodes_by_type"]["Wallet"] == 2
    assert data["edges_by_type"]["HAS_INPUT"] == 1
    assert data["edges_by_type"]["HAS_OUTPUT"] == 1


def test_wallet_fan_in_and_fan_out(isolated_environment):
    """Test wallet fan-in (received payments) and fan-out (spent transactions)."""
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "tx_spend_1,W_HUB,1.0,W_RECV_1,0.99\n"
        "tx_spend_2,W_HUB,2.0,W_RECV_2,1.99\n"
        "tx_fund_hub,W_FUND,3.0,W_HUB,2.99\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)
    client.post(f"/api/v1/graph/{dataset_id}/build")

    res = client.get(f"/api/v1/networkx/{dataset_id}/wallets")
    assert res.status_code == 200
    wallets = res.json()

    # Find W_HUB
    hub = next((w for w in wallets if w["address"] == "W_HUB"), None)
    assert hub is not None
    assert hub["fan_out"] == 2  # Spent in 2 transactions
    assert hub["fan_in"] == 1   # Received output in 1 transaction
    assert hub["degree"] == 3

    # Find W_FUND (only spent)
    fund = next((w for w in wallets if w["address"] == "W_FUND"), None)
    assert fund is not None
    assert fund["fan_out"] == 1
    assert fund["fan_in"] == 0

    # Find W_RECV_1 (only received)
    recv1 = next((w for w in wallets if w["address"] == "W_RECV_1"), None)
    assert recv1 is not None
    assert recv1["fan_in"] == 1
    assert recv1["fan_out"] == 0


def test_connected_components(isolated_environment):
    """Test segmentation of disconnected transaction groups into components."""
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "tx_cluster_1,c1_in,1.0,c1_out,0.99\n"
        "tx_cluster_2,c2_in,2.0,c2_out,1.99\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)
    client.post(f"/api/v1/graph/{dataset_id}/build")

    res = client.get(f"/api/v1/networkx/{dataset_id}/components")
    assert res.status_code == 200
    components = res.json()

    assert len(components) >= 1
    largest = components[0]
    assert largest["node_count"] > 0
    assert largest["edge_count"] > 0
    assert "Transaction" in largest["node_types"]
    assert "Wallet" in largest["node_types"]
    assert len(largest["sample_nodes"]) > 0


def test_shortest_path_existing_and_missing(isolated_environment):
    """Test finding multi-hop investigative path between nodes."""
    csv = (
        "txid,input_addresses,input_amounts,output_addresses,output_amounts\n"
        "tx_hop,sender_wallet,1.0,receiver_wallet,0.99\n"
    )
    dataset_id = ingest_test_dataset(csv)
    isolated_environment.append(dataset_id)
    client.post(f"/api/v1/graph/{dataset_id}/build")

    # 1. Existing path: sender_wallet -> tx_hop -> receiver_wallet
    res_path = client.get(
        f"/api/v1/networkx/{dataset_id}/paths?source=sender_wallet&target=receiver_wallet"
    )
    assert res_path.status_code == 200
    path = res_path.json()
    assert path["path_exists"] is True
    assert path["length"] == 2
    assert path["node_path"] == ["sender_wallet", "tx_hop", "receiver_wallet"]
    assert len(path["edge_types"]) == 2

    # 2. Non-existent node in graph
    res_missing = client.get(
        f"/api/v1/networkx/{dataset_id}/paths?source=sender_wallet&target=unknown_wallet"
    )
    assert res_missing.status_code == 200
    assert res_missing.json()["path_exists"] is False
