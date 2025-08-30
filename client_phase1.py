# client_phase1_full.py
# End-to-end tester for your Flask+Mongo Phase-1 registry.
# Generates: phase1_full_report.md with all requests/responses and signatures.

import os
import json
import time
import requests
from dataclasses import dataclass
from typing import Optional, Tuple
from datetime import datetime, UTC

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

BASE_URL = os.getenv("PHASE1_BASE_URL", "http://127.0.0.1:5000")
REPORT_MD = "phase1_full_report.md"

# Optional anchoring (only used if your server has /blocks/<id>/anchor enabled AND env set server-side)
TRY_ANCHOR = os.getenv("TRY_ANCHOR", "0") == "1"

# ----------------- Helpers -----------------
def canonical_json(data: dict) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)

def iso_now() -> str:
    return datetime.now(UTC).isoformat()

def md_line(text: str):
    with open(REPORT_MD, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def md_block(title: str, obj):
    md_line(f"### {title}")
    if isinstance(obj, (dict, list)):
        md_line("```json")
        md_line(json.dumps(obj, indent=2, default=str))
        md_line("```")
    else:
        md_line(str(obj))
    md_line("")

def ed25519_generate() -> Tuple[str, str]:
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()
    return priv_pem, pub_pem

def ed25519_sign_hex(priv_pem: str, msg: bytes) -> str:
    priv = serialization.load_pem_private_key(priv_pem.encode(), password=None)
    return priv.sign(msg).hex()

def post_json(path: str, body: dict):
    r = requests.post(f"{BASE_URL}{path}", json=body, timeout=60)
    try:
        data = r.json()
    except Exception:
        data = {"_raw": r.text}
    if r.status_code >= 400:
        raise RuntimeError(f"POST {path} failed {r.status_code}: {data}")
    return data

def get_json(path: str):
    r = requests.get(f"{BASE_URL}{path}", timeout=60)
    try:
        data = r.json()
    except Exception:
        data = {"_raw": r.text}
    if r.status_code >= 400:
        raise RuntimeError(f"GET {path} failed {r.status_code}: {data}")
    return data

def upload_evidence(filepath: str):
    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f, "application/octet-stream")}
        r = requests.post(f"{BASE_URL}/evidence/upload", files=files, timeout=120)
    try:
        data = r.json()
    except Exception:
        data = {"_raw": r.text}
    if r.status_code >= 400:
        raise RuntimeError(f"UPLOAD /evidence/upload failed {r.status_code}: {data}")
    return data

# ----------------- Main flow -----------------
def main():
    if os.path.exists(REPORT_MD):
        os.remove(REPORT_MD)
    md_line(f"# Phase-1 Full Client Run")
    md_line(f"- Timestamp: `{iso_now()}`")
    md_line(f"- Base URL: `{BASE_URL}`\n")

    # 0) Health
    health = get_json("/health")
    md_block("Health", health)

    # 1) Accounts (producer, buyer) with real Ed25519 keys
    producer_priv, producer_pub = ed25519_generate()
    buyer_priv, buyer_pub = ed25519_generate()

    acc_prod = post_json("/accounts", {
        "name": "GreenCo",
        "role": "producer",
        "public_key_pem": producer_pub
    })
    acc_buy = post_json("/accounts", {
        "name": "SteelCo",
        "role": "buyer",
        "public_key_pem": buyer_pub
    })
    md_block("Account Created (Producer)", acc_prod)
    md_block("Account Created (Buyer)", acc_buy)

    producer_id = acc_prod["id"]
    buyer_id = acc_buy["id"]

    # 2) Sensor with its own keypair
    sensor_priv, sensor_pub = ed25519_generate()
    sensor = post_json("/sensors", {
        "name": "StackMeter-01",
        "electrolyzer_id": "ELX-001",
        "owner_account_id": producer_id,
        "public_key_pem": sensor_pub
    })
    md_block("Sensor Registered", sensor)
    sensor_id = sensor["id"]

    # 3) Evidence upload
    evid_path = "evidence_run.csv"
    if not os.path.exists(evid_path):
        with open(evid_path, "w", encoding="utf-8") as f:
            f.write("timestamp,voltage,current\n")
            f.write("2025-08-29T10:00:00Z,420,50\n")
            f.write("2025-08-29T12:00:00Z,415,49\n")
    evid = upload_evidence(evid_path)
    md_block("Evidence Uploaded", evid)
    evidence_id = evid["id"]

    # 4) Signed Event (canonical JSON + sensor signature)
    start_time = "2025-08-29T10:00:00"
    end_time   = "2025-08-29T12:00:00"
    event_payload = {
        "sensor_id": sensor_id,
        "start_time": start_time,
        "end_time": end_time,
        "energy_kwh": 1000.0,
        "hydrogen_kg": 20.0,
        "evidence_id": evidence_id
    }
    canonical = canonical_json(event_payload)
    sensor_sig = ed25519_sign_hex(sensor_priv, canonical.encode())

    md_block("Canonical Payload (to be signed by Sensor)", event_payload)
    md_block("Sensor Signature (hex)", sensor_sig)

    evt = post_json("/events", {**event_payload, "sensor_signature_hex": sensor_sig})
    md_block("Event Submitted", evt)
    event_id = evt["id"]

    # 5) Mint credits (1 credit = 1 gram) → to producer
    minted = post_json("/mint", {"event_id": event_id})
    md_block("Credits Minted", minted)
    credit_id = minted["credit_id"]

    # 6) Balances (before transfer)
    bal_prod_before = get_json(f"/accounts/{producer_id}/balance")
    bal_buy_before  = get_json(f"/accounts/{buyer_id}/balance")
    md_block("Producer Balance (before transfer)", bal_prod_before)
    md_block("Buyer Balance (before transfer)", bal_buy_before)

    # 7) Transfer to buyer (owner-signed by producer)
    transfer_payload = {
        "credit_id": credit_id,
        "from_account_id": producer_id,
        "to_account_id": buyer_id
    }
    transfer_sig = ed25519_sign_hex(producer_priv, canonical_json(transfer_payload).encode())
    md_block("Transfer Canonical Payload", transfer_payload)
    md_block("Transfer Signature (by Producer)", transfer_sig)

    transfer_res = post_json("/transfer", {
        **transfer_payload,
        "owner_signature_hex": transfer_sig
    })
    md_block("Transfer Result", transfer_res)

    # 8) Balances (after transfer; before retire)
    bal_prod_after_transfer = get_json(f"/accounts/{producer_id}/balance")
    bal_buy_after_transfer  = get_json(f"/accounts/{buyer_id}/balance")
    md_block("Producer Balance (after transfer)", bal_prod_after_transfer)
    md_block("Buyer Balance (after transfer)", bal_buy_after_transfer)

    # 9) Retire by buyer (owner-signed by buyer)
    retire_payload = {
        "credit_id": credit_id,
        "owner_account_id": buyer_id,
        "reason": "Used for decarbonized steel"
    }
    retire_sig = ed25519_sign_hex(buyer_priv, canonical_json(retire_payload).encode())
    md_block("Retire Canonical Payload", retire_payload)
    md_block("Retire Signature (by Buyer)", retire_sig)

    retire_res = post_json("/retire", {
        **retire_payload,
        "owner_signature_hex": retire_sig
    })
    md_block("Retire Result", retire_res)

    # 10) Balances (after retire)
    bal_prod_final = get_json(f"/accounts/{producer_id}/balance")
    bal_buy_final  = get_json(f"/accounts/{buyer_id}/balance")
    md_block("Producer Balance (final)", bal_prod_final)
    md_block("Buyer Balance (final)", bal_buy_final)

    # 11) Close a block (batch all pending ledger txs → Merkle root)
    try:
        blk_close = post_json("/blocks/close", {"note": "phase1 full client batch"})
        md_block("Block Closed (Merkle built)", blk_close)
    except RuntimeError as e:
        md_block("Block Close (no pending txs?)", str(e))
        blk_close = None

    # 12) Latest block
    try:
        latest = get_json("/blocks/latest")
        md_block("Latest Block", latest)
        latest_block_id = latest.get("block_id")
    except RuntimeError as e:
        md_block("Latest Block (not found)", str(e))
        latest_block_id = None

    # 13) Optional: anchor latest block (only if TRY_ANCHOR=1 and server supports it)
    if TRY_ANCHOR and latest_block_id:
        try:
            anch = post_json(f"/blocks/{latest_block_id}/anchor", {})
            md_block("Anchor Result", anch)
        except RuntimeError as e:
            md_block("Anchor Attempt (error)", str(e))
    else:
        md_block("Anchor Skipped", {
            "reason": "TRY_ANCHOR not set or no latest block yet"
        })

    # 14) List events (for documentation completeness)
    events = get_json("/events")
    md_block("All Events (latest first)", events)

    print("✔ Phase-1 full flow complete.")
    print(f"Report written to: {REPORT_MD}")
    print("IDs:")
    print("  Producer account:", producer_id)
    print("  Buyer account:", buyer_id)
    print("  Sensor id:", sensor_id)
    print("  Evidence id:", evidence_id)
    print("  Event id:", event_id)
    print("  Credit id:", credit_id)

if __name__ == "__main__":
    main()
