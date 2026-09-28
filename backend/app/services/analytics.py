from pathlib import Path
from typing import Any, Dict, List, Optional
import duckdb

from app import config
from app.models.analytics import (
    CorrelationRecord,
    DatasetAnalyticsSummary,
    FeeStats,
    NetworkObservation,
    TimeSeriesBucket,
    VolumeStats,
    WalletActivity,
)


def _get_parquet_path(dataset_id: str) -> str:
    """Resolve and validate path to normalized Parquet file for a dataset."""
    parquet_path = config.PROCESSED_DATA_DIR / dataset_id / "normalized.parquet"
    if not parquet_path.is_file():
        raise FileNotFoundError(f"Normalized Parquet file not found for dataset '{dataset_id}'.")
    return str(parquet_path).replace("\\", "/")


def get_dataset_summary(dataset_id: str) -> DatasetAnalyticsSummary:
    """Compute aggregate analytical statistics over a normalized dataset using DuckDB."""
    parquet_path = _get_parquet_path(dataset_id)
    conn = duckdb.connect()

    # 1. Base counts and timestamps
    base_query = """
    SELECT
        count(*) AS total_records,
        count(distinct txid) AS unique_txids,
        min(timestamp) AS earliest_timestamp,
        max(timestamp) AS latest_timestamp
    FROM read_parquet(?)
    """
    row = conn.execute(base_query, [parquet_path]).fetchone()
    total_records = row[0] if row else 0
    unique_txids = row[1] if row else 0
    earliest_ts = row[2] if row else None
    latest_ts = row[3] if row else None

    # 2. Unique wallets
    wallets_query = """
    WITH all_wallets AS (
        SELECT unnest(input_addresses) AS addr FROM read_parquet(?) WHERE len(input_addresses) > 0
        UNION
        SELECT unnest(output_addresses) AS addr FROM read_parquet(?) WHERE len(output_addresses) > 0
    )
    SELECT count(distinct addr) FROM all_wallets WHERE addr IS NOT NULL AND addr != ''
    """
    unique_wallets = conn.execute(wallets_query, [parquet_path, parquet_path]).fetchone()[0]

    # 3. Unique IPs
    ips_query = """
    WITH all_ips AS (
        SELECT src_ip AS ip FROM read_parquet(?) WHERE src_ip IS NOT NULL AND src_ip != ''
        UNION
        SELECT dst_ip AS ip FROM read_parquet(?) WHERE dst_ip IS NOT NULL AND dst_ip != ''
    )
    SELECT count(distinct ip) FROM all_ips
    """
    unique_ips = conn.execute(ips_query, [parquet_path, parquet_path]).fetchone()[0]

    # 4. Volume stats
    in_sum_query = """
    WITH in_amts AS (
        SELECT unnest(input_amounts) AS amt FROM read_parquet(?) WHERE len(input_amounts) > 0
    )
    SELECT coalesce(sum(amt), 0.0) FROM in_amts
    """
    total_in = conn.execute(in_sum_query, [parquet_path]).fetchone()[0]

    out_stats_query = """
    WITH out_amts AS (
        SELECT unnest(output_amounts) AS amt FROM read_parquet(?) WHERE len(output_amounts) > 0
    )
    SELECT
        coalesce(sum(amt), 0.0) AS total_out,
        avg(amt) AS avg_amt,
        min(amt) AS min_amt,
        max(amt) AS max_amt
    FROM out_amts
    """
    out_row = conn.execute(out_stats_query, [parquet_path]).fetchone()
    volume_stats = VolumeStats(
        total_input_btc=round(float(total_in), 8),
        total_output_btc=round(float(out_row[0]), 8),
        avg_amount=round(float(out_row[1]), 8) if out_row[1] is not None else None,
        min_amount=round(float(out_row[2]), 8) if out_row[2] is not None else None,
        max_amount=round(float(out_row[3]), 8) if out_row[3] is not None else None,
    )

    # 5. Fee stats
    fee_query = """
    SELECT
        coalesce(sum(fee), 0.0) AS total_fee,
        avg(fee) AS avg_fee,
        min(fee) AS min_fee,
        max(fee) AS max_fee,
        count(fee) AS fee_count
    FROM read_parquet(?)
    WHERE fee IS NOT NULL
    """
    fee_row = conn.execute(fee_query, [parquet_path]).fetchone()
    fee_stats = FeeStats(
        total_fee_btc=round(float(fee_row[0]), 8),
        avg_fee_btc=round(float(fee_row[1]), 8) if fee_row[1] is not None else None,
        min_fee_btc=round(float(fee_row[2]), 8) if fee_row[2] is not None else None,
        max_fee_btc=round(float(fee_row[3]), 8) if fee_row[3] is not None else None,
        fee_recorded_count=int(fee_row[4]),
    )

    # 6. Distributions
    script_types = dict(
        conn.execute(
            "SELECT script_type, count(*) FROM read_parquet(?) WHERE script_type IS NOT NULL GROUP BY script_type",
            [parquet_path],
        ).fetchall()
    )

    countries = dict(
        conn.execute(
            "SELECT geo_country, count(*) FROM read_parquet(?) WHERE geo_country IS NOT NULL GROUP BY geo_country",
            [parquet_path],
        ).fetchall()
    )

    asns = {
        str(row[0]): int(row[1])
        for row in conn.execute(
            "SELECT asn, count(*) FROM read_parquet(?) WHERE asn IS NOT NULL GROUP BY asn",
            [parquet_path],
        ).fetchall()
    }

    port_query = """
    WITH p AS (
        SELECT src_port AS port FROM read_parquet(?) WHERE src_port IS NOT NULL
        UNION ALL
        SELECT dst_port AS port FROM read_parquet(?) WHERE dst_port IS NOT NULL
    )
    SELECT port, count(*) FROM p GROUP BY port
    """
    ports = {str(r[0]): int(r[1]) for r in conn.execute(port_query, [parquet_path, parquet_path]).fetchall()}

    return DatasetAnalyticsSummary(
        dataset_id=dataset_id,
        total_records=total_records,
        unique_txids=unique_txids,
        unique_wallets=unique_wallets,
        unique_ips=unique_ips,
        volume_stats=volume_stats,
        fee_stats=fee_stats,
        earliest_timestamp=earliest_ts,
        latest_timestamp=latest_ts,
        script_types=script_types,
        countries=countries,
        asns=asns,
        ports=ports,
    )


def get_wallet_analytics(dataset_id: str, limit: int = 50) -> List[WalletActivity]:
    """Compute wallet-level activity, input/output counts, total sent/received, and net flow."""
    parquet_path = _get_parquet_path(dataset_id)
    conn = duckdb.connect()

    query = """
    WITH ins AS (
        SELECT
            unnest(input_addresses) AS address,
            unnest(input_amounts) AS amount,
            txid
        FROM read_parquet(?)
        WHERE len(input_addresses) > 0
    ),
    outs AS (
        SELECT
            unnest(output_addresses) AS address,
            unnest(output_amounts) AS amount,
            txid
        FROM read_parquet(?)
        WHERE len(output_addresses) > 0
    ),
    in_agg AS (
        SELECT
            address,
            count(*) AS in_cnt,
            coalesce(sum(amount), 0.0) AS total_sent
        FROM ins
        WHERE address IS NOT NULL AND address != ''
        GROUP BY address
    ),
    out_agg AS (
        SELECT
            address,
            count(*) AS out_cnt,
            coalesce(sum(amount), 0.0) AS total_received
        FROM outs
        WHERE address IS NOT NULL AND address != ''
        GROUP BY address
    ),
    combined AS (
        SELECT
            coalesce(i.address, o.address) AS address,
            coalesce(i.in_cnt, 0) AS input_count,
            coalesce(o.out_cnt, 0) AS output_count,
            coalesce(i.total_sent, 0.0) AS total_sent,
            coalesce(o.total_received, 0.0) AS total_received
        FROM in_agg i
        FULL OUTER JOIN out_agg o ON i.address = o.address
    )
    SELECT
        address,
        (input_count + output_count) AS tx_count,
        input_count,
        output_count,
        round(total_sent, 8) AS total_sent,
        round(total_received, 8) AS total_received,
        round((total_received - total_sent), 8) AS net_flow
    FROM combined
    ORDER BY (total_sent + total_received) DESC
    LIMIT ?
    """
    rows = conn.execute(query, [parquet_path, parquet_path, limit]).fetchall()
    return [
        WalletActivity(
            address=r[0],
            tx_count=int(r[1]),
            input_count=int(r[2]),
            output_count=int(r[3]),
            total_sent=float(r[4]),
            total_received=float(r[5]),
            net_flow=float(r[6]),
        )
        for r in rows
    ]


def get_time_series_analytics(dataset_id: str) -> List[TimeSeriesBucket]:
    """Group transactions by time buckets (hourly intervals) with transaction count and output volume."""
    parquet_path = _get_parquet_path(dataset_id)
    conn = duckdb.connect()

    query = """
    WITH out_amts AS (
        SELECT
            substring(timestamp, 1, 13) || ':00:00Z' AS bucket,
            txid,
            unnest(output_amounts) AS amt
        FROM read_parquet(?)
        WHERE timestamp IS NOT NULL AND timestamp != '' AND len(output_amounts) > 0
    ),
    tx_buckets AS (
        SELECT
            substring(timestamp, 1, 13) || ':00:00Z' AS bucket,
            count(distinct txid) AS tx_cnt
        FROM read_parquet(?)
        WHERE timestamp IS NOT NULL AND timestamp != ''
        GROUP BY 1
    ),
    vol_buckets AS (
        SELECT
            bucket,
            coalesce(sum(amt), 0.0) AS volume
        FROM out_amts
        GROUP BY bucket
    )
    SELECT
        t.bucket,
        t.tx_cnt,
        coalesce(v.volume, 0.0) AS volume
    FROM tx_buckets t
    LEFT JOIN vol_buckets v ON t.bucket = v.bucket
    ORDER BY t.bucket ASC
    """
    rows = conn.execute(query, [parquet_path, parquet_path]).fetchall()
    return [
        TimeSeriesBucket(
            timestamp_bucket=r[0],
            tx_count=int(r[1]),
            volume=round(float(r[2]), 8),
        )
        for r in rows
    ]


def get_network_analytics(dataset_id: str) -> Dict[str, Any]:
    """Extract network peer communications, country, ASN, and port summaries."""
    parquet_path = _get_parquet_path(dataset_id)
    conn = duckdb.connect()

    query = """
    SELECT
        src_ip,
        dst_ip,
        src_port,
        dst_port,
        geo_country,
        asn,
        count(*) AS observation_count
    FROM read_parquet(?)
    WHERE (src_ip IS NOT NULL AND src_ip != '') OR (dst_ip IS NOT NULL AND dst_ip != '')
    GROUP BY 1, 2, 3, 4, 5, 6
    ORDER BY observation_count DESC
    LIMIT 50
    """
    obs_rows = conn.execute(query, [parquet_path]).fetchall()
    observations = [
        NetworkObservation(
            src_ip=r[0],
            dst_ip=r[1],
            src_port=r[2],
            dst_port=r[3],
            geo_country=r[4],
            asn=r[5],
            observation_count=int(r[6]),
        )
        for r in obs_rows
    ]

    unique_src_ips = [
        r[0] for r in conn.execute(
            "SELECT distinct src_ip FROM read_parquet(?) WHERE src_ip IS NOT NULL AND src_ip != ''",
            [parquet_path],
        ).fetchall()
    ]
    unique_dst_ips = [
        r[0] for r in conn.execute(
            "SELECT distinct dst_ip FROM read_parquet(?) WHERE dst_ip IS NOT NULL AND dst_ip != ''",
            [parquet_path],
        ).fetchall()
    ]

    return {
        "dataset_id": dataset_id,
        "unique_source_ips": unique_src_ips,
        "unique_destination_ips": unique_dst_ips,
        "observations": [o.model_dump() for o in observations],
    }


def get_correlation_records(dataset_id: str, limit: int = 100) -> List[CorrelationRecord]:
    """Retrieve correlation-ready records joining on-chain transactions with network telemetry."""
    parquet_path = _get_parquet_path(dataset_id)
    conn = duckdb.connect()

    query = """
    SELECT
        txid,
        timestamp,
        input_addresses,
        output_addresses,
        input_amounts,
        output_amounts,
        fee,
        src_ip,
        dst_ip,
        src_port,
        dst_port,
        geo_country,
        asn,
        script_type
    FROM read_parquet(?)
    LIMIT ?
    """
    rows = conn.execute(query, [parquet_path, limit]).fetchall()
    results: List[CorrelationRecord] = []
    for r in rows:
        results.append(
            CorrelationRecord(
                txid=r[0],
                timestamp=r[1],
                input_addresses=r[2] if r[2] is not None else [],
                output_addresses=r[3] if r[3] is not None else [],
                input_amounts=[float(x) for x in r[4]] if r[4] is not None else [],
                output_amounts=[float(x) for x in r[5]] if r[5] is not None else [],
                fee=float(r[6]) if r[6] is not None else None,
                src_ip=r[7],
                dst_ip=r[8],
                src_port=r[9],
                dst_port=r[10],
                geo_country=r[11],
                asn=r[12],
                script_type=r[13],
            )
        )
    return results
