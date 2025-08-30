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
