# prove_state_account.py
# Build a Sparse Merkle proof for <account_id> from Mongo balances,
# verify locally, then compare against on-chain state root.
#
# env:
#   MONGODB_URI, DB_NAME
#   WEB3_RPC_URL, ANCHOR_CONTRACT_ADDRESS
#
# usage:
#   python prove_state_account.py <ACCOUNT_ID> <ONCHAIN_BLOCK_ID>
#
# note:
#   ONCHAIN_BLOCK_ID must be the one you used when anchoring this SMT root.

import os, sys, json
from pymongo import MongoClient
from web3 import Web3

from smt_state import build_state_root, prove_account, verify_account
from dotenv import load_dotenv

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME      = os.getenv("DB_NAME", "h2_registry")
RPC          = os.getenv("WEB3_RPC_URL")
CADDR        = os.getenv("ANCHOR_CONTRACT_ADDRESS")

READ_ROOT_ABI = [{
  "inputs":[{"internalType":"uint256","name":"blockId","type":"uint256"}],
  "name":"roots","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],
  "stateMutability":"view","type":"function"
}]
def norm0x(h: str) -> str:
    h = h.lower()
    if h.startswith("0x"): h = h[2:]
    return h.zfill(64)  # ensure 32 bytes
def fetch_balances(db):
    agg = db.credits.aggregate([
        {"$match": {"status": {"$ne": "retired"}}},
        {"$group": {"_id": "$owner_account_id", "g": {"$sum": "$amount_g"}}}
    ])
    balances = {}
    for row in agg:
        balances[str(row["_id"])] = int(row["g"])
    return balances

def main():
    if len(sys.argv) != 3:
        print("usage: python prove_state_account.py <ACCOUNT_ID> <ONCHAIN_BLOCK_ID>"); sys.exit(1)
    if not (RPC and CADDR):
        raise SystemExit("Set WEB3_RPC_URL and ANCHOR_CONTRACT_ADDRESS")

    account_id = sys.argv[1]
    onchain_block_id = int(sys.argv[2])

    cli = MongoClient(MONGODB_URI)
    db  = cli[DB_NAME]

    balances = fetch_balances(db)
    # local state root (must match the anchored one for this height)
    local_root = build_state_root(balances)

    # build proof for given account
    leaf_hex, proof, root_hex = prove_account(balances, account_id)
    ok_local = verify_account(account_id, balances.get(account_id, 0), leaf_hex, proof, root_hex)

    # fetch on-chain root
    w3 = Web3(Web3.HTTPProvider(RPC))
    c = w3.eth.contract(address=Web3.to_checksum_address(CADDR), abi=READ_ROOT_ABI)
    onchain_root = c.functions.roots(onchain_block_id).call().hex()  # may or may not have 0x depending on web3 version
    local_match = norm0x(onchain_root) == norm0x(local_root)

    res = {
        "account_id": account_id,
        "balance_g": int(balances.get(account_id, 0)),
        "leaf": leaf_hex,
        "proof": proof,
        "local_root": root_hex,
        "local_verify_ok": ok_local,
        "onchain_block_id": str(onchain_block_id),
        "onchain_root": onchain_root,
        "local_vs_onchain_match":local_match
    }
    print(json.dumps(res, indent=2))
    with open(f"proof_account_{account_id}.json", "w") as f:
        json.dump(res, f, indent=2)
    print("Proof saved to", f"proof_account_{account_id}.json")
if __name__ == "__main__":
    main()
