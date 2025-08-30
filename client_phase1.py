# client_phase1_full.py — Drives all Phase-1 endpoints and writes a report
# Run:
#   pip install requests cryptography python-dotenv
#   python client_phase1_full.py
#
# Set TRY_ANCHOR=1 to call /anchor at the end (server must have chain env set)

import os, json, requests
from datetime import datetime, UTC, timedelta
from typing import Tuple

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

BASE = os.getenv("PHASE1_BASE_URL", "http://127.0.0.1:5000/api/v1")
REPORT = "phase1_full_report.md"
TRY_ANCHOR = os.getenv("TRY_ANCHOR", "0") == "1"

def canonical_json(d: dict) -> str:
    return json.dumps(d, separators=(",", ":"), sort_keys=True)

def iso_now(): return datetime.now(UTC).isoformat()

def md(line=""):
    with open(REPORT, "a", encoding="utf-8") as f: f.write(line+"\n")

def block(title: str, obj):
    md(f"### {title}")
    if isinstance(obj, (dict, list)):
        md("```json"); md(json.dumps(obj, indent=2, default=str)); md("```")
    else:
        md(str(obj))
    md()

def ed_keys() -> Tuple[str,str]:
    priv = Ed25519PrivateKey.generate()
    pub  = priv.public_key()
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

def sign_hex(priv_pem: str, msg: bytes) -> str:
    priv = serialization.load_pem_private_key(priv_pem.encode(), password=None)
    return priv.sign(msg).hex()

def POST(path: str, body=None, files=None):
    url = f"{BASE}{path}"
    if files:
        r = requests.post(url, files=files, timeout=90)
    else:
        r = requests.post(url, json=(body or {}), timeout=60)
    try: data = r.json()
    except: data = {"_raw": r.text}
    if r.status_code >= 400: raise RuntimeError(f"POST {path} {r.status_code}: {data}")
    return data

def GET(path: str):
    url = f"{BASE}{path}"
    r = requests.get(url, timeout=60)
    try: data = r.json()
    except: data = {"_raw": r.text}
    if r.status_code >= 400: raise RuntimeError(f"GET {path} {r.status_code}: {data}")
    return data

def main():
    if os.path.exists(REPORT): os.remove(REPORT)
    md(f"# Phase-1 Full Run"); md(f"- Base: `{BASE}`"); md(f"- Time: `{iso_now()}`\n")

    # 0) Health
    block("Health", GET("/health"))

    # 1) Accounts (producer, buyer)
    prod_priv, prod_pub = ed_keys()
    buy_priv,  buy_pub  = ed_keys()

    acc_prod = POST("/accounts", {"name":"GreenCo", "role":"producer", "public_key_pem": prod_pub})
    acc_buy  = POST("/accounts", {"name":"SteelCo", "role":"buyer",    "public_key_pem": buy_pub})
    block("Producer Account", acc_prod)
    block("Buyer Account", acc_buy)
    producer_id = acc_prod["id"]; buyer_id = acc_buy["id"]

    # 2) Sensor
    sensor_priv, sensor_pub = ed_keys()
    electrolyzer_id = f"ELX-{datetime.now(UTC).timestamp():.0f}"  # unique to avoid overlap across runs
    sensor = POST("/sensors", {
        "name": "StackMeter-01",
        "electrolyzer_id": electrolyzer_id,
        "owner_account_id": producer_id,
        "public_key_pem": sensor_pub
    })
    block("Sensor", sensor)
    sensor_id = sensor["id"]

    # 3) Evidence upload (create a small CSV if not present)
    evpath = "evidence_full.csv"
    if not os.path.exists(evpath):
        with open(evpath, "w", encoding="utf-8") as f:
            f.write("timestamp,voltage,current\n")
            f.write("2025-08-29T10:00:00Z,420,50\n")
            f.write("2025-08-29T12:00:00Z,415,49\n")
    evid = POST("/evidence/upload", files={"file": (os.path.basename(evpath), open(evpath,"rb"), "application/octet-stream")})
    block("Evidence", evid)
    evidence_id = evid["id"]

    # 4) Signed event (fresh window avoids overlap)
    st = datetime.now(UTC).replace(microsecond=0)
    en = st + timedelta(hours=2)
    event_payload = {
        "sensor_id": sensor_id,
        "start_time": st.isoformat().replace("+00:00",""),
        "end_time":   en.isoformat().replace("+00:00",""),
        "energy_kwh": 1000.0,
        "hydrogen_kg": 20.0,
        "evidence_id": evidence_id
    }
    canonical = canonical_json(event_payload)
    sensor_sig = sign_hex(sensor_priv, canonical.encode())
    block("Event Canonical (Signed by Sensor)", event_payload)
    block("Sensor Signature", sensor_sig)

    evt = POST("/events", {**event_payload, "sensor_signature_hex": sensor_sig})
    block("Event Submitted", evt)
    if not evt.get("verified"):
        block("ABORT: Event not verified", {"signature_valid":evt.get("signature_valid"), "overlap_ok":evt.get("overlap_ok")})
        raise SystemExit("Event not verified; fix inputs.")
    event_id = evt["id"]

    # 5) Mint credits (1g) -> pending
    minted = POST("/credits/mint", {"event_id": event_id})
    block("Minted (pending)", minted)
    credit_id = minted["credit_id"]

    # 6) Balances before transfer
    bal_prod_pre = GET(f"/accounts/{producer_id}/balance")
    bal_buy_pre  = GET(f"/accounts/{buyer_id}/balance")
    block("Producer Balance (pre)", bal_prod_pre)
    block("Buyer Balance (pre)", bal_buy_pre)

    # 7) Transfer (partial) to buyer – owner signs
    amount_g = 5000  # 5kg
    tx_payload = {"credit_id": credit_id, "from_account_id": producer_id, "to_account_id": buyer_id, "amount_g": amount_g}
    tx_sig = sign_hex(prod_priv, canonical_json(tx_payload).encode())
    block("Transfer Canonical", tx_payload)
    block("Transfer Signature (producer)", tx_sig)
    tx_res = POST("/credits/transfer", {**tx_payload, "owner_signature_hex": tx_sig})
    block("Transfer Result", tx_res)

    # 8) Retire by buyer (partial)
    retire_payload = {"credit_id": tx_res["to_credit_id"], "owner_account_id": buyer_id, "amount_g": 3000, "reason": "green steel batch A"}
    retire_sig = sign_hex(buy_priv, canonical_json(retire_payload).encode())
    block("Retire Canonical", retire_payload)
    block("Retire Signature (buyer)", retire_sig)
    ret = POST("/credits/retire", {**retire_payload, "owner_signature_hex": retire_sig})
    block("Retire Result", ret)

    # 9) Balances after transfer & retire
    bal_prod = GET(f"/accounts/{producer_id}/balance")
    bal_buy  = GET(f"/accounts/{buyer_id}/balance")
    block("Producer Balance (post)", bal_prod)
    block("Buyer Balance (post)", bal_buy)

    # 10) Close a block (batch -> Merkle)
    closed = POST("/blocks/close", {"note": "phase-1 full batch"})
    block("Block Closed (Merkle)", closed)

    # 11) Latest block
    latest = GET("/blocks/latest")
    block("Latest Block", latest)
    latest_block_id = latest.get("block_id")

    # 12) Optional: Anchor
    if TRY_ANCHOR and latest_block_id:
        anch = POST(f"/blocks/{latest_block_id}/anchor", {})
        block("Anchor Result", anch)
    else:
        block("Anchor Skipped", {"reason": "TRY_ANCHOR not set or no block"})

    # 13) List events (final)
    events = GET("/events")
    block("All Events", events)

    print("✔ Phase-1 full flow ok. See", REPORT)
    print("IDs:", {"producer":producer_id,"buyer":buyer_id,"sensor":sensor_id,"evidence":evidence_id,"event":event_id,"credit":credit_id})

if __name__ == "__main__":
    main()
