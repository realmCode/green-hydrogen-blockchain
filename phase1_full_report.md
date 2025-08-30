# Phase-1 Full Run
- Base: `http://127.0.0.1:5000/api/v1`
- Time: `2025-08-30T13:53:26.692898+00:00`

### Health
```json
{
  "ok": true
}
```

### Producer Account
```json
{
  "id": "68b30256a54f3f44a75d4ed7",
  "name": "GreenCo",
  "role": "producer",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAWAf/wfHhaRu4K4pZDtjFAmw6pt5CvwTwwSO6UIV2NBM=\n-----END PUBLIC KEY-----\n",
  "_id": "68b30256a54f3f44a75d4ed7"
}
```

### Buyer Account
```json
{
  "id": "68b30256a54f3f44a75d4ed9",
  "name": "SteelCo",
  "role": "buyer",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEA/wQiqqanUG806CLmR0ejzhQVB+uFcRq1FyY6sgumQeI=\n-----END PUBLIC KEY-----\n",
  "_id": "68b30256a54f3f44a75d4ed9"
}
```

### Sensor
```json
{
  "id": "68b30257a54f3f44a75d4edb",
  "name": "StackMeter-01",
  "electrolyzer_id": "ELX-1756562007",
  "owner_account_id": "68b30256a54f3f44a75d4ed7",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAw1AoKCpKB1/vUyCWEmAqqdfzMoQmc3Q+AdDUVfPSIN8=\n-----END PUBLIC KEY-----\n"
}
```

### Evidence
```json
{
  "id": "68b2c0159479f4c224ec46ba",
  "filename": "evidence_run1.csv",
  "sha256_hex": "867847599370d5c8021adce7b2308b7c79e1e0f9f89256475eba2b4f0f18d0c6",
  "stored_path": "evidence\\867847599370_evidence_run1.csv",
  "created_at": "2025-08-30T09:10:45.021000"
}
```

### Event Canonical (Signed by Sensor)
```json
{
  "sensor_id": "68b30257a54f3f44a75d4edb",
  "start_time": "2025-08-30T13:53:27",
  "end_time": "2025-08-30T15:53:27",
  "energy_kwh": 1000.0,
  "hydrogen_kg": 20.0,
  "evidence_id": "68b2c0159479f4c224ec46ba"
}
```

### Sensor Signature
e5a5ab224cd0126a3c2be7e79626e863571108827cf4fa94991d8e10aa37425f2c9c7aa78221cf0279ca703d215f846648fcfe9be075107c1eeb459658f09909

### Event Submitted
```json
{
  "id": "68b30257a54f3f44a75d4edd",
  "sensor_id": "68b30257a54f3f44a75d4edb",
  "electrolyzer_id": "ELX-1756562007",
  "start_time": "2025-08-30T13:53:27",
  "end_time": "2025-08-30T15:53:27",
  "energy_kwh": 1000.0,
  "hydrogen_kg": 20.0,
  "evidence_id": "68b2c0159479f4c224ec46ba",
  "payload_canonical": "{\"end_time\":\"2025-08-30T15:53:27\",\"energy_kwh\":1000.0,\"evidence_id\":\"68b2c0159479f4c224ec46ba\",\"hydrogen_kg\":20.0,\"sensor_id\":\"68b30257a54f3f44a75d4edb\",\"start_time\":\"2025-08-30T13:53:27\"}",
  "sensor_signature_hex": "e5a5ab224cd0126a3c2be7e79626e863571108827cf4fa94991d8e10aa37425f2c9c7aa78221cf0279ca703d215f846648fcfe9be075107c1eeb459658f09909",
  "signature_valid": true,
  "overlap_ok": true,
  "verified": true
}
```

### Minted (pending)
```json
{
  "credit_id": "68b30257a54f3f44a75d4edf",
  "amount_g": 20000,
  "owner_account_id": "68b30256a54f3f44a75d4ed7",
  "status": "pending",
  "tx_hash": "e465dc7ba7cc16d09bd708d0c8dd05fca78d774971a8cff188719be63de3f31d"
}
```

### Producer Balance (pre)
```json
{
  "account_id": "68b30256a54f3f44a75d4ed7",
  "balance_g": 20000,
  "balance_kg": 20.0
}
```

### Buyer Balance (pre)
```json
{
  "account_id": "68b30256a54f3f44a75d4ed9",
  "balance_g": 0,
  "balance_kg": 0.0
}
```

### Transfer Canonical
```json
{
  "credit_id": "68b30257a54f3f44a75d4edf",
  "from_account_id": "68b30256a54f3f44a75d4ed7",
  "to_account_id": "68b30256a54f3f44a75d4ed9",
  "amount_g": 5000
}
```

### Transfer Signature (producer)
4d86cf242f62855109c3fc5bc25cc82259aed956e7d72a5688e8921d839845fab870574381bf289a713fc3c439cba54a05dd26ff70d92e64a28e95491c208d0f

### Transfer Result
```json
{
  "ok": true,
  "to_credit_id": "68b30258a54f3f44a75d4ee1",
  "tx_hash": "0406e6604ee3d50afdec5457fad091fe4506123e1a7ed54792abce2b4f2d7d17"
}
```

### Retire Canonical
```json
{
  "credit_id": "68b30258a54f3f44a75d4ee1",
  "owner_account_id": "68b30256a54f3f44a75d4ed9",
  "amount_g": 3000,
  "reason": "green steel batch A"
}
```

### Retire Signature (buyer)
c2b78b4545895b912210d9efaa0de175280cb6d50dcb3627cd529a6e158d87e1e3b36f8357ff214428f9d7c7bde1ef88735754ad9f2b100394a283be5ebc1d09

### Retire Result
```json
{
  "ok": true,
  "retired_from_credit_id": "68b30258a54f3f44a75d4ee1",
  "amount_g": 3000,
  "tx_hash": "119f5d1efe6fa4d5959b1b1d55f82b99c0d2f4eb2cde20ab8304920d76f5ae47"
}
```

### Producer Balance (post)
```json
{
  "account_id": "68b30256a54f3f44a75d4ed7",
  "balance_g": 15000,
  "balance_kg": 15.0
}
```

### Buyer Balance (post)
```json
{
  "account_id": "68b30256a54f3f44a75d4ed9",
  "balance_g": 2000,
  "balance_kg": 2.0
}
```

### Block Closed (Merkle)
```json
{
  "block_id": "68b30259a54f3f44a75d4ee5",
  "merkle_root": "4c755cd890bb714a854626173e7787f2943f1e4099601238dd8ed535a6698a4e",
  "tx_count": 7,
  "chain_hash": "2dbe0b0d900e5334e762c4c2c035461240fb9d42035601cc557f1137518d0dda"
}
```

### Latest Block
```json
{
  "block_id": "68b30259a54f3f44a75d4ee5",
  "prev_hash": null,
  "merkle_root": "4c755cd890bb714a854626173e7787f2943f1e4099601238dd8ed535a6698a4e",
  "chain_hash": "2dbe0b0d900e5334e762c4c2c035461240fb9d42035601cc557f1137518d0dda",
  "tx_count": 7,
  "created_at": "2025-08-30T13:53:29.597000",
  "anchor_tx": null
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
    "id": "68b30257a54f3f44a75d4edd",
    "sensor_id": "68b30257a54f3f44a75d4edb",
    "electrolyzer_id": "ELX-1756562007",
    "start_time": "2025-08-30T13:53:27",
    "end_time": "2025-08-30T15:53:27",
    "energy_kwh": 1000.0,
    "hydrogen_kg": 20.0,
    "evidence_id": "68b2c0159479f4c224ec46ba",
    "signature_valid": true,
    "overlap_ok": true,
    "verified": true
  },
  {
    "id": "68b300bd637cd1bc1a07e0b5",
    "sensor_id": "68b300bc637cd1bc1a07e0b4",
    "electrolyzer_id": "ELX-001",
    "start_time": "2025-08-29T10:00:00",
    "end_time": "2025-08-29T12:00:00",
    "energy_kwh": 1000.0,
    "hydrogen_kg": 20.0,
    "evidence_id": "68b2c0159479f4c224ec46ba",
    "signature_valid": true,
    "overlap_ok": false,
    "verified": false
  },
  {
    "id": "68b2ff4962fbb57863ad7216",
    "sensor_id": "68b2ff4862fbb57863ad7215",
    "electrolyzer_id": "ELX-001",
    "start_time": "2025-08-29T10:00:00",
    "end_time": "2025-08-29T12:00:00",
    "energy_kwh": 1000.0,
    "hydrogen_kg": 20.0,
    "evidence_id": "68b2c0159479f4c224ec46ba",
    "signature_valid": true,
    "overlap_ok": false,
    "verified": false
  },
  {
    "id": "68b2ff31ccbb034dda5534e5",
    "sensor_id": "68b2ff31ccbb034dda5534e4",
    "electrolyzer_id": "ELX-001",
    "start_time": "2025-08-29T10:00:00",
    "end_time": "2025-08-29T12:00:00",
    "energy_kwh": 1000.0,
    "hydrogen_kg": 20.0,
    "evidence_id": "68b2c0159479f4c224ec46ba",
    "signature_valid": true,
    "overlap_ok": false,
    "verified": false
  },
  {
    "id": "68b2c4ba7a30392ec22b04f4",
    "sensor_id": "68b2c4ba7a30392ec22b04f3",
    "electrolyzer_id": "ELX-001",
    "start_time": "2025-08-29T10:00:00",
    "end_time": "2025-08-29T12:00:00",
    "energy_kwh": 1000.0,
    "hydrogen_kg": 20.0,
    "evidence_id": "68b2c0159479f4c224ec46ba",
    "signature_valid": true,
    "overlap_ok": false,
    "verified": false
  },
  {
    "id": "68b2c0159479f4c224ec46bb",
    "sensor_id": "68b2c0149479f4c224ec46b9",
    "electrolyzer_id": "ELX-001",
    "start_time": "2025-08-29T10:00:00",
    "end_time": "2025-08-29T12:00:00",
    "energy_kwh": 1000.0,
    "hydrogen_kg": 20.0,
    "evidence_id": "68b2c0159479f4c224ec46ba",
    "signature_valid": true,
    "overlap_ok": true,
    "verified": true
  }
]
```

