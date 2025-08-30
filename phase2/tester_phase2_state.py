# tester_phase2_state.py
# End-to-end tester for Phase-2 SMT endpoints in app.py
#
# What it does:
# 1) GET  /api/v2/state/root                     -> print current SMT root
# 2) GET  /api/v2/state/proof/<ACCOUNT_ID>       -> print balance + local proof check
# 3) POST /api/v2/state/anchor   (optional)      -> anchor the current root on-chain
# 4) Verify on-chain root matches local root     -> using CreditAnchor.roots(blockId)
#
# Usage:
#   python tester_phase2_state.py \
#       --base http://127.0.0.1:5000 \
#       --account 68b30256a54f3f44a75d4ed7 \
#       --contract 0x361F4564D6F6f045aDECf7EB7f88D018FfA7447A \
#       --rpc https://sepolia.infura.io/v3/<KEY> \
#       [--anchor]          # call POST /api/v2/state/anchor before verifying
#
# Notes:
# - If you use --anchor, your server must have WEB3_RPC_URL, PRIVATE_KEY, ANCHOR_CONTRACT_ADDRESS set.
# - If you skip --anchor, make sure you've anchored this exact state recently (or expect mismatch).
#
# Exit codes:
#   0 = all checks passed
#   1 = HTTP or parsing error
#   2 = local proof failed
#   3 = on-chain root mismatch

import sys
import json
import argparse
import requests
from datetime import datetime
from web3 import Web3

def norm0x(h: str) -> str:
    h = (h or "").lower()
    if h.startswith("0x"):
        h = h[2:]
    return h.zfill(64)

def pretty(jobj):
    return json.dumps(jobj, indent=2)

def get_root(base):
    r = requests.get(f"{base}/api/v2/state/root", timeout=30)
    r.raise_for_status()
    return r.json()

def get_proof(base, account_id):
    r = requests.get(f"{base}/api/v2/state/proof/{account_id}", timeout=60)
    r.raise_for_status()
    return r.json()

def post_anchor(base):
    r = requests.post(f"{base}/api/v2/state/anchor", timeout=120)
    # allow server to return 400 with error JSON (missing env) -> raise for non-2xx only after printing
    if r.status_code // 100 != 2:
        try:
            print("Anchor error:", pretty(r.json()))
        except Exception:
            print("Anchor error HTTP", r.status_code, r.text)
        r.raise_for_status()
    return r.json()

def read_onchain_root(rpc, contract_addr, onchain_block_id):
    abi = [{
      "inputs":[{"internalType":"uint256","name":"blockId","type":"uint256"}],
      "name":"roots","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],
      "stateMutability":"view","type":"function"
    }]
    w3 = Web3(Web3.HTTPProvider(rpc))
    c = w3.eth.contract(address=Web3.to_checksum_address(contract_addr), abi=abi)
    res = c.functions.roots(int(onchain_block_id)).call()
    # web3 may return HexBytes or bytes -> normalize hex
    try:
        hx = res.hex()
    except Exception:
        hx = Web3.to_hex(res)
    return hx

def main():
    ap = argparse.ArgumentParser(description="Phase-2 SMT tester")
    ap.add_argument("--base", required=True, help="Server base, e.g. http://127.0.0.1:5000")
    ap.add_argument("--account", required=True, help="Account ID to prove (Mongo ObjectId as string)")
    ap.add_argument("--contract", required=True, help="CreditAnchor contract address")
    ap.add_argument("--rpc", required=True, help="Ethereum RPC (e.g., Sepolia Infura URL)")
    ap.add_argument("--anchor", action="store_true", help="Call POST /api/v2/state/anchor before verifying")
    args = ap.parse_args()

    try:
        print("== Phase-2 SMT Tester ==")
        print("Time:", datetime.utcnow().isoformat() + "Z")
        print("Base:", args.base)
        print("Account:", args.account)

        if args.anchor:
            print("\n[1] Anchoring current SMT state via server ...")
            anchored = post_anchor(args.base)
            print(pretty(anchored))
            onchain_block_id = anchored.get("onchain_block_id")
            state_root_anchored = anchored.get("state_root")
            tx = anchored.get("tx")
            print(f"Anchor tx: {tx}")
        else:
            onchain_block_id = None
            state_root_anchored = None

        print("\n[2] Fetching current SMT state root from server ...")
        root_resp = get_root(args.base)
        print(pretty(root_resp))
        local_root = root_resp.get("state_root")

        print("\n[3] Getting proof for account ...")
        proof_resp = get_proof(args.base, args.account)
        print(pretty(proof_resp))
        if not proof_resp.get("local_verify_ok", False):
            print("❌ Local Merkle proof failed (server reported local_verify_ok=false).")
            sys.exit(2)
        print("✅ Local proof OK.")

        # Decide which block_id to use for on-chain read:
        # - If we just anchored, use that returned id.
        # - Else, derive from local_root the same way anchor_state.py does: uint256(sha256('smt|' + root))
        if onchain_block_id is None:
            import hashlib
            raw = norm0x(local_root)
            onchain_block_id = int(hashlib.sha256(("smt|" + raw).encode()).hexdigest(), 16) % (2**256)

        print("\n[4] Reading on-chain root ...")
        onchain_root = read_onchain_root(args.rpc, args.contract, onchain_block_id)
        print("on-chain root :", onchain_root)
        print("local  root   :", local_root)

        match = norm0x(onchain_root) == norm0x(local_root if state_root_anchored is None else state_root_anchored)
        # If we anchored in step [1], prefer matching the anchored root. Otherwise match current local root.
        print("match?        :", match)

        if match:
            print("\n✅ VERIFIED: server state root matches on-chain root for block_id =", onchain_block_id)
            sys.exit(0)
        else:
            print("\n⚠️  MISMATCH:")
            print("- Did balances change after anchoring?")
            print("- If you skipped --anchor, was the last anchor for this exact state?")
            print("- Re-run with --anchor to commit the current state, then verify again.")
            sys.exit(3)

    except requests.RequestException as e:
        print("HTTP error:", e)
        sys.exit(1)
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()



########## cmd python tester_phase2_state.py  --base http://127.0.0.1:5000  --account 68b327fc742e3da17f4013a5 --contract 0x361F4564D6F6f045aDECf7EB7f88D018FfA7447A  --rpc https://eth-sepolia.g.alchemy.com/v2/47qnmmhS4pv3SC7AIZQ51