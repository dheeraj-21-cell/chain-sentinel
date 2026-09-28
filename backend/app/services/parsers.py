import csv
import io
import json
import xml.etree.ElementTree as ET
from typing import Any, Dict, List


def parse_csv(content: bytes) -> List[Dict[str, Any]]:
    """Parse CSV content bytes into a list of raw dictionaries."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    # Detect delimiter
    sample = text[:4096]
    delimiter = ","
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ","

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        headers = next(reader)
    except StopIteration:
        return []

    # Clean headers
    clean_headers = [h.strip().strip('"').strip("'") for h in headers]

    records: List[Dict[str, Any]] = []
    for row in reader:
        if not row or all(col.strip() == "" for col in row):
            continue  # Skip blank lines
        record: Dict[str, Any] = {}
        for idx, header in enumerate(clean_headers):
            val = row[idx].strip() if idx < len(row) else ""
            record[header] = val if val != "" else None
        records.append(record)

    return records


def parse_json(content: bytes) -> List[Dict[str, Any]]:
    """Parse JSON content bytes (array, wrapped object, or NDJSON) into a list of raw dictionaries."""
    try:
        text = content.decode("utf-8-sig").strip()
    except UnicodeDecodeError:
        text = content.decode("latin-1").strip()

    if not text:
        return []

    # Attempt 1: Standard JSON document
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            # Check for standard container keys
            for key in ["records", "transactions", "data", "items", "rows"]:
                if key in data and isinstance(data[key], list):
                    return [item for item in data[key] if isinstance(item, dict)]
            return [data]
        else:
            raise ValueError("Top-level JSON is neither an object nor an array.")
    except json.JSONDecodeError:
        # Attempt 2: Line-delimited JSON (NDJSON)
        records: List[Dict[str, Any]] = []
        for line_num, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    records.append(item)
            except json.JSONDecodeError as err:
                raise ValueError(f"Malformed JSON on line {line_num}: {err}") from err
        if records:
            return records
        raise ValueError("File content is not valid JSON or NDJSON.")


def parse_xml(content: bytes) -> List[Dict[str, Any]]:
    """Parse XML content bytes into a list of raw dictionaries."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError as err:
        raise ValueError(f"Malformed XML syntax: {err}") from err

    records: List[Dict[str, Any]] = []

    # Determine record elements
    # Common conventions: <dataset><record>...</record></dataset> or <transactions><transaction>...</transaction></transactions>
    child_elements = list(root)
    if not child_elements and root.text and not root.text.strip():
        # Empty root
        return []

    # If root itself looks like a single record or has no child containers
    if root.tag.lower() in ("transaction", "record") and not any(len(c) > 0 for c in child_elements):
        elements_to_process = [root]
    elif child_elements:
        elements_to_process = child_elements
    else:
        elements_to_process = [root]

    for elem in elements_to_process:
        record: Dict[str, Any] = {}
        for child in elem:
            tag = child.tag.strip()
            nested_children = list(child)
            if nested_children:
                # E.g. <input_addresses><item>addr1</item><item>addr2</item></input_addresses>
                items = [nc.text.strip() for nc in nested_children if nc.text and nc.text.strip()]
                record[tag] = items
            else:
                text_val = child.text.strip() if child.text else None
                record[tag] = text_val if text_val != "" else None
        if record:
            records.append(record)

    return records
