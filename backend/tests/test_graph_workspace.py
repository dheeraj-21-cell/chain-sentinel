import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_active_dataset() -> str:
    response = client.get("/api/v1/datasets")
    if response.status_code == 200 and response.json():
        for d in response.json():
            if "showcase" in d.get("original_filename", "").lower():
                return d["dataset_id"]
        return response.json()[0]["dataset_id"]
    return "87c747ba-76c6-4428-b6c7-6d3001670788"


NON_EXISTENT_DATASET = "00000000-0000-0000-0000-000000000000"


def test_get_graph_elements_dataset_not_found():
    """Verify 404 is returned when querying elements for a non-existent dataset."""
    response = client.get(f"/api/v1/graph/{NON_EXISTENT_DATASET}/elements")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_graph_elements_valid_dataset():
    """Verify bounded graph elements are returned with multi-pipeline enrichment."""
    active_id = get_active_dataset()
    response = client.get(f"/api/v1/graph/{active_id}/elements?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == active_id
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0
    assert data["total_dataset_nodes"] >= 10
    assert data["total_dataset_edges"] >= 10
    assert "message" in data

    # Verify node structure and enrichment
    sample_node = data["nodes"][0]
    assert "id" in sample_node
    assert "label" in sample_node
    assert "canonical_id" in sample_node
    assert "properties" in sample_node
    assert "risk_priority" in sample_node
    assert "behavior_findings_count" in sample_node

    # Verify edge structure
    sample_edge = data["edges"][0]
    assert "id" in sample_edge
    assert "source" in sample_edge
    assert "target" in sample_edge
    assert "type" in sample_edge


def test_get_graph_elements_bounded_limits():
    """Verify limit parameter properly caps the initial node query."""
    active_id = get_active_dataset()
    res_small = client.get(f"/api/v1/graph/{active_id}/elements?limit=2")
    res_larger = client.get(f"/api/v1/graph/{active_id}/elements?limit=15")
    assert res_small.status_code == 200
    assert res_larger.status_code == 200
    assert len(res_small.json()["nodes"]) <= len(res_larger.json()["nodes"])


def test_neighborhood_expansion_1_and_2_hops():
    """Verify 1-hop and 2-hop neighborhood expansion from a real wallet node."""
    active_id = get_active_dataset()
    res_elem = client.get(f"/api/v1/graph/{active_id}/elements?limit=5")
    assert res_elem.status_code == 200
    nodes = res_elem.json()["nodes"]
    wallet_nodes = [n for n in nodes if n["label"] == "Wallet"]
    assert len(wallet_nodes) > 0
    target_addr = wallet_nodes[0]["canonical_id"]

    # 1 hop
    res_hop1 = client.get(f"/api/v1/graph/{active_id}/neighborhood?node_id={target_addr}&hops=1")
    assert res_hop1.status_code == 200
    data_hop1 = res_hop1.json()
    assert len(data_hop1["nodes"]) >= 2  # target wallet + at least 1 tx
    assert len(data_hop1["edges"]) >= 1
    assert "expanded 1 hop" in data_hop1["message"].lower()

    # 2 hops
    res_hop2 = client.get(f"/api/v1/graph/{active_id}/neighborhood?node_id={target_addr}&hops=2")
    assert res_hop2.status_code == 200
    data_hop2 = res_hop2.json()
    assert len(data_hop2["nodes"]) >= len(data_hop1["nodes"])
    assert len(data_hop2["edges"]) >= len(data_hop1["edges"])


def test_neighborhood_expansion_invalid_node():
    """Verify empty result with informative message when entity does not exist."""
    active_id = get_active_dataset()
    res = client.get(f"/api/v1/graph/{active_id}/neighborhood?node_id=1FakeAddressThatDoesNotExist999999&hops=1")
    assert res.status_code == 200
    data = res.json()
    assert len(data["nodes"]) == 0
    assert len(data["edges"]) == 0
    assert "not found" in data["message"].lower()


def test_dataset_isolation_in_graph_elements():
    """Verify graph elements strictly belong to the specified dataset_id."""
    active_id = get_active_dataset()
    res = client.get(f"/api/v1/graph/{active_id}/elements?limit=25")
    assert res.status_code == 200
    data = res.json()
    for node in data["nodes"]:
        if "dataset_id" in node["properties"]:
            assert node["properties"]["dataset_id"] == active_id
    for edge in data["edges"]:
        if "dataset_id" in edge["properties"]:
            assert edge["properties"]["dataset_id"] == active_id


def test_read_only_data_integrity():
    """Verify that calling elements and neighborhood endpoints does not alter Neo4j counts."""
    active_id = get_active_dataset()
    res_summary_before = client.get(f"/api/v1/graph/{active_id}/summary")
    assert res_summary_before.status_code == 200
    before_nodes = res_summary_before.json()["total_nodes"]
    before_rels = res_summary_before.json()["total_relationships"]

    res_elem = client.get(f"/api/v1/graph/{active_id}/elements?limit=5")
    assert res_elem.status_code == 200
    target_addr = res_elem.json()["nodes"][0]["canonical_id"]

    # Perform multiple reads and expansions
    client.get(f"/api/v1/graph/{active_id}/elements?limit=50")
    client.get(f"/api/v1/graph/{active_id}/neighborhood?node_id={target_addr}&hops=2")

    res_summary_after = client.get(f"/api/v1/graph/{active_id}/summary")
    assert res_summary_after.status_code == 200
    after_nodes = res_summary_after.json()["total_nodes"]
    after_rels = res_summary_after.json()["total_relationships"]

    assert before_nodes == after_nodes
    assert before_rels == after_rels

