# Phase-1 Full Run
- Base: `http://127.0.0.1:5000/api/v1`
- Time: `2025-08-30T15:30:11.930773+00:00`

### Health
```json
{
  "ok": true
}
```

### Producer Account
```json
{
  "id": "68b31904742e3da17f401393",
  "name": "GreenCo",
  "role": "producer",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAWaAamnIl+D0r5WbcSDGsbLSBWwZidG3/E1pjsMrq8Pk=\n-----END PUBLIC KEY-----\n",
  "_id": "68b31904742e3da17f401393"
}
```

### Buyer Account
```json
{
  "id": "68b31904742e3da17f401395",
  "name": "SteelCo",
  "role": "buyer",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAhGnM/uMSslAFgIsBZaVVbv7gU7hIVd2HCVQeoQyV6II=\n-----END PUBLIC KEY-----\n",
  "_id": "68b31904742e3da17f401395"
}
```

### Sensor
```json
{
  "id": "68b31904742e3da17f401397",
  "name": "StackMeter-01",
  "electrolyzer_id": "ELX-1756567812",
  "owner_account_id": "68b31904742e3da17f401393",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAgabrXoMhEacLgAUdBB2fRmdx9LBNV40EipsOjaOm8ng=\n-----END PUBLIC KEY-----\n"
}
```

### Evidence
```json
{
  "id": "68b31904742e3da17f401399",
  "filename": "evidence_full.csv",
  "sha256_hex": "867847599370d5c8021adce7b2308b7c79e1e0f9f89256475eba2b4f0f18d0c6",
  "stored_path": "evidence\\867847599370_evidence_full.csv",
  "created_at": "2025-08-30T15:30:12.815747",
  "_id": "68b31904742e3da17f401399"
}
```

### Event Canonical (Signed by Sensor)
```json
{
  "sensor_id": "68b31904742e3da17f401397",
  "start_time": "2025-08-30T15:30:12",
  "end_time": "2025-08-30T17:30:12",
  "energy_kwh": 1000.0,
  "hydrogen_kg": 20.0,
  "evidence_id": "68b31904742e3da17f401399"
}
```

### Sensor Signature
e9bd068ceeadaa1489f9a0e3c89b8ba28dbebb94ca9a4a185260eec0cd11952be27cc0c36b78ef422d2ded835f366205ce4da2501cef9a22b9bace349a583300

### Event Submitted
```json
{
  "id": "68b31905742e3da17f40139b",
  "sensor_id": "68b31904742e3da17f401397",
  "electrolyzer_id": "ELX-1756567812",
  "start_time": "2025-08-30T15:30:12",
  "end_time": "2025-08-30T17:30:12",
  "energy_kwh": 1000.0,
  "hydrogen_kg": 20.0,
  "evidence_id": "68b31904742e3da17f401399",
  "payload_canonical": "{\"end_time\":\"2025-08-30T17:30:12\",\"energy_kwh\":1000.0,\"evidence_id\":\"68b31904742e3da17f401399\",\"hydrogen_kg\":20.0,\"sensor_id\":\"68b31904742e3da17f401397\",\"start_time\":\"2025-08-30T15:30:12\"}",
  "sensor_signature_hex": "e9bd068ceeadaa1489f9a0e3c89b8ba28dbebb94ca9a4a185260eec0cd11952be27cc0c36b78ef422d2ded835f366205ce4da2501cef9a22b9bace349a583300",
  "signature_valid": true,
  "overlap_ok": true,
  "verified": true
}
```

### Minted (pending)
```json
{
  "credit_id": "68b31905742e3da17f40139d",
  "amount_g": 20000,
  "owner_account_id": "68b31904742e3da17f401393",
  "status": "pending",
  "tx_hash": "90f8512d9ad24f9ae6250515885576f64b602d3b1c1b03dd5c089154f0214140"
}
```

### Producer Balance (pre)
```json
{
  "account_id": "68b31904742e3da17f401393",
  "balance_g": 20000,
  "balance_kg": 20.0
}
```

### Buyer Balance (pre)
```json
{
  "account_id": "68b31904742e3da17f401395",
  "balance_g": 0,
  "balance_kg": 0.0
}
```

### Transfer Canonical
```json
{
  "credit_id": "68b31905742e3da17f40139d",
  "from_account_id": "68b31904742e3da17f401393",
  "to_account_id": "68b31904742e3da17f401395",
  "amount_g": 5000
}
```

### Transfer Signature (producer)
94e218418ee6eee8424429793ac37b2fce81e1837b6853af5b74a033201d22c7c2d2f773e0016ccadfaf26f8e90c0289a3c2108a01b685118eaa66e7460fa000

### Transfer Result
```json
{
  "ok": true,
  "to_credit_id": "68b31906742e3da17f40139f",
  "tx_hash": "4986eaeafc69e429d3e6e7dff3b91cf88b0ab55198aa58b7f75f0d6f0e1d7175"
}
```

### Retire Canonical
```json
{
  "credit_id": "68b31906742e3da17f40139f",
  "owner_account_id": "68b31904742e3da17f401395",
  "amount_g": 3000,
  "reason": "green steel batch A"
}
```

### Retire Signature (buyer)
7972170d1385bf9552faac94a9d4f135cdb9aeebcd759144ff3b0cb702994e84b45d6132ff19d3dd36375d0b706fe60745f97aa12d695a52d745399b887ed705

### Retire Result
```json
{
  "ok": true,
  "retired_from_credit_id": "68b31906742e3da17f40139f",
  "amount_g": 3000,
  "tx_hash": "2dab74e86b0488079f9ecf02dec242e170445ef50fbae52eb83686c70e026481"
}
```

### Producer Balance (post)
```json
{
  "account_id": "68b31904742e3da17f401393",
  "balance_g": 15000,
  "balance_kg": 15.0
}
```

### Buyer Balance (post)
```json
{
  "account_id": "68b31904742e3da17f401395",
  "balance_g": 2000,
  "balance_kg": 2.0
}
```

### Block Closed (Merkle)
```json
{
  "block_id": "68b31907742e3da17f4013a3",
  "onchain_block_id": "81946780071360465493902026452768846047245876513403836220540536633607810354307",
  "merkle_root": "41f8c48181a0c4254c924179369ce28db1049a2adc6e4277d814837751766aec",
  "tx_count": 8,
  "chain_hash": "20d74db2d9e9c73b51daf57670883a62bae1ea363f8e290d36c28d44e1403074",
  "contract_address": "0x361F4564D6F6f045aDECf7EB7f88D018FfA7447A",
  "anchored": true,
  "anchor_tx": "18ed08f2e62c873bd9d9c37ba1a5470c4101f06136a2759f58986066a4915a5e"
}
```

### Latest Block
```json
{
  "block_id": "68b31907742e3da17f4013a3",
  "prev_hash": null,
  "merkle_root": "41f8c48181a0c4254c924179369ce28db1049a2adc6e4277d814837751766aec",
  "chain_hash": "20d74db2d9e9c73b51daf57670883a62bae1ea363f8e290d36c28d44e1403074",
  "tx_count": 8,
  "created_at": "2025-08-30T15:30:15.615000",
  "anchor_tx": "18ed08f2e62c873bd9d9c37ba1a5470c4101f06136a2759f58986066a4915a5e",
  "onchain_block_id": "81946780071360465493902026452768846047245876513403836220540536633607810354307",
  "contract_address": "0x361F4564D6F6f045aDECf7EB7f88D018FfA7447A",
  "chain": "sepolia"
}
```

### Anchor Skipped
```json
{
  "reason": "TRY_ANCHOR not set or no block"
}
```

### All Events
```json
[
  {
    "id": "68b31905742e3da17f40139b",
    "sensor_id": "68b31904742e3da17f401397",
    "electrolyzer_id": "ELX-1756567812",
    "start_time": "2025-08-30T15:30:12",
    "end_time": "2025-08-30T17:30:12",
    "energy_kwh": 1000.0,
    "hydrogen_kg": 20.0,
    "evidence_id": "68b31904742e3da17f401399",
    "signature_valid": true,
    "overlap_ok": true,
    "verified": true
  }
]
```

