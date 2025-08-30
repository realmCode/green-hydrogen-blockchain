import os, json, sys
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()
RPC = os.environ["WEB3_RPC_URL"]
PK  = os.environ["PRIVATE_KEY"]

USAGE = "usage: python anchor_block.py <contract_addr> <block_id_int> <merkle_root_hex>"

def main():
    if len(sys.argv) != 4:
        print(USAGE); sys.exit(1)
    contract_addr = Web3.to_checksum_address(sys.argv[1])
    ########### mongo id to int block id
    
    import hashlib

    # turn mongo _id string into deterministic uint
    mongo_id = sys.argv[2] # see it from phase1_full_report.md
    block_id = int(hashlib.sha256(mongo_id.encode()).hexdigest(), 16) % (2**256)    

    # block_id = int(sys.argv[2])
    #######################################################
    root_hex = sys.argv[3].lower()
    if not root_hex.startswith("0x"):
        root_hex = "0x" + root_hex
    if len(root_hex) != 66:  # 0x + 64 hex
        raise SystemExit("merkle_root must be 32 bytes (64 hex chars)")

    w3 = Web3(Web3.HTTPProvider(RPC))
    acct = w3.eth.account.from_key(PK)

    with open("CreditAnchor.abi.json") as f:
        abi = json.load(f)
    contract = w3.eth.contract(address=contract_addr, abi=abi)

    tx = contract.functions.anchor(block_id, root_hex).build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "maxFeePerGas": w3.to_wei("20", "gwei"),
        "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
        "chainId": w3.eth.chain_id,
    })
    signed = w3.eth.account.sign_transaction(tx, PK)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    rcpt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print("Anchored. Tx:", tx_hash.hex())
    # read back to confirm
    stored = contract.functions.roots(block_id).call()
    print("Stored root:", stored.hex())

    # optional: decode event
    evs = contract.events.Anchored().process_receipt(rcpt)
    if evs:
        e = evs[0]["args"]
        print("Event Anchored:", {"blockId": e["blockId"], "root": e["root"].hex(), "caller": e["caller"]})

if __name__ == "__main__":
    main()


#OUTPUT

# Anchored. Tx: 295e1bb13e89369c0d68ec3a0dbda51fafca42e55be845a18295fd1588799ce1
# Stored root: 4c755cd890bb714a854626173e7787f2943f1e4099601238dd8ed535a6698a4e
# Event Anchored: {'blockId': 45344809525780088554741427786933097859216388521764039501863031528213753093365, 'root': '4c755cd890bb714a854626173e7787f2943f1e4099601238dd8ed535a6698a4e', 'caller': '0xe67Ec73c5331859927Ee959cFA0aCCc94c55AF03'}