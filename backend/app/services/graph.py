import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from neo4j import Driver, GraphDatabase
import polars as pl

from app import config
from app.models.graph import (
    GraphBuildResponse,
    GraphElementEdge,
    GraphElementNode,
    GraphElementsResponse,
    GraphSummaryResponse,
)
from app.services.storage import load_metadata

_driver: Optional[Driver] = None


def get_neo4j_driver() -> Driver:
    """Obtain or initialize singleton Neo4j driver."""
    global _driver
    if _driver is None:
        uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "investigation_secret_change_me")
        _driver = GraphDatabase.driver(uri, auth=(user, password))
    return _driver


def ensure_schema_constraints() -> None:
    """Initialize Neo4j constraints and indexes for dataset-scoped entities."""
    driver = get_neo4j_driver()
    constraints = [
        "CREATE CONSTRAINT c_dataset_id IF NOT EXISTS FOR (d:Dataset) REQUIRE d.dataset_id IS UNIQUE",
        "CREATE CONSTRAINT c_tx_uid IF NOT EXISTS FOR (t:Transaction) REQUIRE t.uid IS UNIQUE",
        "CREATE CONSTRAINT c_wallet_uid IF NOT EXISTS FOR (w:Wallet) REQUIRE w.uid IS UNIQUE",
        "CREATE CONSTRAINT c_ip_uid IF NOT EXISTS FOR (i:IP) REQUIRE i.uid IS UNIQUE",
        "CREATE CONSTRAINT c_asn_uid IF NOT EXISTS FOR (a:ASN) REQUIRE a.uid IS UNIQUE",
        "CREATE CONSTRAINT c_country_uid IF NOT EXISTS FOR (c:Country) REQUIRE c.uid IS UNIQUE",
    ]
    indexes = [
        "CREATE INDEX idx_tx_dataset IF NOT EXISTS FOR (t:Transaction) ON (t.dataset_id)",
        "CREATE INDEX idx_tx_txid IF NOT EXISTS FOR (t:Transaction) ON (t.txid)",
        "CREATE INDEX idx_wallet_dataset IF NOT EXISTS FOR (w:Wallet) ON (w.dataset_id)",
        "CREATE INDEX idx_wallet_address IF NOT EXISTS FOR (w:Wallet) ON (w.address)",
        "CREATE INDEX idx_ip_dataset IF NOT EXISTS FOR (i:IP) ON (i.dataset_id)",
    ]

    with driver.session() as session:
        for query in constraints:
            session.run(query)
        for query in indexes:
            session.run(query)


def build_graph_for_dataset(dataset_id: str) -> GraphBuildResponse:
    """Build or update persistent Neo4j investigation graph strictly for a specific dataset."""
    ensure_schema_constraints()

    metadata = load_metadata(dataset_id)
    if not metadata:
        raise FileNotFoundError(f"Dataset metadata not found for ID '{dataset_id}'.")

    parquet_path = config.PROCESSED_DATA_DIR / dataset_id / "normalized.parquet"
    if not parquet_path.is_file():
        raise FileNotFoundError(f"Normalized Parquet table not found for dataset '{dataset_id}'.")

    df = pl.read_parquet(parquet_path)
    if len(df) == 0:
        return GraphBuildResponse(
            dataset_id=dataset_id,
            status="SUCCESS",
            message="Dataset contains 0 valid records; no graph entities created.",
        )

    driver = get_neo4j_driver()

    tx_nodes: List[Dict[str, Any]] = []
    input_rels: List[Dict[str, Any]] = []
    output_rels: List[Dict[str, Any]] = []
    network_rels: List[Dict[str, Any]] = []
    ip_nodes: Dict[str, str] = {}
    country_nodes: Dict[str, str] = {}
    asn_nodes: Dict[str, int] = {}

    rows = df.to_dicts()
    for row in rows:
        txid = row.get("txid")
        ts = row.get("timestamp")
        fee = float(row["fee"]) if row.get("fee") is not None else None
        script_type = row.get("script_type")
        src_ip = row.get("src_ip")
        dst_ip = row.get("dst_ip")
        src_port = int(row["src_port"]) if row.get("src_port") is not None else None
        dst_port = int(row["dst_port"]) if row.get("dst_port") is not None else None
        geo_country = row.get("geo_country")
        asn = int(row["asn"]) if row.get("asn") is not None else None

        tx_uid = None
        if txid:
            tx_uid = f"{dataset_id}:{txid}"
            tx_nodes.append({
                "uid": tx_uid,
                "txid": txid,
                "dataset_id": dataset_id,
                "timestamp": ts,
                "fee": fee,
                "script_type": script_type,
            })

            # Inputs
            in_addrs = row.get("input_addresses") or []
            in_amts = row.get("input_amounts") or []
            for pos, addr in enumerate(in_addrs):
                if addr:
                    amt = float(in_amts[pos]) if pos < len(in_amts) and in_amts[pos] is not None else None
                    w_uid = f"{dataset_id}:{addr}"
                    input_rels.append({
                        "tx_uid": tx_uid,
                        "wallet_uid": w_uid,
                        "address": addr,
                        "dataset_id": dataset_id,
                        "amount": amt,
                        "position": pos,
                    })

            # Outputs
            out_addrs = row.get("output_addresses") or []
            out_amts = row.get("output_amounts") or []
            for pos, addr in enumerate(out_addrs):
                if addr:
                    amt = float(out_amts[pos]) if pos < len(out_amts) and out_amts[pos] is not None else None
                    w_uid = f"{dataset_id}:{addr}"
                    output_rels.append({
                        "tx_uid": tx_uid,
                        "wallet_uid": w_uid,
                        "address": addr,
                        "dataset_id": dataset_id,
                        "amount": amt,
                        "position": pos,
                    })

        # Network Telemetry
        if src_ip:
            ip_nodes[f"{dataset_id}:{src_ip}"] = src_ip
            if dst_ip:
                ip_nodes[f"{dataset_id}:{dst_ip}"] = dst_ip
            if geo_country:
                country_nodes[f"{dataset_id}:{geo_country}"] = geo_country
            if asn:
                asn_nodes[f"{dataset_id}:{asn}"] = asn

            network_rels.append({
                "dataset_id": dataset_id,
                "src_ip": src_ip,
                "src_uid": f"{dataset_id}:{src_ip}",
                "dst_ip": dst_ip,
                "dst_uid": f"{dataset_id}:{dst_ip}" if dst_ip else None,
                "src_port": src_port,
                "dst_port": dst_port,
                "tx_uid": tx_uid,
                "timestamp": ts,
                "geo_country": geo_country,
                "country_uid": f"{dataset_id}:{geo_country}" if geo_country else None,
                "asn": asn,
                "asn_uid": f"{dataset_id}:{asn}" if asn else None,
            })

    with driver.session() as session:
        # 1. Dataset root node
        session.run(
            """
            MERGE (d:Dataset {dataset_id: $dataset_id})
            SET d.uid = $dataset_id,
                d.original_filename = $filename,
                d.file_type = $file_type,
                d.ingestion_timestamp = $ingest_time
            """,
            dataset_id=dataset_id,
            filename=metadata.original_filename,
            file_type=metadata.file_type,
            ingest_time=metadata.ingestion_timestamp,
        )

        # 2. Transaction nodes and CONTAINS relations
        if tx_nodes:
            session.run(
                """
                UNWIND $batch AS row
                MERGE (t:Transaction {uid: row.uid})
                SET t.txid = row.txid,
                    t.dataset_id = row.dataset_id,
                    t.timestamp = row.timestamp,
                    t.fee = row.fee,
                    t.script_type = row.script_type
                WITH t, row
                MATCH (d:Dataset {dataset_id: row.dataset_id})
                MERGE (d)-[r:CONTAINS {dataset_id: row.dataset_id}]->(t)
                """,
                batch=tx_nodes,
            )

        # 3. Input Wallets & HAS_INPUT
        if input_rels:
            session.run(
                """
                UNWIND $batch AS row
                MERGE (w:Wallet {uid: row.wallet_uid})
                SET w.address = row.address,
                    w.dataset_id = row.dataset_id
                WITH w, row
                MATCH (t:Transaction {uid: row.tx_uid})
                MERGE (t)-[r:HAS_INPUT {position: row.position}]->(w)
                SET r.dataset_id = row.dataset_id,
                    r.amount = row.amount
                """,
                batch=input_rels,
            )

        # 4. Output Wallets & HAS_OUTPUT
        if output_rels:
            session.run(
                """
                UNWIND $batch AS row
                MERGE (w:Wallet {uid: row.wallet_uid})
                SET w.address = row.address,
                    w.dataset_id = row.dataset_id
                WITH w, row
                MATCH (t:Transaction {uid: row.tx_uid})
                MERGE (t)-[r:HAS_OUTPUT {position: row.position}]->(w)
                SET r.dataset_id = row.dataset_id,
                    r.amount = row.amount
                """,
                batch=output_rels,
            )

        # 5. IP Nodes
        if ip_nodes:
            ip_batch = [{"uid": uid, "address": addr, "dataset_id": dataset_id} for uid, addr in ip_nodes.items()]
            session.run(
                """
                UNWIND $batch AS row
                MERGE (i:IP {uid: row.uid})
                SET i.address = row.address,
                    i.dataset_id = row.dataset_id
                """,
                batch=ip_batch,
            )

        # 6. Country Nodes
        if country_nodes:
            c_batch = [{"uid": uid, "code": code, "dataset_id": dataset_id} for uid, code in country_nodes.items()]
            session.run(
                """
                UNWIND $batch AS row
                MERGE (c:Country {uid: row.uid})
                SET c.code = row.code,
                    c.dataset_id = row.dataset_id
                """,
                batch=c_batch,
            )

        # 7. ASN Nodes
        if asn_nodes:
            asn_batch = [{"uid": uid, "value": val, "dataset_id": dataset_id} for uid, val in asn_nodes.items()]
            session.run(
                """
                UNWIND $batch AS row
                MERGE (a:ASN {uid: row.uid})
                SET a.value = row.value,
                    a.dataset_id = row.dataset_id
                """,
                batch=asn_batch,
            )

        # 8. Network Relationships
        if network_rels:
            session.run(
                """
                UNWIND $batch AS row
                MATCH (src:IP {uid: row.src_uid})
                FOREACH (_ IN CASE WHEN row.tx_uid IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (t:Transaction {uid: row.tx_uid})
                    MERGE (src)-[ot:OBSERVED_TRANSACTION]->(t)
                    SET ot.dataset_id = row.dataset_id,
                        ot.timestamp = row.timestamp,
                        ot.src_port = row.src_port
                )
                FOREACH (_ IN CASE WHEN row.dst_uid IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (dst:IP {uid: row.dst_uid})
                    MERGE (src)-[ct:CONNECTED_TO]->(dst)
                    SET ct.dataset_id = row.dataset_id,
                        ct.timestamp = row.timestamp,
                        ct.src_port = row.src_port,
                        ct.dst_port = row.dst_port
                )
                FOREACH (_ IN CASE WHEN row.country_uid IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (c:Country {uid: row.country_uid})
                    MERGE (src)-[li:LOCATED_IN]->(c)
                    SET li.dataset_id = row.dataset_id
                )
                FOREACH (_ IN CASE WHEN row.asn_uid IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (a:ASN {uid: row.asn_uid})
                    MERGE (src)-[ba:BELONGS_TO]->(a)
                    SET ba.dataset_id = row.dataset_id
                )
                """,
                batch=network_rels,
            )

    summary = get_graph_summary(dataset_id)
    return GraphBuildResponse(
        dataset_id=dataset_id,
        status="SUCCESS",
        transactions_created_or_matched=summary.nodes_by_label.get("Transaction", 0),
        wallets_created_or_matched=summary.nodes_by_label.get("Wallet", 0),
        ips_created_or_matched=summary.nodes_by_label.get("IP", 0),
        asns_created_or_matched=summary.nodes_by_label.get("ASN", 0),
        countries_created_or_matched=summary.nodes_by_label.get("Country", 0),
        relationships_created_or_matched=summary.total_relationships,
        message="Neo4j investigation graph constructed successfully.",
    )


def get_graph_summary(dataset_id: str) -> GraphSummaryResponse:
    """Retrieve actual count of nodes and relationships in Neo4j for a dataset."""
    driver = get_neo4j_driver()
    nodes_by_label: Dict[str, int] = {}
    rels_by_type: Dict[str, int] = {}

    with driver.session() as session:
        # Count nodes by label
        node_res = session.run(
            """
            MATCH (n)
            WHERE n.dataset_id = $dataset_id
            RETURN labels(n)[0] AS label, count(n) AS cnt
            """,
            dataset_id=dataset_id,
        )
        for r in node_res:
            label = r["label"]
            if label:
                nodes_by_label[label] = int(r["cnt"])

        # Count relationships by type
        rel_res = session.run(
            """
            MATCH ()-[r]->()
            WHERE r.dataset_id = $dataset_id
            RETURN type(r) AS rel_type, count(r) AS cnt
            """,
            dataset_id=dataset_id,
        )
        for r in rel_res:
            rtype = r["rel_type"]
            if rtype:
                rels_by_type[rtype] = int(r["cnt"])

    total_nodes = sum(nodes_by_label.values())
    total_rels = sum(rels_by_type.values())

    return GraphSummaryResponse(
        dataset_id=dataset_id,
        total_nodes=total_nodes,
        total_relationships=total_rels,
        nodes_by_label=nodes_by_label,
        relationships_by_type=rels_by_type,
    )


def delete_dataset_graph(dataset_id: str) -> int:
    """Delete all graph entities for a specific dataset (useful for teardown and testing)."""
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run(
            """
            MATCH (n)
            WHERE n.dataset_id = $dataset_id
            DETACH DELETE n
            RETURN count(n) AS deleted
            """,
            dataset_id=dataset_id,
        )
        record = result.single()
        return int(record["deleted"]) if record else 0


def _load_enrichment_maps(dataset_id: str) -> Dict[str, Any]:
    """Load precomputed ML, DBSCAN, behavior, and risk metadata to enrich graph nodes."""
    feat_dir = config.FEATURES_DATA_DIR / dataset_id
    risk_map: Dict[str, Dict[str, Any]] = {}
    cluster_map: Dict[str, int] = {}
    behavior_map: Dict[str, Dict[str, Any]] = {}
    anomaly_map: Dict[str, Dict[str, Any]] = {}

    # Risk scores
    risk_p = feat_dir / "risk_scores.parquet"
    if risk_p.is_file():
        try:
            df_r = pl.read_parquet(risk_p)
            for r in df_r.to_dicts():
                eid = r.get("entity_id")
                if eid:
                    risk_map[eid] = {
                        "score": r.get("score"),
                        "priority": r.get("priority"),
                    }
        except Exception:
            pass

    # Wallet clusters
    clu_p = feat_dir / "wallet_clusters.parquet"
    if clu_p.is_file():
        try:
            df_c = pl.read_parquet(clu_p)
            for r in df_c.to_dicts():
                addr = r.get("address")
                if addr:
                    cluster_map[addr] = r.get("cluster_id")
        except Exception:
            pass

    # Behavioral findings
    bhv_p = feat_dir / "behavioral_findings.parquet"
    if bhv_p.is_file():
        try:
            df_b = pl.read_parquet(bhv_p)
            for r in df_b.to_dicts():
                eid = r.get("entity_id")
                dtype = r.get("detection_type")
                if eid:
                    if eid not in behavior_map:
                        behavior_map[eid] = {"count": 0, "types": set()}
                    behavior_map[eid]["count"] += 1
                    if dtype:
                        behavior_map[eid]["types"].add(dtype)
        except Exception:
            pass

    # ML anomalies (wallet & transaction)
    for fname in ["wallet_anomalies.parquet", "transaction_anomalies.parquet"]:
        anom_p = feat_dir / fname
        if anom_p.is_file():
            try:
                df_a = pl.read_parquet(anom_p)
                for r in df_a.to_dicts():
                    eid = r.get("entity_id")
                    if eid:
                        anomaly_map[eid] = {
                            "is_anomaly": bool(r.get("is_anomaly")),
                            "anomaly_score": r.get("anomaly_score"),
                        }
            except Exception:
                pass

    return {
        "risk": risk_map,
        "cluster": cluster_map,
        "behavior": behavior_map,
        "anomaly": anomaly_map,
    }


def _make_node_element(node_dict: Dict[str, Any], label: str, enrich: Dict[str, Any]) -> GraphElementNode:
    uid = node_dict.get("uid") or node_dict.get("dataset_id") or "unknown"
    if label == "Transaction":
        canonical_id = node_dict.get("txid", uid)
    elif label in ("Wallet", "IP"):
        canonical_id = node_dict.get("address", uid)
    elif label == "Country":
        canonical_id = node_dict.get("code", uid)
    elif label == "ASN":
        canonical_id = str(node_dict.get("value", uid))
    elif label == "Dataset":
        canonical_id = node_dict.get("dataset_id", uid)
    else:
        canonical_id = uid

    risk_info = enrich["risk"].get(canonical_id) or enrich["risk"].get(uid)
    clu_id = enrich["cluster"].get(canonical_id)
    bhv_info = enrich["behavior"].get(canonical_id) or enrich["behavior"].get(uid)
    anom_info = enrich["anomaly"].get(canonical_id) or enrich["anomaly"].get(uid)

    return GraphElementNode(
        id=uid,
        label=label,
        canonical_id=canonical_id,
        properties=node_dict,
        ml_anomaly=anom_info,
        cluster_id=clu_id,
        behavior_findings_count=bhv_info["count"] if bhv_info else 0,
        behavior_finding_types=sorted(list(bhv_info["types"])) if bhv_info else [],
        risk_priority=risk_info["priority"] if risk_info else None,
        risk_score=risk_info["score"] if risk_info else None,
    )


def get_graph_elements(
    dataset_id: str,
    limit: int = 100,
    center_node: Optional[str] = None,
    hops: int = 1,
) -> GraphElementsResponse:
    """Retrieve bounded nodes and edges formatted for Cytoscape.js with pipeline enrichment."""
    metadata = load_metadata(dataset_id)
    if not metadata:
        raise FileNotFoundError(f"Dataset with ID '{dataset_id}' not found.")

    summary = get_graph_summary(dataset_id)
    if summary.total_nodes == 0:
        return GraphElementsResponse(
            dataset_id=dataset_id,
            nodes=[],
            edges=[],
            total_dataset_nodes=0,
            total_dataset_edges=0,
            is_bounded=False,
            message="No graph data available for the active dataset.",
        )

    enrich = _load_enrichment_maps(dataset_id)
    driver = get_neo4j_driver()

    nodes_dict: Dict[str, GraphElementNode] = {}
    edges_dict: Dict[str, GraphElementEdge] = {}

    with driver.session() as session:
        if center_node:
            query = """
            MATCH (start {dataset_id: $dataset_id})
            WHERE start.uid = $center_node OR start.address = $center_node OR start.txid = $center_node
            MATCH path = (start)-[r*1..3]-(m {dataset_id: $dataset_id})
            WHERE length(path) <= $hops AND ALL(rel IN relationships(path) WHERE rel.dataset_id = $dataset_id)
            UNWIND nodes(path) AS n
            UNWIND relationships(path) AS rel
            RETURN DISTINCT n, labels(n)[0] AS label, rel, startNode(rel) AS s, endNode(rel) AS t
            LIMIT $limit
            """
            result = session.run(query, dataset_id=dataset_id, center_node=center_node, hops=min(3, max(1, hops)), limit=limit)
        else:
            query = """
            MATCH (t:Transaction {dataset_id: $dataset_id})
            WITH t LIMIT $limit
            OPTIONAL MATCH (t)-[r]-(neighbor {dataset_id: $dataset_id})
            WHERE r.dataset_id = $dataset_id
            RETURN t, labels(t)[0] AS t_label, r, neighbor, labels(neighbor)[0] AS n_label, startNode(r) AS s, endNode(r) AS t_end
            """
            result = session.run(query, dataset_id=dataset_id, limit=limit)

        for rec in result:
            if center_node:
                n = rec.get("n")
                label = rec.get("label") or "Unknown"
                if n:
                    props = dict(n)
                    uid = props.get("uid") or props.get("dataset_id")
                    if uid and uid not in nodes_dict:
                        nodes_dict[uid] = _make_node_element(props, label, enrich)

                rel = rec.get("rel")
                s_node = rec.get("s")
                t_node = rec.get("t")
                if rel and s_node and t_node:
                    s_uid = s_node.get("uid") or s_node.get("dataset_id")
                    t_uid = t_node.get("uid") or t_node.get("dataset_id")
                    if s_uid and t_uid:
                        eid = f"{s_uid}->{rel.type}->{t_uid}"
                        if eid not in edges_dict:
                            edges_dict[eid] = GraphElementEdge(
                                id=eid,
                                source=s_uid,
                                target=t_uid,
                                type=rel.type,
                                properties=dict(rel),
                            )
            else:
                t = rec.get("t")
                t_label = rec.get("t_label") or "Transaction"
                if t:
                    props = dict(t)
                    uid = props.get("uid") or props.get("dataset_id")
                    if uid and uid not in nodes_dict:
                        nodes_dict[uid] = _make_node_element(props, t_label, enrich)

                neighbor = rec.get("neighbor")
                n_label = rec.get("n_label") or "Unknown"
                if neighbor:
                    n_props = dict(neighbor)
                    n_uid = n_props.get("uid") or n_props.get("dataset_id")
                    if n_uid and n_uid not in nodes_dict:
                        nodes_dict[n_uid] = _make_node_element(n_props, n_label, enrich)

                r = rec.get("r")
                s_node = rec.get("s")
                t_end = rec.get("t_end")
                if r and s_node and t_end:
                    s_uid = s_node.get("uid") or s_node.get("dataset_id")
                    t_uid = t_end.get("uid") or t_end.get("dataset_id")
                    if s_uid and t_uid:
                        eid = f"{s_uid}->{r.type}->{t_uid}"
                        if eid not in edges_dict:
                            edges_dict[eid] = GraphElementEdge(
                                id=eid,
                                source=s_uid,
                                target=t_uid,
                                type=r.type,
                                properties=dict(r),
                            )

        # Include connected network infrastructure (Country and ASN) for all loaded IPs
        loaded_ip_uids = [uid for uid, n in nodes_dict.items() if n.label == "IP"]
        if loaded_ip_uids:
            infra_query = """
            MATCH (i:IP {dataset_id: $dataset_id})-[r]->(infra {dataset_id: $dataset_id})
            WHERE i.uid IN $ip_uids AND (infra:Country OR infra:ASN) AND r.dataset_id = $dataset_id
            RETURN i, r, infra, labels(infra)[0] AS infra_label, startNode(r) AS s, endNode(r) AS t_end
            """
            infra_res = session.run(infra_query, dataset_id=dataset_id, ip_uids=loaded_ip_uids)
            for rec in infra_res:
                infra = rec.get("infra")
                infra_label = rec.get("infra_label") or "Unknown"
                if infra:
                    infra_props = dict(infra)
                    i_uid = infra_props.get("uid") or infra_props.get("dataset_id")
                    if i_uid and i_uid not in nodes_dict:
                        nodes_dict[i_uid] = _make_node_element(infra_props, infra_label, enrich)

                r = rec.get("r")
                s_node = rec.get("s")
                t_end = rec.get("t_end")
                if r and s_node and t_end:
                    s_uid = s_node.get("uid") or s_node.get("dataset_id")
                    t_uid = t_end.get("uid") or t_end.get("dataset_id")
                    if s_uid and t_uid:
                        eid = f"{s_uid}->{r.type}->{t_uid}"
                        if eid not in edges_dict:
                            edges_dict[eid] = GraphElementEdge(
                                id=eid,
                                source=s_uid,
                                target=t_uid,
                                type=r.type,
                                properties=dict(r),
                            )

    nodes_list = list(nodes_dict.values())
    edges_list = list(edges_dict.values())
    is_bounded = summary.total_nodes > len(nodes_list)

    msg = None
    if is_bounded:
        msg = f"Showing a bounded investigation neighborhood ({len(nodes_list)} nodes of {summary.total_nodes}). Expand nodes to explore further."

    return GraphElementsResponse(
        dataset_id=dataset_id,
        nodes=nodes_list,
        edges=edges_list,
        total_dataset_nodes=summary.total_nodes,
        total_dataset_edges=summary.total_relationships,
        is_bounded=is_bounded,
        message=msg,
    )


def get_neighborhood(
    dataset_id: str,
    node_id: str,
    hops: int = 1,
    limit: int = 50,
) -> GraphElementsResponse:
    """Expand graph neighborhood 1-3 hops from a specific entity with duplicate safety."""
    metadata = load_metadata(dataset_id)
    if not metadata:
        raise FileNotFoundError(f"Dataset with ID '{dataset_id}' not found.")

    hops = min(3, max(1, hops))
    enrich = _load_enrichment_maps(dataset_id)
    driver = get_neo4j_driver()

    nodes_dict: Dict[str, GraphElementNode] = {}
    edges_dict: Dict[str, GraphElementEdge] = {}

    with driver.session() as session:
        # Locate start node
        start_res = session.run(
            """
            MATCH (start {dataset_id: $dataset_id})
            WHERE start.uid = $node_id OR start.address = $node_id OR start.txid = $node_id OR start.code = $node_id
            RETURN start, labels(start)[0] AS label LIMIT 1
            """,
            dataset_id=dataset_id,
            node_id=node_id,
        )
        start_rec = start_res.single()
        if not start_rec:
            return GraphElementsResponse(
                dataset_id=dataset_id,
                nodes=[],
                edges=[],
                total_dataset_nodes=0,
                total_dataset_edges=0,
                is_bounded=False,
                message=f"Entity '{node_id}' not found in dataset graph.",
            )

        start_props = dict(start_rec["start"])
        start_label = start_rec["label"] or "Unknown"
        s_uid = start_props.get("uid") or start_props.get("dataset_id")
        nodes_dict[s_uid] = _make_node_element(start_props, start_label, enrich)

        # Traverse path up to hops
        path_query = """
        MATCH (start {dataset_id: $dataset_id})
        WHERE start.uid = $s_uid
        MATCH path = (start)-[r*1..3]-(neighbor {dataset_id: $dataset_id})
        WHERE length(path) <= $hops AND ALL(rel IN relationships(path) WHERE rel.dataset_id = $dataset_id)
        UNWIND nodes(path) AS n
        UNWIND relationships(path) AS rel
        RETURN DISTINCT n, labels(n)[0] AS label, rel, startNode(rel) AS s, endNode(rel) AS t
        LIMIT $limit
        """
        path_res = session.run(path_query, dataset_id=dataset_id, s_uid=s_uid, hops=hops, limit=limit)
        for rec in path_res:
            n = rec.get("n")
            label = rec.get("label") or "Unknown"
            if n:
                props = dict(n)
                uid = props.get("uid") or props.get("dataset_id")
                if uid and uid not in nodes_dict:
                    nodes_dict[uid] = _make_node_element(props, label, enrich)

            rel = rec.get("rel")
            s_node = rec.get("s")
            t_node = rec.get("t")
            if rel and s_node and t_node:
                src_uid = s_node.get("uid") or s_node.get("dataset_id")
                dst_uid = t_node.get("uid") or t_node.get("dataset_id")
                if src_uid and dst_uid:
                    eid = f"{src_uid}->{rel.type}->{dst_uid}"
                    if eid not in edges_dict:
                        edges_dict[eid] = GraphElementEdge(
                            id=eid,
                            source=src_uid,
                            target=dst_uid,
                            type=rel.type,
                            properties=dict(rel),
                        )

    summary = get_graph_summary(dataset_id)
    return GraphElementsResponse(
        dataset_id=dataset_id,
        nodes=list(nodes_dict.values()),
        edges=list(edges_dict.values()),
        total_dataset_nodes=summary.total_nodes,
        total_dataset_edges=summary.total_relationships,
        is_bounded=False,
        message=f"Expanded {hops} hop(s) around '{node_id}' ({len(nodes_dict)} nodes, {len(edges_dict)} edges).",
    )


def delete_graph_for_dataset(dataset_id: str) -> Dict[str, int]:
    """Detach and delete all Neo4j nodes and relationships scoped to a dataset."""
    driver = get_neo4j_driver()
    with driver.session() as session:
        res = session.run("MATCH (n) WHERE n.dataset_id = $did DETACH DELETE n", did=dataset_id)
        summary = res.consume()
        nodes_deleted = summary.counters.nodes_deleted
        rels_deleted = summary.counters.relationships_deleted

        res2 = session.run("MATCH (d:Dataset {dataset_id: $did}) DETACH DELETE d", did=dataset_id)
        summary2 = res2.consume()
        d_deleted = summary2.counters.nodes_deleted

        return {
            "nodes_deleted": nodes_deleted + d_deleted,
            "relationships_deleted": rels_deleted,
        }
