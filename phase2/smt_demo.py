# smt_demo.py
# Demo of the SMT: builds state root from Mongo balances, proves an account, verifies,
# simulates a transfer (delta updates), and shows root change.

import os
from datetime import datetime, UTC
from pymongo import MongoClient
from bson import ObjectId
from smt_state import build_state_root, prove_account, verify_account
from dotenv import load_dotenv

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME      = os.getenv("DB_NAME", "h2_registry")

def fetch_balances(db):
    # credits collection: { owner_account_id, amount_g, status in {"pending","issued"} }
    # Treat "retired" as non-balance
    agg = db.credits.aggregate([
        {"$match": {"status": {"$ne": "retired"}}},
        {"$group": {"_id": "$owner_account_id", "g": {"$sum": "$amount_g"}}}
    ])
    balances = {}
    for row in agg:
        balances[str(row["_id"])] = int(row["g"])
    # include accounts with 0? not necessary for SMT (defaults)
    return balances

def main():
    cli = MongoClient(MONGODB_URI)
    db = cli[DB_NAME]

    print("== SMT Demo ==")
    print("Time:", datetime.now(UTC).isoformat())

    balances = fetch_balances(db)
    print("Accounts (nonzero):", len(balances))

    root = build_state_root(balances)
    print("State root:", root)

    # pick one account to prove (first nonzero or any account in DB.accounts)
    target_acc = next(iter(balances.keys()), None)
    if not target_acc:
        acc = db.accounts.find_one({})
        if not acc:
            print("No accounts found"); return
        target_acc = str(acc["_id"])
        if target_acc not in balances:
            balances[target_acc] = 0  # absent -> zero

    leaf, proof, root_hex = prove_account(balances, target_acc)
    ok = verify_account(target_acc, balances.get(target_acc, 0), leaf, proof, root_hex)
    print("Proof for", target_acc, "OK?", ok)

    # simulate a transfer of 100g from target_acc to some other account (or itself)
    other = db.accounts.find_one({"_id": {"$ne": ObjectId(target_acc)}}) or db.accounts.find_one({})
    other_id = str(other["_id"])
    print(target_acc, "balance before:", balances.get(target_acc, 0))
    print(other_id, "balance before:", balances.get(other_id, 0))
    balances[target_acc] = int(balances.get(target_acc, 0)) - 100
    balances[other_id]   = int(balances.get(other_id, 0)) + 100
    print(target_acc, "balance before:", balances.get(target_acc, 0))
    print(other_id, "balance before:", balances.get(other_id, 0))

    new_root = build_state_root(balances)
    print("New state root after simulated 100g transfer:", new_root)
    print("Root changed?", new_root != root)

if __name__ == "__main__":
    main()
