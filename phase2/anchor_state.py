# anchor_state.py
# Compute SMT state root (balances over all accounts) from Mongo and anchor to chain.
#
# env:
#   MONGODB_URI=mongodb://localhost:27017
#   DB_NAME=h2_registry
#   WEB3_RPC_URL=https://sepolia.infura.io/v3/<KEY>
#   PRIVATE_KEY=0x<your_test_key>
#   ANCHOR_CONTRACT_ADDRESS=0x<CreditAnchor>
#   CHAIN_NAME=sepolia   (optional)
#
# usage:
#   python anchor_state.py
#
# effect:
#   - prints {root, block_id, tx}
#   - (optional) writes a small JSON receipt for your records

import os, json, hashlib
from datetime import datetime, UTC
from pymongo import MongoClient
from web3 import Web3

from smt_state import build_state_root  # from your existing file
from dotenv import load_dotenv

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME      = os.getenv("DB_NAME", "h2_registry")
RPC          = os.getenv("WEB3_RPC_URL")
PK           = os.getenv("PRIVATE_KEY")
CADDR        = os.getenv("ANCHOR_CONTRACT_ADDRESS")
CHAIN_NAME   = os.getenv("CHAIN_NAME", "sepolia")

ABI = [{
  "inputs":[{"internalType":"uint256","name":"blockId","type":"uint256"},
            {"internalType":"bytes32","name":"root","type":"bytes32"}],
  "name":"anchor","outputs":[{"internalType":"bool","name":"","type":"bool"}],
  "stateMutability":"nonpayable","type":"function"
}]

def _signed_raw_bytes(signed):
    return getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")

def fetch_balances(db):
    # sum of credits not retired
    agg = db.credits.aggregate([
        {"$match": {"status": {"$ne": "retired"}}},
        {"$group": {"_id": "$owner_account_id", "g": {"$sum": "$amount_g"}}}
    ])
    balances = {}
    for row in agg:
        balances[str(row["_id"])] = int(row["g"])
    return balances

def to_bytes32_hex(root_hex_no0x: str) -> str:
    h = root_hex_no0x.lower()
    if h.startswith("0x"): h = h[2:]
    if len(h) != 64: raise SystemExit("root must be 32 bytes hex (64 chars)")
    return "0x" + h

def derive_block_id_from_root(root_hex: str) -> int:
    # deterministic block id: uint256( sha256("smt|" + root) )
    raw = root_hex.lower().removeprefix("0x")
    digest = hashlib.sha256(("smt|" + raw).encode()).hexdigest()
    return int(digest, 16) % (2**256)

def main():
    if not (RPC and PK and CADDR):
        raise SystemExit("Set WEB3_RPC_URL, PRIVATE_KEY, ANCHOR_CONTRACT_ADDRESS")

    cli = MongoClient(MONGODB_URI)
    db  = cli[DB_NAME]

    balances = fetch_balances(db)
    root_hex = build_state_root(balances)  # "0x...."
    block_id = derive_block_id_from_root(root_hex)

    w3 = Web3(Web3.HTTPProvider(RPC))
    acct = w3.eth.account.from_key(PK)
    c = w3.eth.contract(address=Web3.to_checksum_address(CADDR), abi=ABI)

    tx = c.functions.anchor(block_id, to_bytes32_hex(root_hex)).build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "gas": 200000,
        "maxFeePerGas": w3.to_wei("20", "gwei"),
        "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
        "chainId": w3.eth.chain_id
    })
    signed = w3.eth.account.sign_transaction(tx, PK)
    txh = w3.eth.send_raw_transaction(_signed_raw_bytes(signed))
    rcpt = w3.eth.wait_for_transaction_receipt(txh)

    out = {
        "type": "smt_anchor",
        "chain": CHAIN_NAME,
        "contract": CADDR,
        "onchain_block_id": str(block_id),
        "state_root": root_hex,
        "tx": txh.hex() if hasattr(txh, "hex") else str(txh),
        "created_at": datetime.now(UTC).isoformat(),
    }
    print(json.dumps(out, indent=2))

    # optional receipt file
    fname = f"smt_anchor_receipt_{block_id}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("✔ wrote", fname)

if __name__ == "__main__":
    main()
