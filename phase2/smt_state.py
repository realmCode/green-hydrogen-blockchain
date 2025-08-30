# smt_state.py
# Binary Sparse Merkle Tree over 256-bit keys (sha256(account_id)).
# Node hash: H(0x01 || left || right), Leaf hash: H(0x00 || value32), H = sha256.
# Default leaves = 0, default tree precomputed so missing keys verify as 0.

import hashlib, json

def H(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()

def b32(n: int) -> bytes:
    return n.to_bytes(32, "big")

def hex32(b: bytes) -> str:
    return "0x" + b.hex()

def key_of(account_id: str) -> bytes:
    return hashlib.sha256(account_id.encode("utf-8")).digest()  # 32 bytes

def bit_at(key_bytes: bytes, depth: int) -> int:
    # depth in [0..255]; 0 = most-significant bit of key
    byte_i = depth // 8
    bit_i = 7 - (depth % 8)
    return (key_bytes[byte_i] >> bit_i) & 1

def precompute_defaults():
    # default leaf: value=0
    default_leaf = H(b"\x00" + b32(0))
    # defaults[d] = default hash at level d (0=root .. 256=leaf)
    defaults = [b""] * 257
    defaults[256] = default_leaf
    for d in range(255, -1, -1):
        ch = defaults[d+1]
        defaults[d] = H(b"\x01" + ch + ch)
    return defaults

DEFAULTS = precompute_defaults()

def leaf_hash(value_g: int) -> bytes:
    return H(b"\x00" + b32(int(value_g)))

def build_state_root(balances: dict[str, int], return_levels=False):
    """
    balances: {account_id(str) -> grams(int)}
    Builds an SMT by bottom-up folding only non-default leaves.
    return_levels=True -> returns per-level node maps for proof building.
    """
    # Level 256: map from position (int) -> hash(bytes)
    lvl = {}
    for acc_id, bal in balances.items():
        if bal == 0:
            continue  # default
        k = key_of(acc_id)
        pos = int.from_bytes(k, "big")
        lvl[pos] = leaf_hash(bal)

    levels = {256: lvl} if return_levels else None
    # fold upward 256 -> 0
    for depth in range(256, 0, -1):
        cur = levels[depth] if return_levels else lvl
        parent = {}
        # combine pairs
        seen = set()
        for pos, h in cur.items():
            if pos in seen:
                continue
            sib = pos ^ 1
            left_pos = pos - (pos & 1)
            right_pos = left_pos ^ 1
            left = cur.get(left_pos, DEFAULTS[depth])
            right = cur.get(right_pos, DEFAULTS[depth])
            ph = H(b"\x01" + left + right)
            ppos = left_pos >> 1
            parent[ppos] = ph
            seen.add(left_pos); seen.add(right_pos)
        if return_levels:
            levels[depth-1] = parent
        lvl = parent

    root = list(lvl.values())[0] if lvl else DEFAULTS[0]
    if return_levels:
        return hex32(root), levels
    return hex32(root)

def prove_account(balances: dict[str, int], account_id: str):
    """
    Returns (leaf_hash_hex, proof_list, root_hex).
    proof_list: [{ "sibling": "0x...", "is_right": bool }, ...] with 256 steps (explicit proof).
    """
    root_hex, levels = build_state_root(balances, return_levels=True)
    k = key_of(account_id)
    pos = int.from_bytes(k, "big")

    # start from leaf depth=256 to root depth=0
    proof = []
    cur_pos = pos
    for depth in range(256, 0, -1):
        layer = levels[depth]
        sib_pos = cur_pos ^ 1
        # sibling hash: from layer or default at this depth
        sib = layer.get(sib_pos, DEFAULTS[depth])
        # is_right means sibling is to the right of current node
        is_current_left = (cur_pos & 1) == 0
        proof.append({"sibling": hex32(sib), "is_right": is_current_left})
        cur_pos >>= 1

    # leaf hash (value)
    leaf = leaf_hash(balances.get(account_id, 0))
    return hex32(leaf), proof, root_hex

def verify_account(account_id: str, balance_g: int, leaf_hex: str, proof: list, root_hex: str) -> bool:
    k = key_of(account_id)
    cur = bytes.fromhex(leaf_hex.removeprefix("0x"))
    # rebuild upward
    for step in proof:
        sib = bytes.fromhex(step["sibling"].removeprefix("0x"))
        if step.get("is_right", False):
            cur = H(b"\x01" + cur + sib)
        else:
            cur = H(b"\x01" + sib + cur)
    return hex32(cur).lower() == root_hex.lower()

# handy JSON helpers for CLI/demo
def canonical_json(d: dict) -> str:
    return json.dumps(d, separators=(",", ":"), sort_keys=True)
