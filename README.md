🌱 Blockchain-Based Green Hydrogen Credit Registry
Transparent • Verifiable • Fraud-Resistant
🚀 Overview

This project implements an end-to-end registry for Green Hydrogen (H₂) credits.
It ensures that every kilogram of H₂ produced from renewable energy is:

Measured by trusted IoT sensors

Signed with cryptographic proofs

Minted into digital credits

Transferred / Retired with owner signatures

Anchored into immutable blockchain blocks with Merkle roots

Auditable via Sparse Merkle Tree proofs & optional on-chain anchoring

✨ Key Features

Ed25519 signatures for all events, transfers, and retirements

Non-overlapping production windows (prevents double counting)

Evidence uploads (CSV/logs tied to events via SHA-256)

Block closing → Merkle root over all transactions

State root proofs (Sparse Merkle Tree for balances)

Marketplace to list/buy credits

Reports: retirement feed for compliance & ESG audits

🛠️ Components

app.py → Flask server exposing all API endpoints

api_tester.py → Original E2E tester (phase 1/2/3)

showcase_cli.py → Judge-friendly CLI (step-by-step with clear prints)

api_tester_pretty.py → Optional verbose tester (compact JSON previews)

📂 Project Structure
├── app.py                 # Flask API server
├── api_tester.py          # Core E2E test script (reference for signatures)
├── showcase_cli.py        # Judge-facing CLI, reuses api_tester helpers
├── api_tester_pretty.py   # Alternative pretty output tester
├── requirements.txt       # Python dependencies
└── README.md              # (this file)

⚙️ Setup & Installation
# 1. Clone the repo
git clone https://github.com/<your-org>/<your-repo>.git
cd <your-repo>

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python app.py

Requirements

Python 3.9+

Libraries: flask, requests, cryptography, python-dotenv

Optional: web3 (if anchoring to Ethereum)

▶️ Demo Instructions
1. Quick Judge Demo
python showcase_cli.py --base http://127.0.0.1:5000


Produces step-by-step banners (easy to follow live)

Preserves exact signature flow from api_tester.py

2. Developer Test
python api_tester.py --base http://127.0.0.1:5000


Full verification including on-chain anchor (if RPC/contract provided)

3. Pretty Output (optional)
python api_tester_pretty.py --base http://127.0.0.1:5000


Compact JSON previews + recap

🔑 Core API Endpoints

GET /api/v1/health → Server health

POST /api/v1/accounts → Create account (producer/buyer)

POST /api/v1/sensors → Register sensor

POST /api/v1/evidence/upload → Upload run evidence

POST /api/v1/events → Submit signed event

POST /api/v1/credits/mint → Mint credits

POST /api/v1/credits/transfer → Owner-signed transfer

POST /api/v1/credits/retire → Owner-signed retire

POST /api/v1/blocks/close → Close block → Merkle root

GET /api/v1/blocks/latest → Inspect latest block

GET /api/v2/state/root → Global state root (SMT)

GET /api/v2/state/proof/<id> → Account proof

POST /api/v1/market/offers → List credits

POST /api/v1/market/buy → Buy credits

GET /api/v1/reports/retirements → Retirement report

🧩 How It All Ties Together

Sensor signs event → ensures tamper-proof production data

Evidence uploaded → hash bound to event

Server verifies signature + overlap window

Mint credits → digital units of Green H₂

Close block → credits activated under Merkle root

Transfers / Retires → owner-signed, immutable record

Sparse Merkle proofs → balances independently verifiable

Marketplace → trade credits fairly

Reports → regulators/auditors can confirm claims

🎯 Impact

Fraud prevention: stops double-counting or fake claims

Transparency: verifiable credits & balances

Compliance: easy proof for regulators & ESG reporting

Adoption: increases trust in renewable H₂ markets

📖 License

MIT (or specify your hackathon license)

want me to also generate a diagram (ascii / mermaid / latex) to put in the README showing the full lifecycle: Sensor → Event → Block → Marketplace → Retirements?
