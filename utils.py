import hashlib
def _norm0x(h: str) -> str:
    h = (h or "").lower()
    if h.startswith("0x"): h = h[2:]
    return h.zfill(64)

# --- Chain helpers (v5/v6 compatible) ---
def _signed_raw_bytes(signed):
    # web3.py v6: signed.raw_transaction ; v5: signed.rawTransaction
    return getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")

def derive_onchain_block_id(mongo_oid_str: str) -> int:
    # same rule as anchor_block.py (sha256 string -> uint256)
    return int(hashlib.sha256(mongo_oid_str.encode()).hexdigest(), 16) % (2**256)

from web3.exceptions import TransactionNotFound
from time import sleep

def _bump(fee):
    # ~12.5% bump (clients typically require >=10%)
    return int(fee + fee // 8)

def send_anchor_with_bump(w3, acct, contract, onchain_block_id, root_bytes, chain_id, attempts=3, wait_receipt=True, wait_timeout=90):
    # Build baseline fees from pending base fee
    base = w3.eth.get_block("pending")["baseFeePerGas"]
    max_priority = w3.to_wei(2, "gwei")   # tweak if needed
    max_fee      = base * 2 + max_priority

    # Always use the pending nonce (so we don't reuse a mined nonce)
    nonce = w3.eth.get_transaction_count(acct.address, "pending")

    last_exc = None
    for i in range(attempts):
        tx = contract.functions.anchor(onchain_block_id, root_bytes).build_transaction({
            "from": acct.address,
            "nonce": nonce,
            "gas": 200000,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority,
            "chainId": chain_id,
        })
        signed = w3.eth.account.sign_transaction(tx, acct.key)

        # web3 versions expose rawTransaction or raw_transaction
        raw = getattr(signed, "rawTransaction", None) or getattr(signed, "raw_transaction", None) or signed
        try:
            tx_hash = w3.eth.send_raw_transaction(raw)
            txh_hex = tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash)

            if wait_receipt:
                w3.eth.wait_for_transaction_receipt(tx_hash, timeout=wait_timeout)
            return txh_hex
        except ValueError as e:
            # JSON-RPC structured error
            msg = str(e)
            # common messages: replacement transaction underpriced / fee too low / already known
            if "replacement transaction underpriced" in msg or "fee too low" in msg or "underpriced" in msg:
                # bump both fees and retry with same nonce
                max_fee      = _bump(max_fee)
                max_priority = _bump(max_priority)
                sleep(2)
                last_exc = e
                continue
            elif "nonce too low" in msg:
                # Someone else used that nonce; refresh nonce and retry once
                nonce = w3.eth.get_transaction_count(acct.address, "pending")
                sleep(1)
                last_exc = e
                continue
            else:
                # other errors: rethrow after loop
                last_exc = e
                break
        except Exception as e:
            last_exc = e
            break

    raise last_exc if last_exc else RuntimeError("Failed to anchor after retries.")
