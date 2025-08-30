# app.py  — Phase-1: Flask + Mongo + Ledger + Merkle + Optional Anchor
# Run:
#   pip install flask pymongo cryptography python-dotenv werkzeug web3
#   export MONGODB_URI="mongodb://localhost:27017"
#   export DB_NAME="h2_registry"
#   python app.py
#
# Optional (for anchoring):
#   export WEB3_RPC_URL="https://sepolia.infura.io/v3/<KEY>"
#   export REGISTRY_PRIVATE_KEY="0x..."
#   export ANCHOR_CONTRACT_ADDRESS="0x..."   # CreditAnchor(anchor(blockId, root))
#
# API base: http://127.0.0.1:5000/api/v1

import os, json, hashlib
from datetime import datetime, timezone
from typing import Optional, List

from flask import Flask, request, Response
from werkzeug.utils import secure_filename
from pymongo import MongoClient, ASCENDING
from bson import ObjectId
from dotenv import load_dotenv

# Ed25519
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature


from utils import _signed_raw_bytes, derive_onchain_block_id, _norm0x
###################### phase 2
from phase2.smt_state import DEFAULTS, build_state_root, prove_account, verify_account  # :contentReference[oaicite:4]{index=4}
from web3 import Web3
import os, json, hashlib
# ---------------- Config ----------------
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME      = os.getenv("DB_NAME", "h2_registry")
EVIDENCE_DIR = os.getenv("EVIDENCE_DIR", "evidence_store")
os.makedirs(EVIDENCE_DIR, exist_ok=True)

# Optional chain env
WEB3_RPC_URL = os.getenv("WEB3_RPC_URL")
REG_PK       = os.getenv("PRIVATE_KEY")
ANCHOR_ADDR  = os.getenv("ANCHOR_CONTRACT_ADDRESS")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

# Indexes (idempotent)
db.evidence.create_index("sha256_hex", unique=True)
db.accounts.create_index("name")
db.sensors.create_index([("electrolyzer_id", ASCENDING), ("owner_account_id", ASCENDING)], unique=True)
db.production_events.create_index([("electrolyzer_id", ASCENDING), ("start_time", ASCENDING), ("end_time", ASCENDING)])
db.credits.create_index([("owner_account_id", ASCENDING), ("status", ASCENDING)])
db.ledger_txs.create_index([("block_id", ASCENDING), ("created_at", ASCENDING)])
db.blocks.create_index([("created_at", ASCENDING)])

def _fetch_balances():
    agg = db.credits.aggregate([
        {"$match": {"status": {"$ne": "retired"}}},
        {"$group": {"_id": "$owner_account_id", "g": {"$sum": "$amount_g"}}}
    ])
    balances = {}
    for row in agg:
        balances[str(row["_id"])] = int(row["g"])
    return balances

app = Flask(__name__)

# --------------- JSON helper ---------------
def j(data, status=200):
    return Response(json.dumps(data, default=str), status=status, mimetype="application/json")

# --------------- Helpers ---------------
def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def canonical_json(data: dict) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)

def as_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

def parse_iso(s: str) -> datetime:
    # supports "...Z"
    if s.endswith("Z"):
        s = s[:-1]
    return datetime.fromisoformat(s)

def load_pubkey(pem_text: str) -> Ed25519PublicKey:
    return serialization.load_pem_public_key(pem_text.encode("utf-8"))

def verify_ed25519(pub_pem: str, msg: bytes, sig_hex: str) -> bool:
    try:
        pub = load_pubkey(pub_pem)
        pub.verify(bytes.fromhex(sig_hex), msg)
        return True
    except (InvalidSignature, ValueError):
        return False

# Units: 1 credit = 1 gram
def kg_to_g(kg: float) -> int:
    return int(round(kg * 1000))

# ---------- Merkle (tree hash over tx_hash strings) ----------
def merkle_root(hashes: List[str]) -> str:
    if not hashes: return "0"*64
    layer = hashes[:]
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            a = layer[i]
            b = layer[i+1] if i+1 < len(layer) else a
            nxt.append(sha256_hex((a + b).encode("utf-8")))
        layer = nxt
    return layer[0]

def tx_hash(payload: dict) -> str:
    return sha256_hex(canonical_json(payload).encode("utf-8"))

def ledger_append(tx_type: str, payload: dict) -> str:
    th = tx_hash({"type": tx_type, **payload})
    db.ledger_txs.insert_one({
        "type": tx_type,
        "payload": payload,
        "tx_hash": th,
        "block_id": None,
        "created_at": datetime.utcnow()
    })
    return th

def close_block(note: Optional[str] = None) -> dict:
    pending = list(db.ledger_txs.find({"block_id": None}).sort("created_at", 1))
    if not pending:
        return {"error": "no pending txs to close"}

    tx_hashes = [p["tx_hash"] for p in pending]
    root = merkle_root(tx_hashes)

    prev = db.blocks.find_one(sort=[("_id", -1)])
    prev_hash = prev["merkle_root"] if prev else None
    chain_hash = sha256_hex(((prev_hash or "") + root).encode("utf-8"))

    # create block doc first to get its ObjectId
    blk_doc = {
        "prev_hash": prev_hash,
        "merkle_root": root,
        "chain_hash": chain_hash,
        "tx_count": len(pending),
        "note": note,
        "created_at": datetime.utcnow(),
        "anchor_tx": None,
        "contract_address": ANCHOR_ADDR,
        "chain": os.getenv("CHAIN_NAME", "sepolia"),
    }
    res = db.blocks.insert_one(blk_doc)
    block_id = res.inserted_id

    # compute and store onchain_block_id (uint256) deterministically
    onchain_block_id = derive_onchain_block_id(str(block_id))
    db.blocks.update_one({"_id": block_id}, {"$set": {"onchain_block_id": str(onchain_block_id)}})

    # attach block_id to all pending txs
    db.ledger_txs.update_many(
        {"_id": {"$in": [p["_id"] for p in pending]}},
        {"$set": {"block_id": block_id}}
    )

    # domain: finalize credits in this block (issue mints)
    for p in pending:
        if p["type"] == "mint":
            cid = ObjectId(p["payload"]["credit_id"])
            db.credits.update_one({"_id": cid}, {"$set": {"status": "issued", "block_id": block_id}})

    # --- Auto-anchor if chain env is present ---
    anchored = False
    anchor_txh = None
    if WEB3_RPC_URL and REG_PK and ANCHOR_ADDR:
        try:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(WEB3_RPC_URL))
            acct = w3.eth.account.from_key(REG_PK)
            abi = [{
              "inputs":[{"internalType":"uint256","name":"blockId","type":"uint256"},
                        {"internalType":"bytes32","name":"root","type":"bytes32"}],
              "name":"anchor","outputs":[{"internalType":"bool","name":"","type":"bool"}],
              "stateMutability":"nonpayable","type":"function"
            }]
            contract = w3.eth.contract(address=Web3.to_checksum_address(ANCHOR_ADDR), abi=abi)
            root_bytes = w3.to_bytes(hexstr=root)
            tx = contract.functions.anchor(onchain_block_id, root_bytes).build_transaction({
                "from": acct.address,
                "nonce": w3.eth.get_transaction_count(acct.address),
                "gas": 200000,
                "maxFeePerGas": w3.to_wei("20", "gwei"),
                "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
                "chainId": w3.eth.chain_id,
            })
            signed = w3.eth.account.sign_transaction(tx, REG_PK)
            txh = w3.eth.send_raw_transaction(_signed_raw_bytes(signed))
            anchor_txh = txh.hex() if hasattr(txh, "hex") else txh

            db.blocks.update_one({"_id": block_id}, {"$set": {"anchor_tx": anchor_txh}})
            # mark minted credits in this block as anchored
            minted_in_block = db.ledger_txs.find({"block_id": block_id, "type": "mint"})
            for t in minted_in_block:
                db.credits.update_one({"_id": ObjectId(t["payload"]["credit_id"])},
                                      {"$set": {"anchor_tx": anchor_txh}})
            ledger_append("anchor", {"block_id": str(block_id), "root": root, "anchor_tx": anchor_txh})
            anchored = True
        except Exception as e:
            # don’t fail block close if anchoring fails; just return the error
            anchor_txh = f"ERROR: {e}"

    return {
        "block_id": str(block_id),
        "onchain_block_id": str(onchain_block_id),
        "merkle_root": root,
        "tx_count": len(pending),
        "chain_hash": chain_hash,
        "contract_address": ANCHOR_ADDR,
        "anchored": anchored,
        "anchor_tx": anchor_txh
    }

# --------------- Routes (prefix: /api/v1) ---------------

@app.get("/api/v1/health")
def health():
    return j({"ok": True})

# ---- Accounts ----
@app.post("/api/v1/accounts")
def create_account():
    body = request.get_json(force=True)
    name = body.get("name")
    role = body.get("role")
    public_key_pem = body.get("public_key_pem")
    if not all([name, role, public_key_pem]):
        return j({"error": "name, role, public_key_pem required"}, 400)
    doc = {"name": name, "role": role, "public_key_pem": public_key_pem}
    res = db.accounts.insert_one(doc)
    ledger_append("account_create", {"account_id": str(res.inserted_id), "role": role})
    return j({"id": str(res.inserted_id), **doc})

@app.get("/api/v1/accounts")
def list_accounts():
    out = []
    for a in db.accounts.find({}):
        out.append({"id": str(a["_id"]), "name": a["name"], "role": a["role"], "public_key_pem": a["public_key_pem"]})
    return j(out)

# ---- Sensors ----
@app.post("/api/v1/sensors")
def register_sensor():
    body = request.get_json(force=True)
    name = body.get("name")
    electrolyzer_id = body.get("electrolyzer_id")
    owner_account_id = body.get("owner_account_id")
    public_key_pem = body.get("public_key_pem")
    if not all([name, electrolyzer_id, owner_account_id, public_key_pem]):
        return j({"error": "name, electrolyzer_id, owner_account_id, public_key_pem required"}, 400)
    try:
        owner = db.accounts.find_one({"_id": ObjectId(owner_account_id)})
    except Exception:
        return j({"error": "invalid owner_account_id"}, 400)
    if not owner:
        return j({"error": "owner account not found"}, 404)

    doc = {"name": name, "electrolyzer_id": electrolyzer_id,
           "owner_account_id": owner["_id"], "public_key_pem": public_key_pem}
    try:
        res = db.sensors.insert_one(doc)
    except Exception as e:
        return j({"error": f"sensor registration failed: {e}"}, 400)
    ledger_append("sensor_register", {"sensor_id": str(res.inserted_id), "electrolyzer_id": electrolyzer_id})
    return j({"id": str(res.inserted_id), "name": name, "electrolyzer_id": electrolyzer_id,
              "owner_account_id": str(owner["_id"]), "public_key_pem": public_key_pem})

@app.get("/api/v1/sensors")
def list_sensors():
    out = []
    for s in db.sensors.find({}):
        out.append({"id": str(s["_id"]), "name": s["name"], "electrolyzer_id": s["electrolyzer_id"],
                    "owner_account_id": str(s["owner_account_id"]), "public_key_pem": s["public_key_pem"]})
    return j(out)

# ---- Evidence ----
@app.post("/api/v1/evidence/upload")
def upload_evidence():
    if "file" not in request.files:
        return j({"error": "file is required"}, 400)
    f = request.files["file"]
    filename = secure_filename(f.filename or "evidence.bin")
    content = f.read()
    digest = sha256_hex(content)

    ex = db.evidence.find_one({"sha256_hex": digest})
    if ex:
        return j({"id": str(ex["_id"]), "filename": ex["filename"], "sha256_hex": ex["sha256_hex"],
                  "stored_path": ex["stored_path"], "created_at": ex["created_at"].isoformat()})

    stored_name = f"{digest[:12]}_{filename}"
    stored_path = os.path.join(EVIDENCE_DIR, stored_name)
    with open(stored_path, "wb") as out:
        out.write(content)
    doc = {"filename": filename, "sha256_hex": digest, "stored_path": stored_path, "created_at": datetime.utcnow()}
    res = db.evidence.insert_one(doc)
    ledger_append("evidence", {"evidence_id": str(res.inserted_id), "sha256_hex": digest})
    return j({"id": str(res.inserted_id), **doc, "created_at": doc["created_at"].isoformat()})

# ---- Overlap check ----
def overlap_exists(electrolyzer_id: str, start: datetime, end: datetime) -> bool:
    q = {
        "electrolyzer_id": electrolyzer_id,
        "$or": [
            {"start_time": {"$lte": start}, "end_time": {"$gt": start}},
            {"start_time": {"$lt": end},   "end_time": {"$gte": end}},
            {"start_time": {"$gte": start}, "end_time": {"$lte": end}},
        ]
    }
    hit = db.production_events.find_one(q)
    return hit is not None

# ---- Events (signed by sensor) ----
@app.post("/api/v1/events")
def submit_event():
    body = request.get_json(force=True)
    sensor_id = body.get("sensor_id")
    start_time = body.get("start_time")
    end_time   = body.get("end_time")
    energy_kwh = body.get("energy_kwh")
    hydrogen_kg= body.get("hydrogen_kg")
    evidence_id= body.get("evidence_id")
    sig_hex    = body.get("sensor_signature_hex")

    if not all([sensor_id, start_time, end_time, energy_kwh, hydrogen_kg, sig_hex]):
        return j({"error": "sensor_id, start_time, end_time, energy_kwh, hydrogen_kg, sensor_signature_hex required"}, 400)

    try: sdoc = db.sensors.find_one({"_id": ObjectId(sensor_id)})
    except Exception: return j({"error": "invalid sensor_id"}, 400)
    if not sdoc: return j({"error": "sensor not found"}, 404)

    ev_oid = None
    if evidence_id is not None:
        try:
            ev_oid = ObjectId(evidence_id)
        except Exception:
            return j({"error": "invalid evidence_id"}, 400)
        if not db.evidence.find_one({"_id": ev_oid}):
            return j({"error": "evidence not found"}, 404)

    try:
        st = as_naive_utc(parse_iso(start_time))
        en = as_naive_utc(parse_iso(end_time))
    except Exception:
        return j({"error": "invalid datetime format; use ISO 8601"}, 400)
    if en <= st: return j({"error": "end_time must be after start_time"}, 400)

    payload = {
        "sensor_id": str(sdoc["_id"]),
        "start_time": st.isoformat(),
        "end_time": en.isoformat(),
        "energy_kwh": round(float(energy_kwh), 6),
        "hydrogen_kg": round(float(hydrogen_kg), 6),
        "evidence_id": str(ev_oid) if ev_oid else None
    }
    canonical = canonical_json(payload)
    sig_ok = verify_ed25519(sdoc["public_key_pem"], canonical.encode("utf-8"), sig_hex)
    ov_ok  = not overlap_exists(sdoc["electrolyzer_id"], st, en)
    verified = bool(sig_ok and ov_ok)

    doc = {
        "sensor_id": sdoc["_id"],
        "electrolyzer_id": sdoc["electrolyzer_id"],
        "start_time": st, "end_time": en,
        "energy_kwh": float(energy_kwh), "hydrogen_kg": float(hydrogen_kg),
        "evidence_id": ev_oid,
        "payload_canonical": canonical,
        "sensor_signature_hex": sig_hex,
        "signature_valid": sig_ok,
        "overlap_ok": ov_ok,
        "verified": verified,
        "created_at": datetime.utcnow()
    }
    res = db.production_events.insert_one(doc)
    ledger_append("event", {"event_id": str(res.inserted_id), "electrolyzer_id": sdoc["electrolyzer_id"],
                            "start_time": payload["start_time"], "end_time": payload["end_time"],
                            "hydrogen_kg": payload["hydrogen_kg"]})

    return j({
        "id": str(res.inserted_id),
        "sensor_id": str(sdoc["_id"]),
        "electrolyzer_id": sdoc["electrolyzer_id"],
        "start_time": st.isoformat(), "end_time": en.isoformat(),
        "energy_kwh": doc["energy_kwh"], "hydrogen_kg": doc["hydrogen_kg"],
        "evidence_id": str(ev_oid) if ev_oid else None,
        "payload_canonical": canonical,
        "sensor_signature_hex": sig_hex,
        "signature_valid": sig_ok, "overlap_ok": ov_ok, "verified": verified
    })

@app.get("/api/v1/events")
def list_events():
    out = []
    for e in db.production_events.find({}).sort("created_at", -1):
        out.append({
            "id": str(e["_id"]), "sensor_id": str(e["sensor_id"]),
            "electrolyzer_id": e["electrolyzer_id"],
            "start_time": e["start_time"].isoformat(), "end_time": e["end_time"].isoformat(),
            "energy_kwh": e["energy_kwh"], "hydrogen_kg": e["hydrogen_kg"],
            "evidence_id": str(e["evidence_id"]) if e.get("evidence_id") else None,
            "signature_valid": bool(e["signature_valid"]),
            "overlap_ok": bool(e["overlap_ok"]), "verified": bool(e["verified"])
        })
    return j(out)

# ---- Credits (1g) ----
@app.post("/api/v1/credits/mint")
def mint_credits():
    body = request.get_json(force=True)
    event_id = body.get("event_id")
    if not event_id: return j({"error": "event_id required"}, 400)
    try:
        evt = db.production_events.find_one({"_id": ObjectId(event_id)})
    except Exception:
        return j({"error": "invalid event_id"}, 400)
    if not evt: return j({"error": "event not found"}, 404)
    if not evt.get("verified"): return j({"error": "event not verified"}, 400)

    sensor = db.sensors.find_one({"_id": evt["sensor_id"]})
    if not sensor: return j({"error": "sensor not found"}, 500)
    producer_id = sensor["owner_account_id"]

    amount_g = kg_to_g(float(evt["hydrogen_kg"]))
    cred = {
        "amount_g": amount_g,
        "status": "pending",  # pending -> issued (on block close) -> retired / anchored flag set separately
        "producer_account_id": producer_id,
        "owner_account_id": producer_id,
        "event_id": evt["_id"],
        "block_id": None,
        "anchor_tx": None,
        "created_at": datetime.utcnow()
    }
    res = db.credits.insert_one(cred)
    credit_id = str(res.inserted_id)

    th = ledger_append("mint", {"credit_id": credit_id, "event_id": event_id, "amount_g": amount_g,
                                "owner_account_id": str(producer_id)})

    return j({"credit_id": credit_id, "amount_g": amount_g, "owner_account_id": str(producer_id),
              "status": "pending", "tx_hash": th})

@app.get("/api/v1/accounts/<account_id>/balance")
def get_balance(account_id):
    try: acc = db.accounts.find_one({"_id": ObjectId(account_id)})
    except Exception: return j({"error": "invalid account_id"}, 400)
    if not acc: return j({"error": "account not found"}, 404)
    agg = list(db.credits.aggregate([
        {"$match": {"owner_account_id": acc["_id"], "status": {"$ne": "retired"}}},
        {"$group": {"_id": None, "g": {"$sum": "$amount_g"}}}
    ]))
    g = int(agg[0]["g"]) if agg else 0
    return j({"account_id": account_id, "balance_g": g, "balance_kg": g/1000.0})

@app.post("/api/v1/credits/transfer")
def transfer_credit():
    """
    Supports partial transfer via 'amount_g'.
    Body: { credit_id, from_account_id, to_account_id, amount_g, owner_signature_hex }
    Signature by FROM account over canonical({credit_id,from_account_id,to_account_id,amount_g})
    """
    body = request.get_json(force=True)
    credit_id = body.get("credit_id")
    from_id   = body.get("from_account_id")
    to_id     = body.get("to_account_id")
    amount_g  = int(body.get("amount_g", 0))
    sig_hex   = body.get("owner_signature_hex")
    if not all([credit_id, from_id, to_id, amount_g, sig_hex]):
        return j({"error": "credit_id, from_account_id, to_account_id, amount_g, owner_signature_hex required"}, 400)

    try:
        cred = db.credits.find_one({"_id": ObjectId(credit_id)})
        from_acc = db.accounts.find_one({"_id": ObjectId(from_id)})
        to_acc   = db.accounts.find_one({"_id": ObjectId(to_id)})
    except Exception:
        return j({"error": "invalid id(s)"}, 400)
    if not cred: return j({"error": "credit not found"}, 404)
    if not from_acc or not to_acc: return j({"error": "account(s) not found"}, 404)
    if cred["status"] == "retired": return j({"error": "credit retired"}, 400)
    if str(cred["owner_account_id"]) != str(from_acc["_id"]): return j({"error": "not owner"}, 400)
    if amount_g <= 0 or amount_g > int(cred["amount_g"]): return j({"error": "invalid amount_g"}, 400)

    payload = {"credit_id": credit_id, "from_account_id": from_id, "to_account_id": to_id, "amount_g": amount_g}
    canonical = canonical_json(payload)
    if not verify_ed25519(from_acc["public_key_pem"], canonical.encode("utf-8"), sig_hex):
        return j({"error": "owner signature invalid"}, 400)

    # Split or move whole
    new_credit_id = None
    if amount_g == int(cred["amount_g"]):
        db.credits.update_one({"_id": cred["_id"]}, {"$set": {"owner_account_id": to_acc["_id"]}})
        new_credit_id = credit_id
    else:
        # reduce source, create new for receiver
        db.credits.update_one({"_id": cred["_id"]}, {"$inc": {"amount_g": -amount_g}})
        new_doc = {
            "amount_g": amount_g, "status": cred["status"],
            "producer_account_id": cred["producer_account_id"],
            "owner_account_id": to_acc["_id"],
            "event_id": cred["event_id"],
            "block_id": cred.get("block_id"), "anchor_tx": cred.get("anchor_tx"),
            "created_at": datetime.utcnow()
        }
        res_new = db.credits.insert_one(new_doc)
        new_credit_id = str(res_new.inserted_id)

    th = ledger_append("transfer", {**payload, "new_credit_id": new_credit_id})
    return j({"ok": True, "to_credit_id": new_credit_id, "tx_hash": th})

@app.post("/api/v1/credits/retire")
def retire_credit():
    """
    Supports partial retire via 'amount_g'.
    Body: { credit_id, owner_account_id, amount_g, reason, owner_signature_hex }
    Signature by OWNER over canonical({credit_id,owner_account_id,amount_g,reason})
    """
    body = request.get_json(force=True)
    credit_id = body.get("credit_id")
    owner_id  = body.get("owner_account_id")
    amount_g  = int(body.get("amount_g", 0))
    reason    = body.get("reason") or ""
    sig_hex   = body.get("owner_signature_hex")

    if not all([credit_id, owner_id, amount_g, sig_hex]):
        return j({"error": "credit_id, owner_account_id, amount_g, owner_signature_hex required"}, 400)

    try:
        cred = db.credits.find_one({"_id": ObjectId(credit_id)})
        owner = db.accounts.find_one({"_id": ObjectId(owner_id)})
    except Exception:
        return j({"error": "invalid id(s)"}, 400)
    if not cred: return j({"error": "credit not found"}, 404)
    if not owner: return j({"error": "owner account not found"}, 404)
    if str(cred["owner_account_id"]) != str(owner["_id"]): return j({"error": "not owner"}, 400)
    if cred["status"] == "retired": return j({"error": "already retired"}, 400)
    if amount_g <= 0 or amount_g > int(cred["amount_g"]): return j({"error": "invalid amount_g"}, 400)

    payload = {"credit_id": credit_id, "owner_account_id": owner_id, "amount_g": amount_g, "reason": reason}
    canonical = canonical_json(payload)
    if not verify_ed25519(owner["public_key_pem"], canonical.encode("utf-8"), sig_hex):
        return j({"error": "owner signature invalid"}, 400)

    # Partial or full retire
    if amount_g == int(cred["amount_g"]):
        db.credits.update_one({"_id": cred["_id"]}, {"$set": {"status": "retired"}})
        retired_credit_id = credit_id
    else:
        db.credits.update_one({"_id": cred["_id"]}, {"$inc": {"amount_g": -amount_g}})
        # store retirement record
        db.retirements.insert_one({
            "credit_id": cred["_id"], "owner_account_id": owner["_id"],
            "amount_g": amount_g, "reason": reason, "timestamp": datetime.utcnow()
        })
        retired_credit_id = credit_id

    th = ledger_append("retire", payload)
    return j({"ok": True, "retired_from_credit_id": retired_credit_id, "amount_g": amount_g, "tx_hash": th})

# ---- Ledger / Blocks ----
@app.post("/api/v1/blocks/close")
def blocks_close():
    body = request.get_json(silent=True) or {}
    note = body.get("note")
    res = close_block(note)
    if "error" in res: return j(res, 400)
    return j(res)

@app.get("/api/v1/blocks/latest")
def blocks_latest():
    blk = db.blocks.find_one(sort=[("_id", -1)])
    if not blk: return j({"error": "no blocks yet"}, 404)
    return j({
        "block_id": str(blk["_id"]),
        "prev_hash": blk.get("prev_hash"),
        "merkle_root": blk["merkle_root"],
        "chain_hash": blk["chain_hash"],
        "tx_count": blk["tx_count"],
        "created_at": blk["created_at"].isoformat(),
        "anchor_tx": blk.get("anchor_tx"),
        "onchain_block_id": blk.get("onchain_block_id"),
        "contract_address": blk.get("contract_address"),
        "chain": blk.get("chain", "sepolia"),
    })

# ---- Optional Anchor to chain ----
@app.post("/api/v1/blocks/<block_id>/anchor")
def anchor_block(block_id):
    if not (WEB3_RPC_URL and REG_PK and ANCHOR_ADDR):
        return j({"error": "chain env missing (WEB3_RPC_URL, REGISTRY_PRIVATE_KEY, ANCHOR_CONTRACT_ADDRESS)"}, 400)
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider(WEB3_RPC_URL))

    try:
        blk = db.blocks.find_one({"_id": ObjectId(block_id)})
    except Exception:
        return j({"error": "invalid block_id"}, 400)
    if not blk:
        return j({"error": "block not found"}, 404)
    if blk.get("anchor_tx"):
        return j({"error": "already anchored", "anchor_tx": blk["anchor_tx"]}, 400)

    acct = w3.eth.account.from_key(REG_PK)
    abi = [{
      "inputs":[{"internalType":"uint256","name":"blockId","type":"uint256"},
                {"internalType":"bytes32","name":"root","type":"bytes32"}],
      "name":"anchor","outputs":[{"internalType":"bool","name":"","type":"bool"}],
      "stateMutability":"nonpayable","type":"function"
    }]
    contract = w3.eth.contract(address=Web3.to_checksum_address(ANCHOR_ADDR), abi=abi)

    onchain_block_id = int(blk.get("onchain_block_id") or derive_onchain_block_id(block_id))
    root_bytes = w3.to_bytes(hexstr=blk["merkle_root"])
    txn = contract.functions.anchor(onchain_block_id, root_bytes).build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "gas": 200000,
        "maxFeePerGas": w3.to_wei("20", "gwei"),
        "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
        "chainId": w3.eth.chain_id
    })
    signed = w3.eth.account.sign_transaction(txn, REG_PK)
    txh = w3.eth.send_raw_transaction(_signed_raw_bytes(signed)).hex()

    db.blocks.update_one({"_id": blk["_id"]}, {"$set": {"anchor_tx": txh}})
    minted_in_block = db.ledger_txs.find({"block_id": blk["_id"], "type": "mint"})
    for t in minted_in_block:
        db.credits.update_one({"_id": ObjectId(t["payload"]["credit_id"])}, {"$set": {"anchor_tx": txh}})
    ledger_append("anchor", {"block_id": block_id, "root": blk["merkle_root"], "anchor_tx": txh})

    return j({"anchored": True, "tx": txh})


########################################################### anchor blocks
from flask import abort
import math

# helper: recompute merkle root for txs in a block
def compute_merkle_root(tx_hashes):
    if not tx_hashes:
        return None
    layer = tx_hashes[:]
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i] if i + 1 == len(layer) else layer[i+1]
            concat = (left + right).encode()
            nxt.append(hashlib.sha256(concat).hexdigest())
        layer = nxt
    return layer[0]

# helper: build merkle proof for a tx
def build_merkle_proof(tx_hashes, target):
    if target not in tx_hashes:
        return None
    proof = []
    idx = tx_hashes.index(target)
    layer = tx_hashes[:]
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i] if i + 1 == len(layer) else layer[i+1]
            pair_hash = hashlib.sha256((left + right).encode()).hexdigest()
            nxt.append(pair_hash)
            if i == idx or i+1 == idx:
                is_right = (i == idx)
                sibling = right if i == idx else left
                proof.append({"sibling": sibling, "is_right": is_right})
                idx = len(nxt)-1
        layer = nxt
    return proof

@app.get("/api/v1/blocks/<block_id>")
def get_block(block_id):
    block = db.blocks.find_one({"_id": ObjectId(block_id)})
    if not block:
        return j({"error": "block not found"}), 404
    block["id"] = str(block["_id"])
    block.pop("_id")
    return j(block)

@app.get("/api/v1/blocks/<block_id>/txs")
def get_block_txs(block_id):
    blk = db.blocks.find_one({"_id": ObjectId(block_id)})
    if not blk:
        return j({"error": "block not found"}), 404

    txs = list(db.ledger_txs.find({"block_id": ObjectId(block_id)}).sort("created_at", 1))
    out = [{"tx_hash": t["tx_hash"], "type": t.get("type","")} for t in txs]
    return j({
        "block_id": block_id,
        "order": "created_at_asc",
        "hash_algo": "sha256",
        "merkle_concat": "left||right, duplicate last if odd",
        "txs": out
    })


@app.get("/api/v1/proof/tx/<tx_hash>")
def get_tx_proof(tx_hash):
    tx = db.ledger_txs.find_one({"tx_hash": tx_hash})
    if not tx:
        return j({"error": "tx not found"}), 404
    block_id = tx["block_id"]
    block = db.blocks.find_one({"_id": ObjectId(block_id)})
    if not block:
        return j({"error": "block not found"}), 404

    txs = list(db.ledger_txs.find({"block_id": block_id}).sort("created_at", 1))
    tx_hashes = [t["tx_hash"] for t in txs]
    proof = build_merkle_proof(tx_hashes, tx_hash)
    root = compute_merkle_root(tx_hashes)

    return j({
        "block_id": block_id,
        "onchain_block_id": block.get("onchain_block_id"),
        "tx_hash": tx_hash,
        "index": tx_hashes.index(tx_hash),
        "hashes_count": len(tx_hashes),
        "proof": proof,
        "merkle_root": root,
        "anchor_tx": block.get("anchor_tx"),
        "contract_address": block.get("contract_address"),
        "chain": block.get("chain", "sepolia")
    })
    
    
    
############## account balance proof
@app.get("/api/v2/state/root")
def v2_state_root():
    balances = _fetch_balances()  # :contentReference[oaicite:5]{index=5}
    root_hex = build_state_root(balances)  # "0x..." :contentReference[oaicite:6]{index=6}
    return j({
        "state_root": root_hex,
        "hash_algo": "sha256",
        "tree": "Sparse Merkle Tree (binary, 256-depth)",
        "leaf_rule": 'H(0x00 || uint256(balance_g))',
        "node_rule": 'H(0x01 || left || right)',
        "key_rule": 'sha256(account_id)',
        "created_at": datetime.utcnow().isoformat() + "Z"
    })

@app.get("/api/v2/state/proof/<account_id>")
def v2_state_proof(account_id):
    balances = _fetch_balances()
    leaf_hex, proof, root_hex = prove_account(balances, account_id)  # :contentReference[oaicite:7]{index=7}
    ok_local = verify_account(account_id, int(balances.get(account_id, 0)), leaf_hex, proof, root_hex)  # :contentReference[oaicite:8]{index=8}
    return j({
        "account_id": account_id,
        "balance_g": int(balances.get(account_id, 0)),
        "leaf": leaf_hex,
        "proof": proof,            # 256 steps (sparse)
        "state_root": root_hex,
        "local_verify_ok": ok_local
    })
@app.get("/api/v2/state/proof/<account_id>/compressed")
def v2_state_proof_compressed(account_id):
    balances = _fetch_balances()
    leaf_hex, proof, root_hex = prove_account(balances, account_id)
    # compress: keep only steps whose sibling != default at that depth
    # :contentReference[oaicite:9]{index=9}
    compact = []
    for depth, step in enumerate(proof, start=1):  # depth 1..256 (from leaf upward)
        default_hex = "0x" + DEFAULTS[257 - depth].hex()
        if _norm0x(step["sibling"]) != _norm0x(default_hex):
            compact.append({"depth": depth, "sibling": step["sibling"], "is_right": step["is_right"]})
    return j({
        "account_id": account_id,
        "balance_g": int(balances.get(account_id, 0)),
        "leaf": leaf_hex,
        "state_root": root_hex,
        "proof_compressed": compact,
        "meta": {"skipped_defaults": 256 - len(compact)}
    })

if __name__ == "__main__":
    app.run(debug=True)
