import os, json, sys
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()
RPC = os.environ["WEB3_RPC_URL"]

def main():
    if len(sys.argv) != 4:
        print("usage: python verify_anchor.py <contract_addr> <block_id_int> <expect_root_hex>")
        sys.exit(1)
    addr = Web3.to_checksum_address(sys.argv[1])
    ########### mongo id to int block id
    
    import hashlib

    # turn mongo _id string into deterministic uint
    mongo_id = sys.argv[2] # see it from phase1_full_report.md
    block_id = int(hashlib.sha256(mongo_id.encode()).hexdigest(), 16) % (2**256)    

    # block_id = int(sys.argv[2])
    #######################################################
    # block_id = int(sys.argv[2]) 
    expect = sys.argv[3].lower()
    if not expect.startswith("0x"):
        expect = "0x" + expect

    w3 = Web3(Web3.HTTPProvider(RPC))
    with open("CreditAnchor.abi.json") as f:
        abi = json.load(f)
    c = w3.eth.contract(address=addr, abi=abi)

    root =  "0x"+c.functions.roots(block_id).call().hex()
    ok = (root.lower() == expect.lower())
    print("on-chain root :", root)
    print("expected       :", expect)
    print("match?         :", ok)

if __name__ == "__main__":
    main()
