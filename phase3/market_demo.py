# market_demo.py
# Phase-3 CLI: list an offer, buy a slice, show retirements.
#
# Env (optional):
#   MONGODB_URI=mongodb://localhost:27017
#   DB_NAME=hackoutv2
#
# Usage:
#   python market_demo.py
#
# Notes:
# - Looks for a producer, a buyer, and a non-retired producer credit (>0 g).
# - Uses "reservation/locked_g" so the same credit can't be oversold when listed.

import os, json, sys, hashlib
from datetime import datetime
from pymongo import MongoClient, ReturnDocument
from bson import ObjectId
from dotenv import load_dotenv
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME     = os.getenv("DB_NAME", "hackoutv2")
cli = MongoClient(MONGODB_URI)
db  = cli[DB_NAME]

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

from datetime import datetime, timezone  # add timezone

def to_public(x):
    """Recursively convert ObjectId and datetime to JSON-safe values."""
    if isinstance(x, dict):
        return {k: to_public(v) for k, v in x.items()}
    if isinstance(x, list):
        return [to_public(v) for v in x]
    try:
        from bson import ObjectId as _OID
        if isinstance(x, _OID):
            return str(x)
    except Exception:
        pass
    if isinstance(x, datetime):
        # timezone-aware ISO
        return x.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return x

def jprint(x):
    print(json.dumps(to_public(x), indent=2))


def id_variants(x):
    """Return both ObjectId and string forms to be robust."""
    out = []
    if isinstance(x, ObjectId):
        out = [x, str(x)]
    else:
        # x might be string; try parse to ObjectId
        out = [x]
        try:
            out.append(ObjectId(x))
        except Exception:
            pass
    return out

def find_any_producer_credit(producer_id):
    """
    Find a producer credit with amount_g > 0, not retired.
    Status in Phase-1 is typically 'issued' once block is closed.
    We accept both pending/issued for demo, but exclude retired.
    Also handle owner_account_id stored as str or ObjectId.
    """
    owner_variants = id_variants(producer_id)
    q = {
        "owner_account_id": {"$in": owner_variants},
        "status": {"$in": ["issued", "pending"]},
        "amount_g": {"$gt": 0}
    }
    credit = db.credits.find_one(q)
    if not credit:
        # Fallback: any non-retired credit > 0
        credit = db.credits.find_one({
            "owner_account_id": {"$in": owner_variants},
            "status": {"$ne": "retired"},
            "amount_g": {"$gt": 0}
        })
    return credit

def list_offer(producer_id: str, credit_id: str, amount_g: int, price_per_g: float):
    credit = db.credits.find_one({"_id": ObjectId(credit_id)})
    if not credit:
        return {"error": "credit not found"}

    if str(credit.get("owner_account_id")) != producer_id:
        return {"error": "not credit owner"}

    if credit.get("status") in ["retired", "pending"]:
        return {"error": f"credit status not sellable: {credit.get('status')}"}

    amt = int(amount_g)
    if amt <= 0:
        return {"error": "amount_g must be > 0"}

    locked = int(credit.get("locked_g", 0))
    available = int(credit.get("amount_g", 0)) - locked
    if amt > available:
        return {"error": f"insufficient available: {available}g"}

    # atomic reservation
    res = db.credits.update_one(
        {
            "_id": credit["_id"],
            "$or": [
                {"locked_g": locked},
                {"locked_g": {"$exists": False}}
            ]
        },
        {"$set": {"locked_g": locked + amt}}
    )
    if res.modified_count != 1:
        return {"error": "reservation failed (concurrent change)"}

    offer_doc = {
        "producer_id": producer_id,
        "credit_id": credit_id,
        "amount_g": amt,
        "price_per_g": float(price_per_g),
        "created_at": datetime.now(timezone.utc),
        "status": "open"
    }
    ins = db.market_offers.insert_one(offer_doc)
    # Build a clean response without raw _id
    return {
        "id": str(ins.inserted_id),
        "producer_id": producer_id,
        "credit_id": credit_id,
        "amount_g": amt,
        "price_per_g": float(price_per_g),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "open"
    }

def buy_offer(buyer_id: str, offer_id: str, amount_g: int):
    amt = int(amount_g)
    if amt <= 0:
        return {"error": "amount_g must be > 0"}

    offer = db.market_offers.find_one({"_id": ObjectId(offer_id)})
    if not offer:
        return {"error": "offer not found"}

    if offer.get("status") != "open":
        return {"error": "offer closed"}

    if amt > int(offer["amount_g"]):
        return {"error": f"exceeds available in offer: {offer['amount_g']}g"}

    credit = db.credits.find_one({"_id": ObjectId(offer["credit_id"])})
    if not credit:
        return {"error": "linked credit missing"}

    # atomic decrement of amount_g and locked_g (allow missing locked_g)
    upd = db.credits.update_one(
        {
            "_id": credit["_id"],
            "amount_g": {"$gte": amt},
            "$or": [
                {"locked_g": {"$exists": False}},   # allow older credits
                {"locked_g": {"$gte": amt}}
            ]
        },
        {
            "$inc": {
                "amount_g": -amt,
                "locked_g": -amt
            }
        }
    )
    if upd.modified_count != 1:
        return {"error": "not enough locked or amount changed concurrently"}

    buyer_credit = {
        "amount_g": amt,
        "owner_account_id": buyer_id,
        "status": "issued",
        "from_offer": str(offer["_id"]),
        "source_credit_id": str(credit["_id"]),
        "created_at": datetime.now(timezone.utc)
    }
    buyer_credit_id = db.credits.insert_one(buyer_credit).inserted_id

    offer_left = int(offer["amount_g"]) - amt
    new_status = "closed" if offer_left == 0 else "open"
    db.market_offers.update_one(
        {"_id": offer["_id"]},
        {"$set": {"amount_g": offer_left, "status": new_status}}
    )

    tx = {
        "type": "market_buy",
        "buyer_id": buyer_id,
        "producer_id": offer["producer_id"],
        "offer_id": str(offer["_id"]),
        "new_credit_id": str(buyer_credit_id),
        "amount_g": amt,
        "price_per_g": float(offer["price_per_g"]),
        "timestamp": datetime.now(timezone.utc)
    }
    db.market_txs.insert_one(tx)

    return {
        "ok": True,
        "new_credit_id": str(buyer_credit_id),
        "offer_left": offer_left,
        "offer_status": new_status
    }

def list_retirements():
    rets = list(db.ledger_txs.find({"type": "retire"}))
    out = []
    for r in rets:
        p = r.get("payload", {})
        out.append({
            "credit_id": p.get("credit_id"),
            "owner": p.get("owner_account_id"),
            "amount_g": p.get("amount_g"),
            "reason": p.get("reason"),
            "tx_hash": r.get("tx_hash")
        })
    return out

def balances_by_account():
    agg = db.credits.aggregate([
        {"$match": {"status": {"$ne": "retired"}}},
        {"$group": {"_id": "$owner_account_id", "g": {"$sum": "$amount_g"}}}
    ])
    m = {}
    for row in agg:
        m[str(row["_id"])] = int(row["g"])
    return m

def main():
    print("== Phase-3 Marketplace Demo ==")
    producer = db.accounts.find_one({"role": "producer"})
    buyer    = db.accounts.find_one({"role": "buyer"})

    if not producer or not buyer:
        print("Need at least one producer and one buyer account in DB.")
        sys.exit(1)

    print("Producer:", str(producer["_id"]), "| Buyer:", str(buyer["_id"]))

    credit = find_any_producer_credit(producer["_id"])
    if not credit:
        print("No sellable producer credit found. Make sure you minted & issued credits (status != 'retired', amount_g>0).")
        sys.exit(2)

    print("\n[Balances before]")
    jprint(balances_by_account())

    # 1) Producer lists 5000g for sale at 0.1 (unit price is arbitrary demo)
    offer = list_offer(str(producer["_id"]), str(credit["_id"]), amount_g=5000, price_per_g=0.1)
    if "error" in offer:
        print("List offer error:"); jprint(offer); sys.exit(3)
    print("\n[Offer listed]")
    jprint(offer)

    # 2) Buyer purchases 2000g
    buy_res = buy_offer(str(buyer["_id"]), offer["id"], amount_g=2000)
    if "error" in buy_res:
        print("Buy error:"); jprint(buy_res); sys.exit(4)
    print("\n[Buyer purchase]")
    jprint(buy_res)

    print("\n[Balances after]")
    jprint(balances_by_account())

    # 3) Retirements report preview (will be empty unless you ran retire ops)
    print("\n[Retirements report]")
    jprint(list_retirements())

if __name__ == "__main__":
    main()
