import os, json, hashlib
from datetime import datetime, timezone
from typing import Optional

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from pymongo import MongoClient, ASCENDING
from bson import ObjectId
from dotenv import load_dotenv

# ---- Crypto (Ed25519) ----
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

# ------------------- Config -------------------
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "h2_registry")
EVIDENCE_DIR = os.getenv("EVIDENCE_DIR", "evidence_store")
os.makedirs(EVIDENCE_DIR, exist_ok=True)

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

# indexes (idempotent)
db.evidence.create_index("sha256_hex", unique=True)
db.sensors.create_index([("electrolyzer_id", ASCENDING), ("owner_account_id", ASCENDING)], unique=True)
db.production_events.create_index([("electrolyzer_id", ASCENDING), ("start_time", ASCENDING), ("end_time", ASCENDING)])
# ---- NEW COLLECTION INDEXES ----
db.credits.create_index([("owner_account_id", 1), ("status", 1)])
db.ledger_txs.create_index([("block_id", 1)])   # null until closed into a block
db.blocks.create_index([("created_at", 1)])

# ---- UNITS ----
# 1 credit = 1 gram (int)
def kg_to_g(kg: float) -> int:
    return int(round(kg * 1000))

# ---- MINI LEDGER & MERKLE ----
def tx_hash(payload: dict) -> str:
    return sha256_hex(canonical_json(payload).encode("utf-8"))

def merkle_root(hashes: list[str]) -> str:
    if not hashes: 
        return "0"*64
    layer = hashes[:]
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            a = layer[i]
            b = layer[i+1] if i+1 < len(layer) else a  # duplicate odd
            nxt.append(sha256_hex((a + b).encode("utf-8")))
        layer = nxt
    return layer[0]

def ledger_append(tx_type: str, payload: dict) -> str:
    """Store a pending ledger tx (block_id=None). Returns tx_hash."""
    th = tx_hash({"type": tx_type, **payload})
    db.ledger_txs.insert_one({
        "type": tx_type,
        "payload": payload,
        "tx_hash": th,
        "block_id": None,
        "created_at": datetime.utcnow()
    })
    return th

def close_block(note: str | None = None) -> dict:
    """Take all pending txs (block_id=None), roll Merkle, create a block."""
    pending = list(db.ledger_txs.find({"block_id": None}).sort("created_at", 1))
    if not pending:
        return {"error": "no pending txs"}
    tx_hashes = [p["tx_hash"] for p in pending]
    root = merkle_root(tx_hashes)
    # prev
    prev = db.blocks.find_one(sort=[("_id", -1)])
    prev_hash = prev["merkle_root"] if prev else None
    blk = {
        "prev_hash": prev_hash,
        "merkle_root": root,
        "tx_count": len(pending),
        "note": note,
        "created_at": datetime.utcnow(),
        "anchor_tx": None
    }
    res = db.blocks.insert_one(blk)
    block_id = res.inserted_id
    db.ledger_txs.update_many({"_id": {"$in": [p["_id"] for p in pending]}},
                              {"$set": {"block_id": block_id}})
    return {"block_id": str(block_id), "merkle_root": root, "tx_count": len(pending)}

app = Flask(__name__)
from flask.json.provider import DefaultJSONProvider
from bson import ObjectId
from datetime import datetime

class MongoJSONProvider(DefaultJSONProvider):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

app.json = MongoJSONProvider(app)

# ------------------- Helpers -------------------
def canonical_json(data: dict) -> str:
    """Deterministic JSON for signing (sorted keys, compact)."""
    return json.dumps(data, separators=(",", ":"), sort_keys=True)

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def load_pubkey(pem_text: str) -> Ed25519PublicKey:
    return serialization.load_pem_public_key(pem_text.encode("utf-8"))

def verify_ed25519(pub_pem: str, msg: bytes, sig_hex: str) -> bool:
    try:
        pub = load_pubkey(pub_pem)
        pub.verify(bytes.fromhex(sig_hex), msg)
        return True
    except (InvalidSignature, ValueError):
        return False

def as_naive_utc(dt: datetime) -> datetime:
    """Convert any tz-aware dt to naive UTC; keep naive as-is."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

def parse_datetime(s: str) -> datetime:
    # Accept "YYYY-MM-DDTHH:MM:SS" (naive) or ISO with 'Z'/'+/-'
    try:
        # handle trailing Z
        if s.endswith("Z"):
            s = s[:-1]
            return datetime.fromisoformat(s).replace(tzinfo=None)
        return datetime.fromisoformat(s)
    except Exception:
        raise ValueError("invalid datetime format; use ISO 8601")

def oid(s: Optional[str]) -> Optional[ObjectId]:
    if s is None:
        return None
    return ObjectId(s)

def o2s(x):
    return str(x) if isinstance(x, ObjectId) else x

# ------------------- Routes -------------------

@app.get("/health")
def health():
    return jsonify({"ok": True})

# ---- Accounts ----
@app.post("/accounts")
def create_account():
    body = request.get_json(force=True, silent=False)
    name = body.get("name")
    role = body.get("role")
    public_key_pem = body.get("public_key_pem")
    if not all([name, role, public_key_pem]):
        return jsonify({"error": "name, role, public_key_pem required"}), 400

    doc = {"name": name, "role": role, "public_key_pem": public_key_pem}
    res = db.accounts.insert_one(doc)
    return jsonify({"id": str(res.inserted_id), **doc})

@app.get("/accounts")
def list_accounts():
    out = []
    for a in db.accounts.find({}):
        out.append({"id": str(a["_id"]), "name": a["name"], "role": a["role"], "public_key_pem": a["public_key_pem"]})
    return jsonify(out)

# ---- Sensors ----
@app.post("/sensors")
def register_sensor():
    body = request.get_json(force=True, silent=False)
    name = body.get("name")
    electrolyzer_id = body.get("electrolyzer_id")
    owner_account_id = body.get("owner_account_id")
    public_key_pem = body.get("public_key_pem")

    if not all([name, electrolyzer_id, owner_account_id, public_key_pem]):
        return jsonify({"error": "name, electrolyzer_id, owner_account_id, public_key_pem required"}), 400

    try:
        owner = db.accounts.find_one({"_id": ObjectId(owner_account_id)})
    except Exception:
        return jsonify({"error": "invalid owner_account_id"}), 400
    if not owner:
        return jsonify({"error": "owner account not found"}), 404

    doc = {
        "name": name,
        "electrolyzer_id": electrolyzer_id,
        "owner_account_id": owner["_id"],
        "public_key_pem": public_key_pem
    }
    try:
        res = db.sensors.insert_one(doc)
    except Exception as e:
        return jsonify({"error": f"sensor registration failed: {e}"}), 400

    return jsonify({
        "id": str(res.inserted_id),
        "name": name,
        "electrolyzer_id": electrolyzer_id,
        "owner_account_id": str(owner["_id"]),
        "public_key_pem": public_key_pem
    })

@app.get("/sensors")
def list_sensors():
    out = []
    for s in db.sensors.find({}):
        out.append({
            "id": str(s["_id"]),
            "name": s["name"],
            "electrolyzer_id": s["electrolyzer_id"],
            "owner_account_id": str(s["owner_account_id"]),
            "public_key_pem": s["public_key_pem"]
        })
    return jsonify(out)

# ---- Evidence (file upload & SHA-256 pin) ----
@app.post("/evidence/upload")
def upload_evidence():
    if "file" not in request.files:
        return jsonify({"error": "file is required"}), 400
    f = request.files["file"]
    filename = secure_filename(f.filename or "evidence.bin")
    content = f.read()
    digest = sha256_hex(content)

    existing = db.evidence.find_one({"sha256_hex": digest})
    if existing:
        return jsonify({
            "id": str(existing["_id"]),
            "filename": existing["filename"],
            "sha256_hex": existing["sha256_hex"],
            "stored_path": existing["stored_path"],
            "created_at": existing["created_at"].isoformat()
        })

    stored_name = f"{digest[:12]}_{filename}"
    stored_path = os.path.join(EVIDENCE_DIR, stored_name)
    with open(stored_path, "wb") as out:
        out.write(content)

    doc = {
        "filename": filename,
        "sha256_hex": digest,
        "stored_path": stored_path,
        "created_at": datetime.utcnow()
    }
    res = db.evidence.insert_one(doc)
    return jsonify({
        "id": str(res.inserted_id),
        "filename": filename,
        "sha256_hex": digest,
        "stored_path": stored_path,
        "created_at": doc["created_at"].isoformat()
    })

# ---- Overlap check helper ----
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
@app.post("/events")
def submit_event():
    body = request.get_json(force=True, silent=False)

    sensor_id = body.get("sensor_id")
    start_time = body.get("start_time")
    end_time = body.get("end_time")
    energy_kwh = body.get("energy_kwh")
    hydrogen_kg = body.get("hydrogen_kg")
    evidence_id = body.get("evidence_id")
    sensor_signature_hex = body.get("sensor_signature_hex")

    # Basic checks
    if not all([sensor_id, start_time, end_time, energy_kwh, hydrogen_kg, sensor_signature_hex]):
        return jsonify({"error": "sensor_id, start_time, end_time, energy_kwh, hydrogen_kg, sensor_signature_hex required"}), 400

    # Load sensor
    try:
        sdoc = db.sensors.find_one({"_id": ObjectId(sensor_id)})
    except Exception:
        return jsonify({"error": "invalid sensor_id"}), 400
    if not sdoc:
        return jsonify({"error": "sensor not found"}), 404

    # Evidence (optional)
    evidence_oid = None
    if evidence_id is not None:
        try:
            evidence_oid = ObjectId(evidence_id)
        except Exception:
            return jsonify({"error": "invalid evidence_id"}), 400
        ev = db.evidence.find_one({"_id": evidence_oid})
        if not ev:
            return jsonify({"error": "evidence not found"}), 404

    # Parse times
    try:
        st = as_naive_utc(parse_datetime(start_time))
        en = as_naive_utc(parse_datetime(end_time))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if en <= st:
        return jsonify({"error": "end_time must be after start_time"}), 400

    # Canonical payload EXACTLY as signed by the sensor
    payload = {
        "sensor_id": str(sdoc["_id"]),
        "start_time": st.isoformat(),
        "end_time": en.isoformat(),
        "energy_kwh": round(float(energy_kwh), 6),
        "hydrogen_kg": round(float(hydrogen_kg), 6),
        "evidence_id": str(evidence_oid) if evidence_oid else None
    }
    canonical = canonical_json(payload)
    sig_ok = verify_ed25519(sdoc["public_key_pem"], canonical.encode("utf-8"), sensor_signature_hex)

    # Overlap per electrolyzer
    ov_ok = not overlap_exists(sdoc["electrolyzer_id"], st, en)
    verified = bool(sig_ok and ov_ok)

    doc = {
        "sensor_id": sdoc["_id"],
        "electrolyzer_id": sdoc["electrolyzer_id"],
        "start_time": st,
        "end_time": en,
        "energy_kwh": float(energy_kwh),
        "hydrogen_kg": float(hydrogen_kg),
        "evidence_id": evidence_oid,
        "payload_canonical": canonical,
        "sensor_signature_hex": sensor_signature_hex,
        "signature_valid": sig_ok,
        "overlap_ok": ov_ok,
        "verified": verified,
        "created_at": datetime.utcnow()
    }
    res = db.production_events.insert_one(doc)

    return jsonify({
        "id": str(res.inserted_id),
        "sensor_id": str(sdoc["_id"]),
        "electrolyzer_id": sdoc["electrolyzer_id"],
        "start_time": st.isoformat(),
        "end_time": en.isoformat(),
        "energy_kwh": doc["energy_kwh"],
        "hydrogen_kg": doc["hydrogen_kg"],
        "evidence_id": str(evidence_oid) if evidence_oid else None,
        "payload_canonical": canonical,
        "sensor_signature_hex": sensor_signature_hex,
        "signature_valid": sig_ok,
        "overlap_ok": ov_ok,
        "verified": verified
    })

@app.get("/events")
def list_events():
    out = []
    for e in db.production_events.find({}).sort("created_at", -1):
        out.append({
            "id": str(e["_id"]),
            "sensor_id": str(e["sensor_id"]),
            "electrolyzer_id": e["electrolyzer_id"],
            "start_time": e["start_time"].isoformat(),
            "end_time": e["end_time"].isoformat(),
            "energy_kwh": e["energy_kwh"],
            "hydrogen_kg": e["hydrogen_kg"],
            "evidence_id": str(e["evidence_id"]) if e.get("evidence_id") else None,
            "payload_canonical": e["payload_canonical"],
            "sensor_signature_hex": e["sensor_signature_hex"],
            "signature_valid": bool(e["signature_valid"]),
            "overlap_ok": bool(e["overlap_ok"]),
            "verified": bool(e["verified"])
        })
    return jsonify(out)
# ---------- CREDITS (1 credit = 1 gram) ----------

@app.post("/mint")
def mint_credits():
    """
    Body: { "event_id": "<id>" }
    Rules:
      - event must exist and be verified
      - credits go to the producer (sensor owner)
      - amount_g = hydrogen_kg * 1000
    """
    body = request.get_json(force=True, silent=False)
    event_id = body.get("event_id")
    if not event_id:
        return jsonify({"error": "event_id required"}, 400)

    try:
        evt = db.production_events.find_one({"_id": ObjectId(event_id)})
    except Exception:
        return jsonify({"error": "invalid event_id"}, 400)

    if not evt:
        return jsonify({"error": "event not found"}, 404)
    if not evt.get("verified"):
        return jsonify({"error": "event not verified"}, 400)

    # producer is the owner of the sensor
    sensor = db.sensors.find_one({"_id": evt["sensor_id"]})
    if not sensor:
        return jsonify({"error": "sensor not found for event"}, 500)
    producer_id = sensor["owner_account_id"]

    amount_g = kg_to_g(float(evt["hydrogen_kg"]))
    payload = {
        "event_id": str(evt["_id"]),
        "producer_account_id": str(producer_id),
        "owner_account_id": str(producer_id),
        "amount_g": amount_g
    }
    th = ledger_append("mint", payload)

    cred = {
        "amount_g": amount_g,
        "status": "issued",  # issued | transferred | retired
        "producer_account_id": producer_id,
        "owner_account_id": producer_id,
        "event_id": evt["_id"],
        "tx_hash": th,
        "created_at": datetime.utcnow()
    }
    res = db.credits.insert_one(cred)

    return jsonify({
        "credit_id": str(res.inserted_id),
        "amount_g": amount_g,
        "owner_account_id": str(producer_id),
        "tx_hash": th
    })

@app.get("/accounts/<account_id>/balance")
def get_balance(account_id):
    """
    Sum of non-retired credits for an account (grams + kg).
    """
    try:
        acc = db.accounts.find_one({"_id": ObjectId(account_id)})
    except Exception:
        return jsonify({"error": "invalid account_id"}, 400)
    if not acc:
        return jsonify({"error": "account not found"}, 404)

    agg = list(db.credits.aggregate([
        {"$match": {"owner_account_id": acc["_id"], "status": {"$ne": "retired"}}},
        {"$group": {"_id": None, "g": {"$sum": "$amount_g"}}}
    ]))
    g = int(agg[0]["g"]) if agg else 0
    kg = g / 1000.0
    return jsonify({"account_id": account_id, "balance_g": g, "balance_kg": kg})

@app.post("/transfer")
def transfer_credit():
    """
    Body: { "credit_id": "...", "from_account_id": "...", "to_account_id": "...", "owner_signature_hex": "..." }
    Owner signs canonical({"credit_id","from_account_id","to_account_id"})
    """
    body = request.get_json(force=True, silent=False)
    credit_id = body.get("credit_id")
    from_id = body.get("from_account_id")
    to_id = body.get("to_account_id")
    sig_hex = body.get("owner_signature_hex")
    if not all([credit_id, from_id, to_id, sig_hex]):
        return jsonify({"error": "credit_id, from_account_id, to_account_id, owner_signature_hex required"}, 400)

    try:
        cred = db.credits.find_one({"_id": ObjectId(credit_id)})
    except Exception:
        return jsonify({"error": "invalid credit_id"}, 400)
    if not cred:
        return jsonify({"error": "credit not found"}, 404)
    if cred["status"] == "retired":
        return jsonify({"error": "credit retired"}, 400)

    try:
        from_acc = db.accounts.find_one({"_id": ObjectId(from_id)})
        to_acc = db.accounts.find_one({"_id": ObjectId(to_id)})
    except Exception:
        return jsonify({"error": "invalid account id(s)"}, 400)
    if not from_acc or not to_acc:
        return jsonify({"error": "account(s) not found"}, 404)
    if str(cred["owner_account_id"]) != str(from_acc["_id"]):
        return jsonify({"error": "from_account is not current owner"}, 400)

    payload = {
        "credit_id": credit_id,
        "from_account_id": from_id,
        "to_account_id": to_id
    }
    canonical = canonical_json(payload)
    if not verify_ed25519(from_acc["public_key_pem"], canonical.encode("utf-8"), sig_hex):
        return jsonify({"error": "owner signature invalid"}, 400)

    th = ledger_append("transfer", payload)
    db.credits.update_one({"_id": cred["_id"]},
                          {"$set": {"owner_account_id": to_acc["_id"], "status": "transferred"}})

    db.transfers.insert_one({
        "credit_id": cred["_id"],
        "from_account_id": from_acc["_id"],
        "to_account_id": to_acc["_id"],
        "timestamp": datetime.utcnow(),
        "owner_signature_hex": sig_hex,
        "tx_hash": th
    })

    return jsonify({"id": "ok", "to": to_id, "tx_hash": th})

@app.post("/retire")
def retire_credit():
    """
    Body: { "credit_id": "...", "owner_account_id": "...", "reason": "...", "owner_signature_hex": "..." }
    Owner signs canonical({"credit_id","owner_account_id","reason"})
    """
    body = request.get_json(force=True, silent=False)
    credit_id = body.get("credit_id")
    owner_id = body.get("owner_account_id")
    reason = body.get("reason") or ""
    sig_hex = body.get("owner_signature_hex")
    if not all([credit_id, owner_id, sig_hex]):
        return jsonify({"error": "credit_id, owner_account_id, owner_signature_hex required"}, 400)

    try:
        cred = db.credits.find_one({"_id": ObjectId(credit_id)})
        owner = db.accounts.find_one({"_id": ObjectId(owner_id)})
    except Exception:
        return jsonify({"error": "invalid id(s)"}, 400)
    if not cred:
        return jsonify({"error": "credit not found"}, 404)
    if not owner:
        return jsonify({"error": "owner account not found"}, 404)
    if str(cred["owner_account_id"]) != str(owner["_id"]):
        return jsonify({"error": "not owner"}, 400)
    if cred["status"] == "retired":
        return jsonify({"error": "already retired"}, 400)

    payload = {"credit_id": credit_id, "owner_account_id": owner_id, "reason": reason}
    canonical = canonical_json(payload)
    if not verify_ed25519(owner["public_key_pem"], canonical.encode("utf-8"), sig_hex):
        return jsonify({"error": "owner signature invalid"}, 400)

    th = ledger_append("retire", payload)
    db.credits.update_one({"_id": cred["_id"]}, {"$set": {"status": "retired"}})
    db.retirements.insert_one({
        "credit_id": cred["_id"],
        "owner_account_id": owner["_id"],
        "reason": reason,
        "timestamp": datetime.utcnow(),
        "owner_signature_hex": sig_hex,
        "tx_hash": th
    })
    return jsonify({"id": "ok", "tx_hash": th})
@app.post("/blocks/close")
def blocks_close():
    """
    Close a block from all pending ledger txs (block_id=None).
    Body: { "note": "optional text" }
    """
    body = request.get_json(silent=True) or {}
    note = body.get("note")
    res = close_block(note)
    if "error" in res:
        return jsonify(res, 400)
    return jsonify(res)

@app.get("/blocks/latest")
def blocks_latest():
    blk = db.blocks.find_one(sort=[("_id", -1)])
    if not blk:
        return jsonify({"error": "no blocks yet"}, 404)
    out = {
        "block_id": str(blk["_id"]),
        "prev_hash": blk.get("prev_hash"),
        "merkle_root": blk["merkle_root"],
        "tx_count": blk["tx_count"],
        "created_at": blk["created_at"].isoformat(),
        "anchor_tx": blk.get("anchor_tx")
    }
    return jsonify(out)

# OPTIONAL: minimal anchor endpoint (requires web3 installed + env set)
# pip install web3

@app.post("/blocks/<block_id>/anchor")
def anchor_block(block_id):
    from web3 import Web3

    WEB3_RPC_URL = os.getenv("WEB3_RPC_URL")
    PK = os.getenv("REGISTRY_PRIVATE_KEY")
    CONTRACT = os.getenv("ANCHOR_CONTRACT_ADDRESS")
    if not (WEB3_RPC_URL and PK and CONTRACT):
        return jsonify({"error": "missing chain env (WEB3_RPC_URL, REGISTRY_PRIVATE_KEY, ANCHOR_CONTRACT_ADDRESS)"}, 400)

    try:
        blk = db.blocks.find_one({"_id": ObjectId(block_id)})
    except Exception:
        return jsonify({"error": "invalid block_id"}, 400)
    if not blk:
        return jsonify({"error": "block not found"}, 404)
    if blk.get("anchor_tx"):
        return jsonify({"error": "already anchored", "anchor_tx": blk["anchor_tx"]}, 400)

    w3 = Web3(Web3.HTTPProvider(WEB3_RPC_URL))
    acct = w3.eth.account.from_key(PK)
    abi = [{
      "inputs":[{"internalType":"uint256","name":"blockId","type":"uint256"},
                {"internalType":"bytes32","name":"root","type":"bytes32"}],
      "name":"anchor","outputs":[{"internalType":"bool","name":"","type":"bool"}],
      "stateMutability":"nonpayable","type":"function"
    }]
    contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT), abi=abi)

    # derive numeric block id safely from Mongo _id's increment (or use a counter)
    # For demo, we just pass a small synthetic id (hash % 1e6)
    synthetic_id = int(sha256_hex(str(blk["_id"]).encode())[:10], 16) % 1_000_000
    root_bytes = w3.to_bytes(hexstr=blk["merkle_root"])

    txn = contract.functions.anchor(synthetic_id, root_bytes).build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "gas": 200000,
        "maxFeePerGas": w3.to_wei("20", "gwei"),
        "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
        "chainId": w3.eth.chain_id
    })
    signed = w3.eth.account.sign_transaction(txn, PK)
    txh = w3.eth.send_raw_transaction(signed.rawTransaction).hex()

    db.blocks.update_one({"_id": blk["_id"]}, {"$set": {"anchor_tx": txh}})
    # also ledger a meta "anchor" tx (optional)
    ledger_append("anchor", {"block_id": str(blk["_id"]), "root": blk["merkle_root"], "anchor_tx": txh})

    return jsonify({"anchored": True, "tx": txh})


# ------------------- Main -------------------
if __name__ == "__main__":
    app.run(debug=True)
