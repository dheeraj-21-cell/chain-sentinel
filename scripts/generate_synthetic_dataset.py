#!/usr/bin/env python3
"""
Realistic Synthetic Bitcoin Transaction & P2P Network Metadata Generator
Part of Phase 10.5 — Offline Validation & ML Verification.

Produces a realistic synthetic CSV following the SIH schema with diverse behavioral
populations (ordinary, fan-in, fan-out, burst, dispersion, peeling chain, dormancy).
Zero fake intelligence: generates raw CSV records for genuine ingestion.
"""

import argparse
import csv
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import random
from typing import Any, Dict, List, Optional


# Base58 character set for Bitcoin address simulation
B58_CHARS = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BECH32_CHARS = "023456789acdefghjklmnpqrstuvwxyz"


def generate_address(addr_type: str = "p2pkh", seed_int: int = 0) -> str:
    """Generate a realistic Bitcoin address string."""
    rng = random.Random(seed_int)
    if addr_type == "p2pkh":
        # Starts with 1, 33-34 chars
        suffix = "".join(rng.choice(B58_CHARS) for _ in range(33))
        return f"1{suffix}"
    elif addr_type == "p2sh":
        # Starts with 3, 33-34 chars
        suffix = "".join(rng.choice(B58_CHARS) for _ in range(33))
        return f"3{suffix}"
    elif addr_type == "p2wpkh":
        # Starts with bc1q, 38-42 chars
        suffix = "".join(rng.choice(BECH32_CHARS) for _ in range(38))
        return f"bc1q{suffix}"
    elif addr_type == "p2tr":
        # Starts with bc1p, 58-62 chars
        suffix = "".join(rng.choice(BECH32_CHARS) for _ in range(58))
        return f"bc1p{suffix}"
    suffix = "".join(rng.choice(B58_CHARS) for _ in range(33))
    return f"1{suffix}"


def generate_txid(seed_int: int) -> str:
    """Generate a realistic 64-char hex transaction ID."""
    raw = f"bitcoin_tx_sim_{seed_int}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# Known ASN & Geo registry for realistic telemetry
NETWORK_PEERS = [
    {"country": "US", "asn": 15169, "ips": ["142.250.190.46", "142.250.72.110", "172.217.16.206"]},
    {"country": "US", "asn": 13335, "ips": ["104.244.42.1", "104.244.42.129", "162.158.0.1"]},
    {"country": "US", "asn": 16509, "ips": ["54.239.28.85", "52.95.110.1", "3.5.0.1"]},
    {"country": "DE", "asn": 24940, "ips": ["88.198.50.12", "136.243.10.45", "144.76.80.99"]},
    {"country": "NL", "asn": 16276, "ips": ["51.255.40.10", "149.202.80.20", "198.245.50.5"]},
    {"country": "SG", "asn": 4657, "ips": ["203.116.1.10", "203.116.20.50", "116.86.0.1"]},
    {"country": "JP", "asn": 2516, "ips": ["111.89.0.1", "124.211.0.1", "210.140.0.1"]},
    {"country": "GB", "asn": 2856, "ips": ["81.130.0.1", "81.134.0.1", "86.128.0.1"]},
]


def generate_synthetic_dataset(
    target_count: int = 700,
    seed: int = 42,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generate a realistic synthetic Bitcoin transaction & P2P network metadata CSV.
    """
    random.seed(seed)
    base_time = datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc)

    records: List[Dict[str, Any]] = []
    tx_counter = 1
    addr_counter = 1000

    def next_addr(addr_type: str = "p2pkh") -> str:
        nonlocal addr_counter
        addr_counter += 1
        return generate_address(addr_type, seed_int=addr_counter)

    def next_txid() -> str:
        nonlocal tx_counter
        tx_counter += 1
        return generate_txid(tx_counter)

    def random_peer() -> Dict[str, Any]:
        peer = random.choice(NETWORK_PEERS)
        src_ip = random.choice(peer["ips"])
        # random destination from another provider
        other = random.choice([p for p in NETWORK_PEERS if p["asn"] != peer["asn"]])
        dst_ip = random.choice(other["ips"])
        return {
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": random.choice([8333, 18333, random.randint(49152, 65530)]),
            "dst_port": 8333,
            "country": peer["country"],
            "asn": f"AS{peer['asn']}",
        }

    scale = max(0.15, min(1.0, target_count / 700.0))
    if target_count >= 350:
        baseline_count = target_count - 300
    else:
        baseline_count = max(20, int(400 * scale))

    # =========================================================================
    # Population 1: Baseline Ordinary Transactions (~400 records)
    # =========================================================================
    current_time = base_time
    for _ in range(baseline_count):
        current_time += timedelta(minutes=random.randint(15, 180), seconds=random.randint(0, 59))
        st = random.choice(["p2pkh", "p2wpkh", "p2sh", "p2tr"])
        in_addr = next_addr(st)
        in_amt = round(random.uniform(0.01, 3.5), 8)

        fee = round(random.uniform(0.00005, 0.0004), 8)
        # 1 or 2 outputs
        has_change = random.random() < 0.75
        if has_change:
            out_amt1 = round(in_amt * random.uniform(0.2, 0.8), 8)
            out_amt2 = round(in_amt - out_amt1 - fee, 8)
            if out_amt2 <= 0:
                out_amt2 = 0.001
                in_amt = round(out_amt1 + out_amt2 + fee, 8)
            out_addrs = [next_addr(st), next_addr(st)]
            out_amts = [out_amt1, out_amt2]
        else:
            out_amt = round(in_amt - fee, 8)
            if out_amt <= 0:
                out_amt = 0.005
                in_amt = round(out_amt + fee, 8)
            out_addrs = [next_addr(st)]
            out_amts = [out_amt]

        peer = random_peer()
        records.append({
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "src_ip": peer["src_ip"],
            "dst_ip": peer["dst_ip"],
            "src_port": peer["src_port"],
            "dst_port": peer["dst_port"],
            "txid": next_txid(),
            "input_addresses": in_addr,
            "input_amounts": str(in_amt),
            "output_addresses": ";".join(out_addrs),
            "output_amounts": ";".join(str(a) for a in out_amts),
            "fee": str(fee),
            "script_type": st,
            "geo_country": peer["country"],
            "asn": peer["asn"],
        })

    # =========================================================================
    # Population 2: Recurring / Repeated Wallet Activity (~80 records)
    # 5 specific merchant / hub wallets that transact repeatedly
    # =========================================================================
    hub_wallets = [next_addr("p2wpkh") for _ in range(5)]
    for _ in range(80 if target_count >= 350 else max(5, int(80 * scale))):
        current_time += timedelta(minutes=random.randint(30, 240))
        hub = random.choice(hub_wallets)
        is_hub_sender = random.random() < 0.5
        other_wallet = next_addr("p2wpkh")

        amt = round(random.uniform(0.05, 1.2), 8)
        fee = 0.0001
        in_amt = round(amt + fee, 8)

        if is_hub_sender:
            in_addrs = [hub]
            in_amts = [in_amt]
            out_addrs = [other_wallet]
            out_amts = [amt]
        else:
            in_addrs = [other_wallet]
            in_amts = [in_amt]
            out_addrs = [hub]
            out_amts = [amt]

        peer = random_peer()
        records.append({
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "src_ip": peer["src_ip"],
            "dst_ip": peer["dst_ip"],
            "src_port": peer["src_port"],
            "dst_port": peer["dst_port"],
            "txid": next_txid(),
            "input_addresses": in_addrs[0],
            "input_amounts": str(in_amts[0]),
            "output_addresses": out_addrs[0],
            "output_amounts": str(out_amts[0]),
            "fee": str(fee),
            "script_type": "p2wpkh",
            "geo_country": peer["country"],
            "asn": peer["asn"],
        })

    # =========================================================================
    # Population 3: Fan-In Consolidation (~35 records)
    # Multiple distinct input wallets funding a single recipient collector
    # =========================================================================
    collector_wallet = next_addr("p2sh")
    for _ in range(35 if target_count >= 350 else max(2, int(35 * scale))):
        current_time += timedelta(minutes=random.randint(60, 360))
        num_sources = random.randint(3, 6)
        src_addrs = [next_addr("p2pkh") for _ in range(num_sources)]
        src_amts = [round(random.uniform(0.1, 0.8), 8) for _ in range(num_sources)]
        fee = 0.0002
        tot_in = round(sum(src_amts), 8)
        out_amt = round(tot_in - fee, 8)

        peer = random_peer()
        records.append({
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "src_ip": peer["src_ip"],
            "dst_ip": peer["dst_ip"],
            "src_port": peer["src_port"],
            "dst_port": peer["dst_port"],
            "txid": next_txid(),
            "input_addresses": ";".join(src_addrs),
            "input_amounts": ";".join(str(a) for a in src_amts),
            "output_addresses": collector_wallet,
            "output_amounts": str(out_amt),
            "fee": str(fee),
            "script_type": "p2sh",
            "geo_country": peer["country"],
            "asn": peer["asn"],
        })

    # =========================================================================
    # Population 4: Fan-Out Distribution (~35 records)
    # A single distributor wallet sending to 4-8 destination wallets
    # =========================================================================
    distributor_wallet = next_addr("p2wpkh")
    for _ in range(35 if target_count >= 350 else max(2, int(35 * scale))):
        current_time += timedelta(minutes=random.randint(60, 300))
        num_dests = random.randint(4, 7)
        dst_addrs = [next_addr("p2pkh") for _ in range(num_dests)]
        dst_amts = [round(random.uniform(0.05, 0.4), 8) for _ in range(num_dests)]
        fee = 0.00025
        tot_out = round(sum(dst_amts), 8)
        tot_in = round(tot_out + fee, 8)

        peer = random_peer()
        records.append({
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "src_ip": peer["src_ip"],
            "dst_ip": peer["dst_ip"],
            "src_port": peer["src_port"],
            "dst_port": peer["dst_port"],
            "txid": next_txid(),
            "input_addresses": distributor_wallet,
            "input_amounts": str(tot_in),
            "output_addresses": ";".join(dst_addrs),
            "output_amounts": ";".join(str(a) for a in dst_amts),
            "fee": str(fee),
            "script_type": "p2wpkh",
            "geo_country": peer["country"],
            "asn": peer["asn"],
        })

    # =========================================================================
    # Population 5: Bursty Activity (~30 records)
    # High-density bursts: 3 bursts of 8-10 txs within 2-4 minutes
    # =========================================================================
    burst_wallet = next_addr("p2pkh")
    for burst_idx in range(3 if target_count >= 350 else max(1, int(3 * scale))):
        burst_time = current_time + timedelta(hours=random.randint(12, 48))
        current_time = burst_time
        for _ in range(10 if target_count >= 350 else 4):
            burst_time += timedelta(seconds=random.randint(10, 25))
            amt = round(random.uniform(0.02, 0.2), 8)
            fee = 0.0001
            in_amt = round(amt + fee, 8)
            dest = next_addr("p2pkh")
            peer = random_peer()
            records.append({
                "timestamp": burst_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "src_ip": peer["src_ip"],
                "dst_ip": peer["dst_ip"],
                "src_port": peer["src_port"],
                "dst_port": peer["dst_port"],
                "txid": next_txid(),
                "input_addresses": burst_wallet,
                "input_amounts": str(in_amt),
                "output_addresses": dest,
                "output_amounts": str(amt),
                "fee": str(fee),
                "script_type": "p2pkh",
                "geo_country": peer["country"],
                "asn": peer["asn"],
            })

    # =========================================================================
    # Population 6: Rapid Value Dispersion (~25 records)
    # Wallet receives funds and fans them out within 120 seconds
    # =========================================================================
    dispersion_hub = next_addr("p2wpkh")
    for _ in range(5 if target_count >= 350 else max(1, int(5 * scale))):
        disp_time = current_time + timedelta(hours=random.randint(8, 24))
        current_time = disp_time
        # Initial funding tx
        inflow_amt = 5.0
        fee1 = 0.0001
        peer1 = random_peer()
        records.append({
            "timestamp": disp_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "src_ip": peer1["src_ip"],
            "dst_ip": peer1["dst_ip"],
            "src_port": peer1["src_port"],
            "dst_port": peer1["dst_port"],
            "txid": next_txid(),
            "input_addresses": next_addr("p2wpkh"),
            "input_amounts": str(round(inflow_amt + fee1, 8)),
            "output_addresses": dispersion_hub,
            "output_amounts": str(inflow_amt),
            "fee": str(fee1),
            "script_type": "p2wpkh",
            "geo_country": peer1["country"],
            "asn": peer1["asn"],
        })

        # Rapid fanout 60 seconds later to 4 destinations
        disp_time += timedelta(seconds=60)
        dest_addrs = [next_addr("p2pkh") for _ in range(4)]
        dest_amts = [1.2, 1.2, 1.2, 1.3998]
        fee2 = 0.0002
        peer2 = random_peer()
        records.append({
            "timestamp": disp_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "src_ip": peer2["src_ip"],
            "dst_ip": peer2["dst_ip"],
            "src_port": peer2["src_port"],
            "dst_port": peer2["dst_port"],
            "txid": next_txid(),
            "input_addresses": dispersion_hub,
            "input_amounts": str(inflow_amt),
            "output_addresses": ";".join(dest_addrs),
            "output_amounts": ";".join(str(a) for a in dest_amts),
            "fee": str(fee2),
            "script_type": "p2wpkh",
            "geo_country": peer2["country"],
            "asn": peer2["asn"],
        })

    # =========================================================================
    # Population 7: Multi-Hop Sequential Chains (~30 records)
    # W0 -> W1 -> W2 -> W3 -> W4 with chronological progression
    # =========================================================================
    for chain_id in range(6 if target_count >= 350 else max(1, int(6 * scale))):
        chain_time = current_time + timedelta(hours=random.randint(6, 18))
        current_time = chain_time
        chain_wallets = [next_addr("p2pkh") for _ in range(6)]
        chain_amt = round(random.uniform(2.0, 4.0), 8)
        for hop in range(5):
            chain_time += timedelta(minutes=random.randint(15, 45))
            fee = 0.0001
            out_amt = round(chain_amt - fee, 8)
            peer = random_peer()
            records.append({
                "timestamp": chain_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "src_ip": peer["src_ip"],
                "dst_ip": peer["dst_ip"],
                "src_port": peer["src_port"],
                "dst_port": peer["dst_port"],
                "txid": next_txid(),
                "input_addresses": chain_wallets[hop],
                "input_amounts": str(chain_amt),
                "output_addresses": chain_wallets[hop + 1],
                "output_amounts": str(out_amt),
                "fee": str(fee),
                "script_type": "p2pkh",
                "geo_country": peer["country"],
                "asn": peer["asn"],
            })
            chain_amt = out_amt

    # =========================================================================
    # Population 8: Peeling Chain-like Activity (~25 records)
    # High value split into smaller payment + continuation change address
    # =========================================================================
    for peel_run in range(5 if target_count >= 350 else max(1, int(5 * scale))):
        peel_time = current_time + timedelta(hours=random.randint(8, 20))
        current_time = peel_time
        current_holding_wallet = next_addr("p2sh")
        current_balance = 25.0
        for hop in range(5):
            peel_time += timedelta(minutes=random.randint(10, 30))
            peeled_payment = round(random.uniform(0.5, 1.5), 8)
            fee = 0.00015
            continuation_balance = round(current_balance - peeled_payment - fee, 8)
            continuation_wallet = next_addr("p2sh")
            merchant_dest = next_addr("p2wpkh")

            peer = random_peer()
            records.append({
                "timestamp": peel_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "src_ip": peer["src_ip"],
                "dst_ip": peer["dst_ip"],
                "src_port": peer["src_port"],
                "dst_port": peer["dst_port"],
                "txid": next_txid(),
                "input_addresses": current_holding_wallet,
                "input_amounts": str(current_balance),
                "output_addresses": f"{merchant_dest};{continuation_wallet}",
                "output_amounts": f"{peeled_payment};{continuation_balance}",
                "fee": str(fee),
                "script_type": "p2sh",
                "geo_country": peer["country"],
                "asn": peer["asn"],
            })
            current_holding_wallet = continuation_wallet
            current_balance = continuation_balance

    # =========================================================================
    # Population 9: Dormant-to-Active Entity (~15 records)
    # Early transactions on Day 2, silent for 35+ days, renewed on Day 45
    # =========================================================================
    dormant_wallet = next_addr("p2pkh")
    # Early activity (Day 2)
    early_time = base_time + timedelta(days=2, hours=10)
    for _ in range(5 if target_count >= 350 else 2):
        early_time += timedelta(hours=2)
        peer = random_peer()
        records.append({
            "timestamp": early_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "src_ip": peer["src_ip"],
            "dst_ip": peer["dst_ip"],
            "src_port": peer["src_port"],
            "dst_port": peer["dst_port"],
            "txid": next_txid(),
            "input_addresses": next_addr("p2pkh"),
            "input_amounts": "1.5",
            "output_addresses": dormant_wallet,
            "output_amounts": "1.4999",
            "fee": "0.0001",
            "script_type": "p2pkh",
            "geo_country": peer["country"],
            "asn": peer["asn"],
        })

    # Sudden reactivation on Day 45 (43 days dormancy > 30 days threshold)
    reactivation_time = base_time + timedelta(days=45, hours=14)
    for _ in range(10 if target_count >= 350 else 3):
        reactivation_time += timedelta(hours=3)
        peer = random_peer()
        records.append({
            "timestamp": reactivation_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "src_ip": peer["src_ip"],
            "dst_ip": peer["dst_ip"],
            "src_port": peer["src_port"],
            "dst_port": peer["dst_port"],
            "txid": next_txid(),
            "input_addresses": dormant_wallet,
            "input_amounts": "0.5",
            "output_addresses": next_addr("p2pkh"),
            "output_amounts": "0.4999",
            "fee": "0.0001",
            "script_type": "p2pkh",
            "geo_country": peer["country"],
            "asn": peer["asn"],
        })

    # =========================================================================
    # Population 10: Statistical Outliers / Extreme Volume (~15 records)
    # High-volume whale transfers (100 - 450 BTC) to provide genuine ML variation
    # =========================================================================
    for _ in range(15 if target_count >= 350 else max(1, int(15 * scale))):
        current_time += timedelta(hours=random.randint(24, 72))
        whale_wallet = next_addr("p2tr")
        whale_amt = round(random.uniform(85.0, 350.0), 8)
        fee = round(random.uniform(0.005, 0.02), 8)
        dest = next_addr("p2tr")
        peer = random_peer()
        records.append({
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "src_ip": peer["src_ip"],
            "dst_ip": peer["dst_ip"],
            "src_port": peer["src_port"],
            "dst_port": peer["dst_port"],
            "txid": next_txid(),
            "input_addresses": whale_wallet,
            "input_amounts": str(whale_amt),
            "output_addresses": dest,
            "output_amounts": str(round(whale_amt - fee, 8)),
            "fee": str(fee),
            "script_type": "p2tr",
            "geo_country": peer["country"],
            "asn": peer["asn"],
        })

    # =========================================================================
    # Population 11: Telemetry Variance & Legitimate Missing Values (~10 records)
    # Valid on-chain transactions lacking network metadata (off-p2p observation)
    # =========================================================================
    for _ in range(10 if target_count >= 350 else max(2, int(10 * scale))):
        current_time += timedelta(hours=random.randint(12, 36))
        in_amt = 1.0
        fee = 0.0001
        records.append({
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "src_ip": "",
            "dst_ip": "",
            "src_port": "",
            "dst_port": "",
            "txid": next_txid(),
            "input_addresses": next_addr("p2pkh"),
            "input_amounts": str(in_amt),
            "output_addresses": next_addr("p2pkh"),
            "output_amounts": str(round(in_amt - fee, 8)),
            "fee": str(fee) if random.random() < 0.5 else "",
            "script_type": "p2pkh",
            "geo_country": "",
            "asn": "",
        })

    # Sort records chronologically
    records.sort(key=lambda r: r["timestamp"])

    # Write to CSV
    if output_path is None:
        output_path = Path("data/raw/synthetic_bitcoin_demo.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "timestamp",
        "src_ip",
        "dst_ip",
        "src_port",
        "dst_port",
        "txid",
        "input_addresses",
        "input_amounts",
        "output_addresses",
        "output_amounts",
        "fee",
        "script_type",
        "geo_country",
        "asn",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate realistic synthetic Bitcoin transaction dataset.")
    parser.add_argument("--count", type=int, default=700, help="Approximate record count (default: 700)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--output", type=str, default="data/raw/synthetic_bitcoin_demo.csv", help="Output CSV path")
    args = parser.parse_args()

    out_file = generate_synthetic_dataset(
        target_count=args.count,
        seed=args.seed,
        output_path=Path(args.output),
    )
    print(f"Successfully generated synthetic dataset with seed {args.seed}: {out_file}")


if __name__ == "__main__":
    main()
