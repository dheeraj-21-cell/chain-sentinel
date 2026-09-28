from datetime import datetime, timezone
import ipaddress
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from app.models.dataset import RejectedRecord
from app.models.transaction import NormalizedTransaction

# Canonical mapping for aliases
FIELD_ALIASES = {
    "timestamp": ["timestamp", "time", "date", "datetime", "block_time", "tx_time"],
    "src_ip": ["src_ip", "source_ip", "srcip", "source_address", "client_ip"],
    "dst_ip": ["dst_ip", "dest_ip", "destination_ip", "dstip", "peer_ip", "server_ip"],
    "src_port": ["src_port", "source_port", "srcport"],
    "dst_port": ["dst_port", "dest_port", "destination_port", "dstport"],
    "txid": ["txid", "tx_id", "transaction_id", "tx_hash", "hash"],
    "input_addresses": ["input_addresses", "input_address", "inputs", "in_addresses", "from_addresses", "vin_addresses"],
    "output_addresses": ["output_addresses", "output_address", "outputs", "out_addresses", "to_addresses", "vout_addresses"],
    "input_amounts": ["input_amounts", "input_amount", "in_amounts", "vin_amounts"],
    "output_amounts": ["output_amounts", "output_amount", "out_amounts", "vout_amounts"],
    "fee": ["fee", "fees", "tx_fee"],
    "script_type": ["script_type", "scripttype", "type"],
    "geo_country": ["geo_country", "country", "country_code"],
    "asn": ["asn", "as_number", "autonomous_system"],
}


def canonicalize_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map raw input keys to canonical field names, trimming string values."""
    canonical: Dict[str, Any] = {}
    normalized_keys = {
        re.sub(r"[^a-zA-Z0-9_]", "", k.lower().strip()): (k, v)
        for k, v in raw.items()
    }

    for canonical_name, aliases in FIELD_ALIASES.items():
        found = False
        for alias in aliases:
            cleaned_alias = re.sub(r"[^a-zA-Z0-9_]", "", alias.lower().strip())
            if cleaned_alias in normalized_keys:
                orig_k, val = normalized_keys[cleaned_alias]
                canonical[canonical_name] = val
                found = True
                break
        if not found:
            canonical[canonical_name] = None

    return canonical


def parse_array_field(val: Any) -> List[str]:
    """Parse string, list, or JSON representation into a list of strings."""
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        return [str(x).strip().strip("'").strip('"') for x in val if x is not None and str(x).strip() != ""]
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return []
        if val.startswith("[") and val.endswith("]"):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return [str(x).strip().strip("'").strip('"') for x in parsed if x is not None and str(x).strip() != ""]
            except Exception:
                # Strip square brackets and continue delimiter parsing
                val = val[1:-1].strip()
        # Delimiters
        for delim in [";", "|", ","]:
            if delim in val:
                return [p.strip().strip("'").strip('"') for p in val.split(delim) if p.strip().strip("'").strip('"') != ""]
        return [val.strip().strip("'").strip('"')]
    return [str(val).strip().strip("'").strip('"')]


def normalize_timestamp(val: Any) -> Optional[str]:
    """Normalize timestamp value to UTC ISO-8601 string or raise ValueError."""
    if val is None or (isinstance(val, str) and val.strip() == ""):
        return None

    # Epoch numeric
    if isinstance(val, (int, float)):
        ts = float(val)
        if ts > 1e11:  # Milliseconds
            ts = ts / 1000.0
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    if isinstance(val, str):
        val = val.strip()
        # Check if numeric string
        try:
            ts = float(val)
            if ts > 1e11:
                ts = ts / 1000.0
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass

        # Try ISO format
        val_clean = val.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(val_clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass

        # Try common formats
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y-%m-%d",
            "%d-%m-%Y %H:%M:%S",
        ):
            try:
                dt = datetime.strptime(val, fmt).replace(tzinfo=timezone.utc)
                return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                continue

    raise ValueError(f"Unable to parse timestamp: '{val}'")


def normalize_and_validate_record(
    record_index: int,
    raw_record: Dict[str, Any],
    dataset_id: str,
) -> Tuple[Optional[NormalizedTransaction], Optional[RejectedRecord]]:
    """Validate and normalize a raw record into a NormalizedTransaction or RejectedRecord."""
    errors: List[str] = []
    canonical = canonicalize_record(raw_record)

    # 1. Timestamp
    normalized_ts: Optional[str] = None
    if canonical["timestamp"] is not None:
        try:
            normalized_ts = normalize_timestamp(canonical["timestamp"])
        except ValueError as err:
            errors.append(str(err))

    # 2. IP Addresses
    normalized_src_ip: Optional[str] = None
    if canonical["src_ip"] is not None and str(canonical["src_ip"]).strip() != "":
        raw_ip = str(canonical["src_ip"]).strip()
        try:
            ip_obj = ipaddress.ip_address(raw_ip)
            normalized_src_ip = str(ip_obj)
        except ValueError:
            errors.append(f"Invalid source IP address: '{raw_ip}'")

    normalized_dst_ip: Optional[str] = None
    if canonical["dst_ip"] is not None and str(canonical["dst_ip"]).strip() != "":
        raw_ip = str(canonical["dst_ip"]).strip()
        try:
            ip_obj = ipaddress.ip_address(raw_ip)
            normalized_dst_ip = str(ip_obj)
        except ValueError:
            errors.append(f"Invalid destination IP address: '{raw_ip}'")

    # 3. Network Ports
    normalized_src_port: Optional[int] = None
    if canonical["src_port"] is not None and str(canonical["src_port"]).strip() != "":
        raw_port = str(canonical["src_port"]).strip()
        try:
            p = int(raw_port)
            if 1 <= p <= 65535:
                normalized_src_port = p
            else:
                errors.append(f"Source port '{raw_port}' out of valid range (1..65535)")
        except ValueError:
            errors.append(f"Source port '{raw_port}' is not an integer")

    normalized_dst_port: Optional[int] = None
    if canonical["dst_port"] is not None and str(canonical["dst_port"]).strip() != "":
        raw_port = str(canonical["dst_port"]).strip()
        try:
            p = int(raw_port)
            if 1 <= p <= 65535:
                normalized_dst_port = p
            else:
                errors.append(f"Destination port '{raw_port}' out of valid range (1..65535)")
        except ValueError:
            errors.append(f"Destination port '{raw_port}' is not an integer")

    # 4. Transaction ID (txid)
    normalized_txid: Optional[str] = None
    if canonical["txid"] is not None and str(canonical["txid"]).strip() != "":
        normalized_txid = str(canonical["txid"]).strip()

    # 5. Input addresses & amounts
    input_addresses = parse_array_field(canonical["input_addresses"])
    raw_input_amounts = parse_array_field(canonical["input_amounts"])
    input_amounts: List[float] = []
    for amt_str in raw_input_amounts:
        try:
            amt = float(amt_str)
            if amt < 0:
                errors.append(f"Negative input amount not permitted: {amt}")
            else:
                input_amounts.append(amt)
        except ValueError:
            errors.append(f"Invalid numeric value for input amount: '{amt_str}'")

    # Check positional consistency between input addresses and amounts
    if input_addresses and input_amounts:
        if len(input_addresses) != len(input_amounts):
            errors.append(
                f"Inconsistent input array lengths: input_addresses has {len(input_addresses)} "
                f"items but input_amounts has {len(input_amounts)} items."
            )

    # 6. Output addresses & amounts
    output_addresses = parse_array_field(canonical["output_addresses"])
    raw_output_amounts = parse_array_field(canonical["output_amounts"])
    output_amounts: List[float] = []
    for amt_str in raw_output_amounts:
        try:
            amt = float(amt_str)
            if amt < 0:
                errors.append(f"Negative output amount not permitted: {amt}")
            else:
                output_amounts.append(amt)
        except ValueError:
            errors.append(f"Invalid numeric value for output amount: '{amt_str}'")

    # Check positional consistency between output addresses and amounts
    if output_addresses and output_amounts:
        if len(output_addresses) != len(output_amounts):
            errors.append(
                f"Inconsistent output array lengths: output_addresses has {len(output_addresses)} "
                f"items but output_amounts has {len(output_amounts)} items."
            )

    # 7. Fee
    normalized_fee: Optional[float] = None
    if canonical["fee"] is not None and str(canonical["fee"]).strip() != "":
        raw_fee = str(canonical["fee"]).strip()
        try:
            fee_val = float(raw_fee)
            if fee_val < 0:
                errors.append(f"Negative fee not permitted: {fee_val}")
            else:
                normalized_fee = fee_val
        except ValueError:
            errors.append(f"Invalid numeric value for fee: '{raw_fee}'")

    # 8. Script type
    normalized_script: Optional[str] = None
    if canonical["script_type"] is not None and str(canonical["script_type"]).strip() != "":
        normalized_script = str(canonical["script_type"]).strip().lower()

    # 9. Geo Country
    normalized_country: Optional[str] = None
    if canonical["geo_country"] is not None and str(canonical["geo_country"]).strip() != "":
        normalized_country = str(canonical["geo_country"]).strip()

    # 10. ASN
    normalized_asn: Optional[int] = None
    if canonical["asn"] is not None and str(canonical["asn"]).strip() != "":
        raw_asn = str(canonical["asn"]).strip()
        if raw_asn.upper().startswith("AS"):
            raw_asn = raw_asn[2:].strip()
        try:
            normalized_asn = int(raw_asn)
        except ValueError:
            errors.append(f"Invalid ASN format: '{canonical['asn']}'")

    if errors:
        rejected = RejectedRecord(
            record_index=record_index,
            raw_data=raw_record,
            errors=errors,
        )
        return None, rejected

    normalized_tx = NormalizedTransaction(
        dataset_id=dataset_id,
        timestamp=normalized_ts,
        src_ip=normalized_src_ip,
        dst_ip=normalized_dst_ip,
        src_port=normalized_src_port,
        dst_port=normalized_dst_port,
        txid=normalized_txid,
        input_addresses=input_addresses,
        output_addresses=output_addresses,
        input_amounts=input_amounts,
        output_amounts=output_amounts,
        fee=normalized_fee,
        script_type=normalized_script,
        geo_country=normalized_country,
        asn=normalized_asn,
    )
    return normalized_tx, None
