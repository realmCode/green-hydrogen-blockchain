# Phase-1 Full Run
- Base: `http://127.0.0.1:5000/api/v1`
- Time: `2025-08-30T15:10:22.338555+00:00`

### Health
```json
{
  "ok": true
}
```

### Producer Account
```json
{
  "id": "68b3145e3366f44b40c69a0b",
  "name": "GreenCo",
  "role": "producer",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEA0MDDi0kUk2/RctbGR5Ems9p4Jfr5yzicWHpXXxqKMlA=\n-----END PUBLIC KEY-----\n",
  "_id": "68b3145e3366f44b40c69a0b"
}
```

### Buyer Account
```json
{
  "id": "68b3145e3366f44b40c69a0d",
  "name": "SteelCo",
  "role": "buyer",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEABQUNa+DeJE7G2IKE+TAcUWzjGb9nxWJ249Nivl02zq0=\n-----END PUBLIC KEY-----\n",
  "_id": "68b3145e3366f44b40c69a0d"
}
```

### Sensor
```json
{
  "id": "68b3145e3366f44b40c69a0f",
  "name": "StackMeter-01",
  "electrolyzer_id": "ELX-1756566623",
  "owner_account_id": "68b3145e3366f44b40c69a0b",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAHxBAUITq8swRMViLk2xJngBkrtEltwYOPiZn6XiIzXA=\n-----END PUBLIC KEY-----\n"
}
```

### Evidence
```json
{
  "id": "68b313513366f44b40c69a00",
  "filename": "evidence_full.csv",
  "sha256_hex": "867847599370d5c8021adce7b2308b7c79e1e0f9f89256475eba2b4f0f18d0c6",
  "stored_path": "evidence\\867847599370_evidence_full.csv",
  "created_at": "2025-08-30T15:05:53.535000"
}
```

### Event Canonical (Signed by Sensor)
```json
{
  "sensor_id": "68b3145e3366f44b40c69a0f",
  "start_time": "2025-08-30T15:10:23",
  "end_time": "2025-08-30T17:10:23",
  "energy_kwh": 1000.0,
  "hydrogen_kg": 20.0,
  "evidence_id": "68b313513366f44b40c69a00"
}
```

### Sensor Signature
2a35e716e09ef8fb9b5ab7cade5a3903e91f0089dbc52e500c95404ef53cf6e83d653815758d94766aaee4a59d5cdb752e973242353dbb6a68645b6aba363b06

### Event Submitted
```json
{
  "id": "68b3145f3366f44b40c69a11",
  "sensor_id": "68b3145e3366f44b40c69a0f",
  "electrolyzer_id": "ELX-1756566623",
  "start_time": "2025-08-30T15:10:23",
  "end_time": "2025-08-30T17:10:23",
  "energy_kwh": 1000.0,
  "hydrogen_kg": 20.0,
  "evidence_id": "68b313513366f44b40c69a00",
  "payload_canonical": "{\"end_time\":\"2025-08-30T17:10:23\",\"energy_kwh\":1000.0,\"evidence_id\":\"68b313513366f44b40c69a00\",\"hydrogen_kg\":20.0,\"sensor_id\":\"68b3145e3366f44b40c69a0f\",\"start_time\":\"2025-08-30T15:10:23\"}",
  "sensor_signature_hex": "2a35e716e09ef8fb9b5ab7cade5a3903e91f0089dbc52e500c95404ef53cf6e83d653815758d94766aaee4a59d5cdb752e973242353dbb6a68645b6aba363b06",
  "signature_valid": true,
  "overlap_ok": true,
  "verified": true
}
```

### Minted (pending)
```json
{
  "credit_id": "68b3145f3366f44b40c69a13",
  "amount_g": 20000,
  "owner_account_id": "68b3145e3366f44b40c69a0b",
  "status": "pending",
  "tx_hash": "6e03f61761b14e790f94edc48f15dc102e753ab47d1a8570e4f3ff0c5ef7487a"
}
```

### Producer Balance (pre)
```json
{
  "account_id": "68b3145e3366f44b40c69a0b",
  "balance_g": 20000,
  "balance_kg": 20.0
}
```

### Buyer Balance (pre)
```json
{
  "account_id": "68b3145e3366f44b40c69a0d",
  "balance_g": 0,
  "balance_kg": 0.0
}
```

### Transfer Canonical
```json
{
  "credit_id": "68b3145f3366f44b40c69a13",
  "from_account_id": "68b3145e3366f44b40c69a0b",
  "to_account_id": "68b3145e3366f44b40c69a0d",
  "amount_g": 5000
}
```

### Transfer Signature (producer)
d0e6e87724f5304adee2b6373a617dc0307986e8aaa527c549f7dbe1405aedd60f7458bad59d0c1e6c3a4005d7c76c6e3d83653840aad7975a7b80df80b88e05

