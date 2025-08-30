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

app = Flask(__name__)

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

