# verify_tx.py
# usage: python verify_tx.py <api_base> <tx_hash>
# example: python verify_tx.py http://127.0.0.1:5000/api/v1 119f5d1e...

import sys, requests, hashlib
from web3 import Web3


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fold_proof(tx_hash, proof):
    cur = tx_hash.lower()
    for step in proof:
        sib = step["sibling"].lower()
        if step.get("is_right", False):
            cur = sha256_hex((cur + sib).encode())
        else:
            cur = sha256_hex((sib + cur).encode())
    return cur


def main():
    api = sys.argv[1]
    th = sys.argv[2].lower()
    p = requests.get(f"{api}/proof/tx/{th}", timeout=30)
    print(p.url)
    p = p.json()
    root_calc = fold_proof(th, p["proof"])
    ok_local = root_calc == p["merkle_root"].lower()
    print("local merkle:", root_calc)
    print("server root :", p["merkle_root"])
    print("local==server?", ok_local)

    # check on-chain
    w3 = Web3(
        Web3.HTTPProvider("https://eth-sepolia.g.alchemy.com/v2/47qnmmhS4pv3SC7AIZQ51")
    )
    abi = [
        {
            "inputs": [
                {"internalType": "uint256", "name": "blockId", "type": "uint256"}
            ],
            "name": "roots",
            "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
            "stateMutability": "view",
            "type": "function",
        }
    ]
    c = w3.eth.contract(address=Web3.to_checksum_address(p["contract_address"]), abi=abi)
    onchain_root = c.functions.roots(int(p["onchain_block_id"])).call().hex()
    ok_chain = onchain_root.lower() == p["merkle_root"].lower()
    print("on-chain root:", onchain_root)
    print("server==chain?", ok_chain)
    print("VERIFIED:", ok_local and ok_chain)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python verify_tx.py <api_base> <tx_hash>")
        sys.exit(1)
    main()
