# Phase-1 Full Run
- Base: `http://127.0.0.1:5000/api/v1`
- Time: `2025-08-30T16:34:04.237071+00:00`

### Health
```json
{
  "ok": true
}
```

### Producer Account
```json
{
  "id": "68b327fc742e3da17f4013a5",
  "name": "GreenCo",
  "role": "producer",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAsGY321Kjxyzmv6mJpO1D0hG4JbQLlLRmS/HsFJXpUH0=\n-----END PUBLIC KEY-----\n",
  "_id": "68b327fc742e3da17f4013a5"
}
```

### Buyer Account
```json
{
  "id": "68b327fd742e3da17f4013a7",
  "name": "SteelCo",
  "role": "buyer",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAoQcEwwJHPwQSLIgGlyLd4O8D5+9ia71ZcyZ6mhKvZZI=\n-----END PUBLIC KEY-----\n",
  "_id": "68b327fd742e3da17f4013a7"
}
```

### Sensor
```json
{
  "id": "68b327fe742e3da17f4013a9",
  "name": "StackMeter-01",
  "electrolyzer_id": "ELX-1756571646",
  "owner_account_id": "68b327fc742e3da17f4013a5",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAtO0Y19OJrx+QGzIGLcRmZri3rt1WVNnV1ahfBkdpXJE=\n-----END PUBLIC KEY-----\n"
}
```

### Evidence
```json
{
  "id": "68b327fe742e3da17f4013ab",
  "filename": "evidence_full.csv",
  "sha256_hex": "867847599370d5c8021adce7b2308b7c79e1e0f9f89256475eba2b4f0f18d0c6",
  "stored_path": "evidence\\867847599370_evidence_full.csv",
  "created_at": "2025-08-30T16:34:06.665469",
  "_id": "68b327fe742e3da17f4013ab"
}
```

### Event Canonical (Signed by Sensor)
```json
{
  "sensor_id": "68b327fe742e3da17f4013a9",
  "start_time": "2025-08-30T16:34:06",
  "end_time": "2025-08-30T18:34:06",
  "energy_kwh": 1000.0,
  "hydrogen_kg": 20.0,
  "evidence_id": "68b327fe742e3da17f4013ab"
}
```

### Sensor Signature
14d0a3621d35c2322929f15efeb1b0aa3b9668ddbba761446655ec1a85e2d16c6c09f9807e08dfb1aaf319b552064cc85f6137a88bd9a9a000f1e76539b90d06

### Event Submitted
```json
{
  "id": "68b327ff742e3da17f4013ad",
  "sensor_id": "68b327fe742e3da17f4013a9",
  "electrolyzer_id": "ELX-1756571646",
  "start_time": "2025-08-30T16:34:06",
  "end_time": "2025-08-30T18:34:06",
  "energy_kwh": 1000.0,
  "hydrogen_kg": 20.0,
  "evidence_id": "68b327fe742e3da17f4013ab",
  "payload_canonical": "{\"end_time\":\"2025-08-30T18:34:06\",\"energy_kwh\":1000.0,\"evidence_id\":\"68b327fe742e3da17f4013ab\",\"hydrogen_kg\":20.0,\"sensor_id\":\"68b327fe742e3da17f4013a9\",\"start_time\":\"2025-08-30T16:34:06\"}",
  "sensor_signature_hex": "14d0a3621d35c2322929f15efeb1b0aa3b9668ddbba761446655ec1a85e2d16c6c09f9807e08dfb1aaf319b552064cc85f6137a88bd9a9a000f1e76539b90d06",
  "signature_valid": true,
  "overlap_ok": true,
  "verified": true
}
```

### Minted (pending)
```json
{
  "credit_id": "68b327ff742e3da17f4013af",
  "amount_g": 20000,
  "owner_account_id": "68b327fc742e3da17f4013a5",
  "status": "pending",
  "tx_hash": "281b05cc3a38fb507b504675685504c57d8a7c031d48e6b4c5a40b02ff0ab8e6"
}
```

### Producer Balance (pre)
```json
{
  "account_id": "68b327fc742e3da17f4013a5",
  "balance_g": 20000,
  "balance_kg": 20.0
}
```

### Buyer Balance (pre)
```json
{
  "account_id": "68b327fd742e3da17f4013a7",
  "balance_g": 0,
  "balance_kg": 0.0
}
```

### Transfer Canonical
```json
{
  "credit_id": "68b327ff742e3da17f4013af",
  "from_account_id": "68b327fc742e3da17f4013a5",
  "to_account_id": "68b327fd742e3da17f4013a7",
  "amount_g": 5000
}
```

### Transfer Signature (producer)
1d457e3c287f9b7aee8066ddfbdb628429cca1ff391e7034dd747f0a77a0b9587765c5111978164ffdafdda4aed62c7ff58e1f0b2206cd98bb558d7594467000

### Transfer Result
```json
{
  "ok": true,
  "to_credit_id": "68b32800742e3da17f4013b1",
  "tx_hash": "301bc6b04d129c015e7ded1f92e9985f95aa14687c5eb45644948a6fa1d42c23"
}
```

### Retire Canonical
```json
{
  "credit_id": "68b32800742e3da17f4013b1",
  "owner_account_id": "68b327fd742e3da17f4013a7",
  "amount_g": 3000,
  "reason": "green steel batch A"
}
```

### Retire Signature (buyer)
380c0745e0e7525137e62b52708cd94aa6d5b0cf46278be1bd5d2639285646d7304edc67c47e0df3361e9ec84b73c89cbd8821c2cf0ca467e22eda75b92bbf01

### Retire Result
```json
{
  "ok": true,
  "retired_from_credit_id": "68b32800742e3da17f4013b1",
  "amount_g": 3000,
  "tx_hash": "0347d094c7779bfca39c92fd01254b997b109ff0e6c5c32a9f2fd9aed1190f24"
}
```

### Producer Balance (post)
```json
{
  "account_id": "68b327fc742e3da17f4013a5",
  "balance_g": 15000,
  "balance_kg": 15.0
}
```

### Buyer Balance (post)
```json
{
  "account_id": "68b327fd742e3da17f4013a7",
  "balance_g": 2000,
  "balance_kg": 2.0
}
```

### Block Closed (Merkle)
```json
{
  "block_id": "68b32802742e3da17f4013b5",
  "onchain_block_id": "74014085841491529059581906606222636997717802053467212386246365037116583828068",
  "merkle_root": "b475047d7408c17cb6b339e8824f7967ad860b038fdf996ca2ed75461b7390be",
  "tx_count": 8,
  "chain_hash": "ec9ef039915075627a1f6264cc6ffa04ea1e4d4cb80dca75a7be303a60b4f919",
  "contract_address": "0x361F4564D6F6f045aDECf7EB7f88D018FfA7447A",
  "anchored": true,
  "anchor_tx": "8786fc5f852f6296bdc1a46c56447b2c9796eaa94344a85ab2c276da68f7f8b4"
}
```

### Latest Block
```json
{
  "block_id": "68b32802742e3da17f4013b5",
  "prev_hash": null,
  "merkle_root": "b475047d7408c17cb6b339e8824f7967ad860b038fdf996ca2ed75461b7390be",
  "chain_hash": "ec9ef039915075627a1f6264cc6ffa04ea1e4d4cb80dca75a7be303a60b4f919",
  "tx_count": 8,
  "created_at": "2025-08-30T16:34:10.158000",
  "anchor_tx": "8786fc5f852f6296bdc1a46c56447b2c9796eaa94344a85ab2c276da68f7f8b4",
  "onchain_block_id": "74014085841491529059581906606222636997717802053467212386246365037116583828068",
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
    "id": "68b327ff742e3da17f4013ad",
    "sensor_id": "68b327fe742e3da17f4013a9",
    "electrolyzer_id": "ELX-1756571646",
    "start_time": "2025-08-30T16:34:06",
    "end_time": "2025-08-30T18:34:06",
    "energy_kwh": 1000.0,
    "hydrogen_kg": 20.0,
    "evidence_id": "68b327fe742e3da17f4013ab",
    "signature_valid": true,
    "overlap_ok": true,
    "verified": true
  }
]
```

