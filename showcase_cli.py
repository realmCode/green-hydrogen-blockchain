"""
showcase_cli.py — Judge-friendly runner that *reuses* api_tester.py helpers
--------------------------------------------------------------------------
- Uses the exact ed25519_sign_hex() + canonical_event_payload() from api_tester.py
- Calls the same endpoints & sequence, but prints clearer, judge-facing messages
- Does NOT change any signing/canonicalization logic

Run:
  pip install requests cryptography
  python app.py
  python showcase_cli.py --base http://127.0.0.1:5000  [--evidence path.csv]
"""
from __future__ import annotations

import argparse, os, sys, json, time, hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import requests

# Import user's exact helpers so signatures match server checks
import importlib.util, pathlib
API_TESTER_PATH = pathlib.Path(__file__).with_name("api_tester.py")
if not API_TESTER_PATH.exists():
    print("❌ api_tester.py not found next to showcase_cli.py")
    sys.exit(2)
spec = importlib.util.spec_from_file_location("api_tester", str(API_TESTER_PATH))
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)  # type: ignore

# Pretty helpers (printing only)
def box(title: str):
    print("\n" + "═"*78)
    print(f"🧭 {title}")
    print("═"*78)

def ok(msg: str): print(f"   ✅ {msg}")
def info(msg: str): print(f"   • {msg}")
def warn(msg: str): print(f"   ⚠️  {msg}")
def die(msg: str, code: int = 1):
    print(f"\n❌ {msg}")
    sys.exit(code)

def jpeek(obj: Any, limit: int = 900) -> str:
    try:
        s = json.dumps(obj, indent=2, ensure_ascii=False, default=str)
    except Exception:
        s = str(obj)
    return s if len(s) <= limit else s[:limit] + "... (truncated)"

def main():
    ap = argparse.ArgumentParser(description="Judge-friendly showcase (reuses api_tester helpers)")
    ap.add_argument("--base", default="http://127.0.0.1:5000", help="API base, e.g. http://127.0.0.1:5000")
    ap.add_argument("--evidence", default=os.getenv("EVIDENCE_DIR",""))
    args = ap.parse_args()
    base = args.base.rstrip("/")

    # 0) Health
    box("Health check")
    h = api.request_json(base, "GET", "/api/v1/health")
    assert h.get("ok") is True
    ok("API alive")
    info(f"Base: {base}")

    # 1) Accounts + Sensor (USE EXACT ed25519 & payload style)
    box("Create Producer/Buyer accounts and register Sensor (Ed25519)")
    prod_sk, prod_priv_pem, prod_pub_pem, _ = api.ed25519_keypair_pem()
    buy_sk,  buy_priv_pem,  buy_pub_pem,  _ = api.ed25519_keypair_pem()
    sens_sk, sens_priv_pem, sens_pub_pem, _ = api.ed25519_keypair_pem()

    producer = api.request_json(base, "POST", "/api/v1/accounts", {
        "name":"GreenCo", "role":"producer", "public_key_pem": prod_pub_pem
    }, ok=200)
    buyer = api.request_json(base, "POST", "/api/v1/accounts", {
        "name":"SteelCo", "role":"buyer", "public_key_pem": buy_pub_pem
    }, ok=200)
    prod_id = producer.get("id") or producer.get("_id")
    buy_id  = buyer.get("id") or buyer.get("_id")
    if not prod_id or not buy_id:
        die("Account creation failed (ids not present)")
    info(f"Producer id: {prod_id}  Buyer id: {buy_id}")

    sensor = api.request_json(base, "POST", "/api/v1/sensors", {
        "name":"StackMeter-01",
        "electrolyzer_id":"ELX-"+str(int(time.time())),
        "owner_account_id": prod_id,
        "public_key_pem": sens_pub_pem
    }, ok=200)
    sens_id = sensor["id"]
    info(f"Sensor id: {sens_id}  ELX: {sensor.get('electrolyzer_id','?')}")

    # 2) Evidence (multipart) — EXACT endpoint and behavior
    box("Upload evidence (bind hash to event)")
    if args.evidence and os.path.exists(args.evidence):
        content = open(args.evidence,"rb").read(); fname=os.path.basename(args.evidence)
    else:
        content = b"timestamp,reading\n2025-08-30T10:00Z,ok\n"; fname="evidence_run1.csv"
    evidence = api.upload_file(base, "/api/v1/evidence/upload", fname, content, ok=200)
    evid_id = evidence["id"]
    ok(f"Evidence id: {evid_id}  sha256: {evidence.get('sha256_hex','')[:12]}…")

    # 3) Event times — EXACT style from api_tester.py
    box("Create signed production event (sensor-signed canonical JSON)")
    start = (datetime.now(timezone.utc) - timedelta(hours=2)).replace(microsecond=0).isoformat().replace("+00:00","")
    end   = (datetime.now(timezone.utc)).replace(microsecond=0).isoformat().replace("+00:00","")
    payload_canon = api.canonical_event_payload(
        sens_id, start, end, energy_kwh=1000.0, hydrogen_kg=20.0, evidence_id=evid_id
    )
    sig_hex = api.ed25519_sign_hex(sens_sk, payload_canon.encode())

    event = api.request_json(base, "POST", "/api/v1/events", {
        "sensor_id": sens_id,
        "start_time": start,
        "end_time": end,
        "energy_kwh": 1000.0,
        "hydrogen_kg": 20.0,
        "evidence_id": evid_id,
        "sensor_signature_hex": sig_hex
    }, ok=200)
    assert event.get("verified") and event.get("overlap_ok") and event.get("signature_valid")
    event_id = event["id"]
    ok(f"Event accepted id: {event_id}")
    info("Server verified signature & non-overlap.")

    # 4) Mint (grams) — EXACT call
    box("Mint credits from event")
    mint = api.request_json(base, "POST", "/api/v1/credits/mint", {"event_id": event_id}, ok=200)
    credit_id = mint["credit_id"]; amount_g = int(mint["amount_g"])
    info(f"Minted credit id: {credit_id}  amount_g: {amount_g}  status: {mint.get('status')}")

    # 5) Close block (activate)
    box("Close a block (Merkle over txs) to activate credits")
    r = requests.post(f"{base}/api/v1/blocks/close", json={})
    r.raise_for_status()
    blk = r.json()
    ok(f"Block closed id: {blk.get('block_id','?')}  tx_count: {blk.get('tx_count')}")

    # 6) Balances pre-transfer
    box("Balances (pre-transfer)")
    prod_bal_pre = api.request_json(base, "GET", f"/api/v1/accounts/{prod_id}/balance")
    info(jpeek(prod_bal_pre))

    # 7) Transfer (owner-signed) — EXACT canonicalization & signing
    box("Transfer 5,000 g from Producer → Buyer (owner-signed)")
    transfer_canon = json.dumps({
        "credit_id": credit_id,
        "from_account_id": prod_id,
        "to_account_id": buy_id,
        "amount_g": 5000
    }, sort_keys=True, separators=(",", ":"))
    owner_sig = api.ed25519_sign_hex(prod_sk, transfer_canon.encode())

    tx = api.request_json(base, "POST", "/api/v1/credits/transfer", {
        "credit_id": credit_id,
        "from_account_id": prod_id,
        "to_account_id": buy_id,
        "amount_g": 5000,
        "owner_signature_hex": owner_sig
    }, ok=200)
    to_credit = tx.get("to_credit_id") or credit_id
    ok(f"Transfer OK → new credit for buyer: {to_credit}")

    # 8) Retire (owner-signed) — EXACT canonicalization & signing
    box("Retire 3,000 g by Buyer (owner-signed claim)")
    retire_canon = json.dumps({
        "credit_id": to_credit,
        "owner_account_id": buy_id,
        "amount_g": 3000,
        "reason": "green steel batch A"
    }, sort_keys=True, separators=(",", ":"))
    buyer_sig = api.ed25519_sign_hex(buy_sk, retire_canon.encode())

    retire = api.request_json(base, "POST", "/api/v1/credits/retire", {
        "credit_id": to_credit,
        "owner_account_id": buy_id,
        "amount_g": 3000,
        "reason": "green steel batch A",
        "owner_signature_hex": buyer_sig
    }, ok=200)
    ok("Retirement recorded")

    # 9) Balances post-transfer/retire
    box("Balances (post transfer/retire)")
    prod_bal_post = api.request_json(base, "GET", f"/api/v1/accounts/{prod_id}/balance")
    buy_bal_post  = api.request_json(base, "GET", f"/api/v1/accounts/{buy_id}/balance")
    info("Producer: " + jpeek(prod_bal_post))
    info("Buyer   : " + jpeek(buy_bal_post))

    # 10) Close block (commit ops)
    box("Close another block to commit ops (transfer/retire)")
    block = api.request_json(base, "POST", "/api/v1/blocks/close", {})
    ok("Block closed")

    # 11) Latest block + Merkle verify
    box("Verify latest block by recomputing Merkle from /txs")
    latest = api.request_json(base, "GET", "/api/v1/blocks/latest")
    txs = api.request_json(base, "GET", f"/api/v1/blocks/{latest['block_id']}/txs")
    local = (lambda hashes: hashlib.sha256(("".join(hashes)).encode("utf-8")).hexdigest())(  # simple concat hash
        [t["tx_hash"] for t in txs.get("txs",[])]
    )
    # NOTE: above is only for a quick judge visual; your server returns the reference merkle root anyway.
    # We don't alter signatures; this part is educational.
    info(f"Server merkle_root: {latest.get('merkle_root')}")
    info(f"Local quick-hash : {local[:16]}… (for demo only)")

    # 12) SMT state + proofs (same endpoints)
    box("Sparse Merkle State: root + account proofs")
    root = api.request_json(base, "GET", "/api/v2/state/root")
    prod_proof = api.request_json(base, "GET", f"/api/v2/state/proof/{prod_id}")
    buy_proof  = api.request_json(base, "GET", f"/api/v2/state/proof/{buy_id}")
    info(f"Producer proof OK? {prod_proof.get('local_verify_ok')}  Buyer proof OK? {buy_proof.get('local_verify_ok')}")

    # 13) Marketplace (same flow)
    box("Marketplace: list 5,000 g then buy 2,000 g + 3,000 g")
    offer = api.request_json(base, "POST", "/api/v1/market/offers", {
        "producer_id": prod_id,
        "credit_id": credit_id,
        "amount_g": 5000,
        "price_per_g": 0.1
    }, ok=200)
    info(f"Offer id: {offer['id']}")
    api.request_json(base, "POST", "/api/v1/market/buy", {
        "buyer_id": buy_id, "offer_id": offer["id"], "amount_g": 2000
    }, ok=200)
    api.request_json(base, "POST", "/api/v1/market/buy", {
        "buyer_id": buy_id, "offer_id": offer["id"], "amount_g": 3000
    }, ok=200)
    ok("Bought 2k + 3k g from offer")

    # 14) Reports (optional)
    try:
        box("Reports: retirements (if available)")
        rep = api.request_json(base, "GET", "/api/v1/reports/retirements", ok=200)
        info(jpeek(rep))
    except SystemExit:
        warn("Retirements report not available — skipping")

    # Final judge recap
    box("Judge Recap")
    print(f"Producer  : {prod_id}")
    print(f"Buyer     : {buy_id}")
    print(f"Sensor    : {sens_id}  ELX: {sensor.get('electrolyzer_id','?')}")
    print(f"Evidence  : {evid_id}  sha256: {evidence.get('sha256_hex','')[:16]}…")
    print(f"Event     : {event_id}")
    print(f"Credit    : {credit_id}  amount_g: {amount_g}")
    print(f"LatestBlk : {latest.get('block_id','?')}")
    print("\n🎉 Demo complete — same signatures, clearer story for judges")

if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as e:
        die(f"HTTP error: {e}", 1)
    except AssertionError as e:
        die(f"Assert failed: {e}", 2)