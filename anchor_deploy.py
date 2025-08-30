import os, json
from dotenv import load_dotenv
from web3 import Web3
from solcx import install_solc, set_solc_version, compile_source

load_dotenv()
RPC = os.environ["WEB3_RPC_URL"]
PK  = os.environ["PRIVATE_KEY"]

SRC = r"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract CreditAnchor {
    event Anchored(uint256 indexed blockId, bytes32 indexed root, address indexed caller);
    mapping(uint256 => bytes32) public roots;

    function anchor(uint256 blockId, bytes32 root) external returns (bool) {
        require(roots[blockId] == bytes32(0), "already anchored");
        roots[blockId] = root;
        emit Anchored(blockId, root, msg.sender);
        return true;
    }
}
"""

def main():
    # 1) compile
    install_solc("0.8.20")
    set_solc_version("0.8.20")
    compiled = compile_source(SRC, output_values=["abi", "bin"])
    _, c = list(compiled.items())[0]
    abi, bytecode = c["abi"], c["bin"]

    # 2) connect + account
    w3 = Web3(Web3.HTTPProvider(RPC))
    acct = w3.eth.account.from_key(PK)

    # 3) build & send deploy tx
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = Contract.constructor().build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "maxFeePerGas": w3.to_wei("20", "gwei"),
        "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
        "chainId": w3.eth.chain_id,
    })
    signed = w3.eth.account.sign_transaction(tx, PK)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

    rcpt = w3.eth.wait_for_transaction_receipt(tx_hash)

    addr = rcpt.contractAddress
    print("Contract deployed at:", addr)
    print("Tx:", tx_hash.hex())
    # save ABI for later
    with open("CreditAnchor.abi.json", "w") as f: json.dump(abi, f)

if __name__ == "__main__":
    main()
