from typing import Any, Dict, List, Optional, Tuple
import networkx as nx

from app.models.graph_analysis import (
    ConnectedComponentInfo,
    GraphMetricsSummary,
    PathResult,
    WalletGraphMetrics,
)
from app.services.graph import get_neo4j_driver
from app.services.storage import load_metadata


def load_dataset_networkx_graph(dataset_id: str) -> nx.MultiDiGraph:
    """Extract a dataset-isolated directed multigraph from Neo4j into NetworkX."""
    metadata = load_metadata(dataset_id)
    if not metadata:
        raise FileNotFoundError(f"Dataset with ID '{dataset_id}' not found.")

    driver = get_neo4j_driver()
    G = nx.MultiDiGraph(dataset_id=dataset_id)

    with driver.session() as session:
        # 1. Fetch nodes strictly for this dataset_id
        nodes_query = """
        MATCH (n)
        WHERE n.dataset_id = $dataset_id
        RETURN coalesce(n.uid, n.dataset_id) AS uid, labels(n)[0] AS label, properties(n) AS props
        """
        node_records = session.run(nodes_query, dataset_id=dataset_id)
        for rec in node_records:
            uid = rec["uid"]
            if not uid:
                continue
            label = rec["label"]
            props = rec["props"] or {}

            # Canonical identifier lookup
            if label == "Transaction":
                canonical_id = props.get("txid", uid)
            elif label in ("Wallet", "IP"):
                canonical_id = props.get("address", uid)
            elif label == "Country":
                canonical_id = props.get("code", uid)
            elif label == "ASN":
                canonical_id = str(props.get("value", uid))
            elif label == "Dataset":
                canonical_id = props.get("dataset_id", uid)
            else:
                canonical_id = uid

            G.add_node(
                uid,
                label=label,
                canonical_id=canonical_id,
                **props,
            )

        # 2. Fetch relationships strictly for this dataset_id
        rels_query = """
        MATCH (s)-[r]->(t)
        WHERE r.dataset_id = $dataset_id
        RETURN coalesce(s.uid, s.dataset_id) AS source_uid, coalesce(t.uid, t.dataset_id) AS target_uid, type(r) AS rel_type, properties(r) AS props
        """
        rel_records = session.run(rels_query, dataset_id=dataset_id)
        for rec in rel_records:
            s_uid = rec["source_uid"]
            t_uid = rec["target_uid"]
            rel_type = rec["rel_type"]
            props = rec["props"] or {}

            # Ensure endpoints exist in G
            if s_uid and t_uid and s_uid in G and t_uid in G:
                G.add_edge(
                    s_uid,
                    t_uid,
                    key=rel_type,
                    type=rel_type,
                    **props,
                )

    return G


def get_graph_metrics(dataset_id: str) -> GraphMetricsSummary:
    """Compute NetworkX graph topology metrics and component distributions."""
    G = load_dataset_networkx_graph(dataset_id)
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()

    density = nx.density(G) if n_nodes > 1 else 0.0

    components = list(nx.weakly_connected_components(G))
    comp_count = len(components)
    largest_comp_size = max((len(c) for c in components), default=0)

    nodes_by_type: Dict[str, int] = {}
    for _, data in G.nodes(data=True):
        label = data.get("label", "Unknown")
        nodes_by_type[label] = nodes_by_type.get(label, 0) + 1

    edges_by_type: Dict[str, int] = {}
    for _, _, _, data in G.edges(keys=True, data=True):
        rtype = data.get("type", "Unknown")
        edges_by_type[rtype] = edges_by_type.get(rtype, 0) + 1

    avg_degree = (sum(dict(G.degree()).values()) / n_nodes) if n_nodes > 0 else 0.0

    return GraphMetricsSummary(
        dataset_id=dataset_id,
        node_count=n_nodes,
        edge_count=n_edges,
        density=round(float(density), 6),
        is_directed=True,
        connected_components_count=comp_count,
        largest_component_size=largest_comp_size,
        nodes_by_type=nodes_by_type,
        edges_by_type=edges_by_type,
        average_degree=round(float(avg_degree), 4),
    )


def get_wallet_features(dataset_id: str, limit: int = 50) -> List[WalletGraphMetrics]:
    """Calculate wallet degree, fan-in (funding/received), fan-out (spending/sent), and centralities."""
    G = load_dataset_networkx_graph(dataset_id)
    wallet_nodes = [n for n, d in G.nodes(data=True) if d.get("label") == "Wallet"]
    if not wallet_nodes:
        return []

    # NetworkX centralities
    in_centrality = nx.in_degree_centrality(G)
    out_centrality = nx.out_degree_centrality(G)

    results: List[WalletGraphMetrics] = []
    for w_uid in wallet_nodes:
        data = G.nodes[w_uid]
        address = data.get("canonical_id") or data.get("address") or w_uid

        # In the transaction graph:
        # (:Transaction)-[:HAS_INPUT]->(:Wallet) => Wallet was spent/funded transaction => fan_out
        # (:Transaction)-[:HAS_OUTPUT]->(:Wallet) => Transaction paid to Wallet => fan_in
        in_edges = G.in_edges(w_uid, keys=True, data=True)
        fan_in = 0
        fan_out = 0
        for _, _, _, edge_data in in_edges:
            rel_type = edge_data.get("type")
            if rel_type == "HAS_OUTPUT":
                fan_in += 1
            elif rel_type == "HAS_INPUT":
                fan_out += 1

        total_deg = fan_in + fan_out
        results.append(
            WalletGraphMetrics(
                address=address,
                degree=total_deg,
                fan_in=fan_in,
                fan_out=fan_out,
                in_degree_centrality=round(float(in_centrality.get(w_uid, 0.0)), 6),
                out_degree_centrality=round(float(out_centrality.get(w_uid, 0.0)), 6),
            )
        )

    results.sort(key=lambda w: w.degree, reverse=True)
    return results[:limit]


def get_connected_components(dataset_id: str) -> List[ConnectedComponentInfo]:
    """Segment graph into weakly connected components and return structural summaries."""
    G = load_dataset_networkx_graph(dataset_id)
    raw_components = list(nx.weakly_connected_components(G))
    raw_components.sort(key=len, reverse=True)

    results: List[ConnectedComponentInfo] = []
    for comp_idx, comp_nodes in enumerate(raw_components, start=1):
        subgraph = G.subgraph(comp_nodes)
        node_types: Dict[str, int] = {}
        sample_nodes: List[str] = []

        for node_id in comp_nodes:
            d = G.nodes[node_id]
            lbl = d.get("label", "Unknown")
            node_types[lbl] = node_types.get(lbl, 0) + 1
            if len(sample_nodes) < 6:
                sample_nodes.append(f"{lbl}:{d.get('canonical_id', node_id)}")

        results.append(
            ConnectedComponentInfo(
                component_id=comp_idx,
                node_count=subgraph.number_of_nodes(),
                edge_count=subgraph.number_of_edges(),
                node_types=node_types,
                sample_nodes=sample_nodes,
            )
        )

    return results


def _resolve_node(G: nx.MultiDiGraph, query: str) -> Optional[str]:
    """Find node in NetworkX graph by uid, canonical_id, or raw value."""
    if query in G:
        return query
    for node_id, data in G.nodes(data=True):
        if data.get("canonical_id") == query or data.get("address") == query or data.get("txid") == query:
            return node_id
    return None


def get_shortest_path(dataset_id: str, source: str, target: str) -> PathResult:
    """Find multi-hop investigative path between two nodes in the dataset graph."""
    G = load_dataset_networkx_graph(dataset_id)
    src_node = _resolve_node(G, source)
    tgt_node = _resolve_node(G, target)

    if not src_node or not tgt_node:
        return PathResult(
            source=source,
            target=target,
            path_exists=False,
            length=None,
            node_path=[],
            edge_types=[],
        )

    # Use undirected projection for investigative multi-hop connectivity
    G_undir = G.to_undirected()
    if not nx.has_path(G_undir, src_node, tgt_node):
        return PathResult(
            source=source,
            target=target,
            path_exists=False,
            length=None,
            node_path=[],
            edge_types=[],
        )

    path_nodes = nx.shortest_path(G_undir, src_node, tgt_node)
    canonical_path = [G.nodes[n].get("canonical_id", n) for n in path_nodes]

    # Trace edge types along the path
    edge_types: List[str] = []
    for i in range(len(path_nodes) - 1):
        u, v = path_nodes[i], path_nodes[i + 1]
        # Check forward or backward edge in G
        if G.has_edge(u, v):
            edges = G.get_edge_data(u, v)
            rtype = list(edges.values())[0].get("type", "CONNECTED")
        elif G.has_edge(v, u):
            edges = G.get_edge_data(v, u)
            rtype = f"REVERSE_{list(edges.values())[0].get('type', 'CONNECTED')}"
        else:
            rtype = "CONNECTED"
        edge_types.append(rtype)

    return PathResult(
        source=source,
        target=target,
        path_exists=True,
        length=len(path_nodes) - 1,
        node_path=canonical_path,
        edge_types=edge_types,
    )
