# tester_all_phases.py
# Full E2E tester for Phase-1/2/3 with proper evidence upload (multipart)
#
# Run:
#   python tester_all_phases.py --base http://127.0.0.1:5000
#
# Optional:
#   --rpc https://sepolia.infura.io/v3/<KEY> --contract 0xYourAnchor [--anchor-state]

import argparse, json, sys, time, hashlib, os
from datetime import datetime, timedelta, timezone
import requests

# ---- tiny utils -------------------------------------------------------------

def p(obj): print(json.dumps(obj, indent=2))
def die(msg, code=2): print("❌", msg); sys.exit(code)

def must(resp, expected=200):
    """Accept both 200/201 as success; still allow specifying 'expected'."""
    if resp.status_code not in (expected, 200, 201):
        try: body = resp.json()
        except Exception: body = resp.text
        die(f"[{resp.request.method} {resp.request.url}] "
            f"expected {expected} (or 200/201), got {resp.status_code}\n{body}", 1)
    try:
        return resp.json()
    except Exception:
        die("Response is not JSON", 1)

def norm0x(h: str) -> str:
    h = (h or "").lower()
    if h.startswith("0x"): h = h[2:]
    return h.zfill(64)

def sha256_hex_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def ed25519_keypair_pem():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    sk = Ed25519PrivateKey.generate()
    pk = sk.public_key()
    priv_pem = sk.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption())
    pub_pem = pk.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)
    return sk, priv_pem.decode(), pub_pem.decode(), pk

def ed25519_sign_hex(sk, msg_bytes: bytes) -> str:
    sig = sk.sign(msg_bytes)
    return sig.hex()

def canonical_event_payload(sensor_id, start_time, end_time, energy_kwh, hydrogen_kg, evidence_id):
    d = {
        "energy_kwh": float(energy_kwh),
        "evidence_id": str(evidence_id),
        "hydrogen_kg": float(hydrogen_kg),
        "end_time": end_time,
        "sensor_id": str(sensor_id),
        "start_time": start_time
    }
    return json.dumps(d, sort_keys=True, separators=(",", ":"))

def request_json(base, method, path, payload=None, ok=200):
    url = base.rstrip("/") + path
    r = requests.request(method, url, json=payload, timeout=60)
    return must(r, ok)

def upload_file(base, path, filename: str, content: bytes, ok=200):
    """multipart/form-data file upload"""
    url = base.rstrip("/") + path
    files = {"file": (filename, content, "application/octet-stream")}
    r = requests.post(url, files=files, timeout=60)
    return must(r, ok)

# ---- main -------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Full E2E tester (Phase-1/2/3)")
    ap.add_argument("--base", required=True, help="API base, e.g. http://127.0.0.1:5000")
    ap.add_argument("--rpc", help="Ethereum RPC (optional)")
    ap.add_argument("--contract", help="Anchor contract address (optional)")
    ap.add_argument("--anchor-state", action="store_true", help="Call /api/v2/state/anchor on server")
    args = ap.parse_args()

    base = args.base.rstrip("/")

    print("== E2E Tester (Phase-1/2/3) ==")
    print("Base:", base)
    print("Time:", datetime.now(timezone.utc).isoformat())

    # Health
    health = request_json(base, "GET", "/api/v1/health")
    assert health.get("ok") is True
    print("Health OK")

    # --- Phase 1: accounts, sensor, evidence, event, mint, transfer, retire, block close

    # Create producer & buyer (Ed25519 keys)
    prod_sk, prod_priv_pem, prod_pub_pem, _ = ed25519_keypair_pem()
    buy_sk,  buy_priv_pem,  buy_pub_pem,  _ = ed25519_keypair_pem()
    sens_sk, sens_priv_pem, sens_pub_pem, _ = ed25519_keypair_pem()

    producer = request_json(base, "POST", "/api/v1/accounts", {
        "name": "GreenCo", "role": "producer", "public_key_pem": prod_pub_pem
    }, ok=200)
    buyer = request_json(base, "POST", "/api/v1/accounts", {
        "name": "SteelCo", "role": "buyer", "public_key_pem": buy_pub_pem
    }, ok=200)
    prod_id = producer.get("id") or producer.get("_id"); assert prod_id
    buy_id  = buyer.get("id") or buyer.get("_id"); assert buy_id
    print("Producer id:", prod_id)
    print("Buyer id   :", buy_id)

    sensor = request_json(base, "POST", "/api/v1/sensors", {
        "name": "StackMeter-01",
        "electrolyzer_id": "ELX-" + str(int(time.time())),
        "owner_account_id": prod_id,
        "public_key_pem": sens_pub_pem
    }, ok=200)
    sens_id = sensor["id"]; print("Sensor id  :", sens_id)

    # ---- Evidence (multipart upload to /api/v1/evidence/upload) ----
    evidence_bytes = b"timestamp,reading\n2025-08-30T10:00Z,ok\n"
    evidence = upload_file(base, "/api/v1/evidence/upload", "evidence_run1.csv", evidence_bytes, ok=200)
    evid_id = evidence["id"]; print("Evidence id:", evid_id)

    # Signed event
    start = (datetime.now(timezone.utc) - timedelta(hours=2)).replace(microsecond=0).isoformat().replace("+00:00","")
    end   = (datetime.now(timezone.utc)).replace(microsecond=0).isoformat().replace("+00:00","")
    payload_canon = canonical_event_payload(
        sens_id, start, end, energy_kwh=1000.0, hydrogen_kg=20.0, evidence_id=evid_id
    )
    sig_hex = ed25519_sign_hex(sens_sk, payload_canon.encode())

    event = request_json(base, "POST", "/api/v1/events", {
        "sensor_id": sens_id,
        "start_time": start,
        "end_time": end,
        "energy_kwh": 1000.0,
        "hydrogen_kg": 20.0,
        "evidence_id": evid_id,
        "sensor_signature_hex": sig_hex
    }, ok=200)
    assert event.get("verified") is True and event.get("overlap_ok") is True and event.get("signature_valid") is True
    event_id = event["id"]
    print("Event OK:", event_id)

    # Mint (grams expected by your app)
    mint = request_json(base, "POST", "/api/v1/credits/mint", {"event_id": event_id}, ok=200)
    credit_id = mint["credit_id"]; amount_g = int(mint["amount_g"])
    assert amount_g in (20000, 20)
    print("Minted credit:", credit_id, "amount_g:", amount_g, "status:", mint.get("status"))

    r = requests.post(f"{base}/api/v1/blocks/close", json={})
    r.raise_for_status()    
    blk = r.json()
    print(blk)
    # Producer balance pre
    prod_bal_pre = request_json(base, "GET", f"/api/v1/accounts/{prod_id}/balance")
    print("Producer balance (pre):"); p(prod_bal_pre)

    # Transfer 5 000 g to buyer (owner_signature)
    transfer_canon = json.dumps({
        "credit_id": credit_id,
        "from_account_id": prod_id,
        "to_account_id": buy_id,
        "amount_g": 5000
    }, sort_keys=True, separators=(",", ":"))
    owner_sig = ed25519_sign_hex(prod_sk, transfer_canon.encode())

    tx = request_json(base, "POST", "/api/v1/credits/transfer", {
        "credit_id": credit_id,
        "from_account_id": prod_id,
        "to_account_id": buy_id,
        "amount_g": 5000,
        "owner_signature_hex": owner_sig
    }, ok=200)
    print("Transfer result:"); p(tx)

    # Retire 3 000 g by buyer (owner_signature)
    retire_canon = json.dumps({
        "credit_id": tx.get("to_credit_id") or tx.get("credit_id") or credit_id,
        "owner_account_id": buy_id,
        "amount_g": 3000,
        "reason": "green steel batch A"
    }, sort_keys=True, separators=(",", ":"))
    buyer_sig = ed25519_sign_hex(buy_sk, retire_canon.encode())

    retire = request_json(base, "POST", "/api/v1/credits/retire", {
        "credit_id": tx.get("to_credit_id") or credit_id,
        "owner_account_id": buy_id,
        "amount_g": 3000,
        "reason": "green steel batch A",
        "owner_signature_hex": buyer_sig
    }, ok=200)
    print("Retire result:"); p(retire)

    # Producer & Buyer balances post
    prod_bal_post = request_json(base, "GET", f"/api/v1/accounts/{prod_id}/balance")
    buy_bal_post  = request_json(base, "GET", f"/api/v1/accounts/{buy_id}/balance")
    print("Producer balance (post):"); p(prod_bal_post)
    print("Buyer balance (post):"); p(buy_bal_post)

    # Close block (your server may auto-anchor; if not, it still returns block info)
    block = request_json(base, "POST", "/api/v1/blocks/close", {})
    print("Block closed:"); p(block)

    latest = request_json(base, "GET", "/api/v1/blocks/latest")
    print("Latest block:"); p(latest)
    if latest.get("anchor_tx"): print("Anchor TX:", latest["anchor_tx"])
    else: print("Anchor skipped (ENV not set on server)")

    # --- Phase 2: SMT state + proofs (+ optional anchor/verify) ----------------

    root = request_json(base, "GET", "/api/v2/state/root")
    print("State root:"); p(root)
    prod_proof = request_json(base, "GET", f"/api/v2/state/proof/{prod_id}")
    buy_proof  = request_json(base, "GET", f"/api/v2/state/proof/{buy_id}")
    assert prod_proof.get("local_verify_ok") is True
    assert buy_proof.get("local_verify_ok") is True
    print("Producer proof OK, Buyer proof OK")

    if args.anchor_state:
        anch = request_json(base, "POST", "/api/v2/state/anchor", {}, ok=200)
        print("Anchored state:", anch.get("tx"))
        onchain_block_id = anch.get("onchain_block_id")
    else:
        onchain_block_id = None

    if args.rpc and args.contract:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(args.rpc))
        abi = [{
          "inputs":[{"internalType":"uint256","name":"blockId","type":"uint256"}],
          "name":"roots","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],
          "stateMutability":"view","type":"function"
        }]
        c = w3.eth.contract(address=Web3.to_checksum_address(args.contract), abi=abi)
        local_root = root.get("state_root")
        if onchain_block_id is None:
            import hashlib
            raw = norm0x(local_root)
            onchain_block_id = int(hashlib.sha256(("smt|" + raw).encode()).hexdigest(), 16) % (2**256)
        chain_root = c.functions.roots(int(onchain_block_id)).call()
        try: chain_hex = chain_root.hex()
        except Exception: chain_hex = Web3.to_hex(chain_root)
        print("On-chain root:", chain_hex)
        print("Local  root  :", local_root)
        print("Match?       :", norm0x(chain_hex)==norm0x(local_root))

    # --- Phase 3: Marketplace list/buy ----------------------------------------

    # Pick a non-retired producer credit with available grams
    # If you don't have a credits listing endpoint, we’ll reuse 'credit_id' from mint.
    sell_credit_id = credit_id

    offer = request_json(base, "POST", "/api/v1/market/offers", {
        "producer_id": prod_id,
        "credit_id": sell_credit_id,
        "amount_g": 5000,
        "price_per_g": 0.1
    }, ok=200)
    print("Offer listed:"); p(offer)
    offer_id = offer["id"]

    # Buyer partial purchase (2 000 g)
    buy1 = request_json(base, "POST", "/api/v1/market/buy", {
        "buyer_id": buy_id,
        "offer_id": offer_id,
        "amount_g": 2000
    }, ok=200)
    print("Buy #1:"); p(buy1)

    # Finalize remaining (3 000 g)
    buy2 = request_json(base, "POST", "/api/v1/market/buy", {
        "buyer_id": buy_id, "offer_id": offer_id, "amount_g": 3000
    }, ok=200)
    print("Buy #2:"); p(buy2)

    # Balances after market
    prod_bal_market = request_json(base, "GET", f"/api/v1/accounts/{prod_id}/balance")
    buy_bal_market  = request_json(base, "GET", f"/api/v1/accounts/{buy_id}/balance")
    print("Producer balance (after market):"); p(prod_bal_market)
    print("Buyer balance (after market):"); p(buy_bal_market)

    # Retirements feed
    rep = request_json(base, "GET", "/api/v1/reports/retirements")
    print("Retirements report sample:")
    p(rep if len(json.dumps(rep)) < 1500 else {"note":"large payload ok"})

    print("\n✅ ALL CHECKS PASSED")
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as e:
        die(f"HTTP error: {e}", 1)
    except AssertionError as e:
        die(f"Assert failed: {e}", 2)
