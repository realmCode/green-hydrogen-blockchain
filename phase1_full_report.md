# Phase-1 Full Client Run
- Timestamp: `2025-08-30T09:30:29.789845+00:00`
- Base URL: `http://127.0.0.1:5000`

### Health
```json
{
  "ok": true
}
```

### Account Created (Producer)
```json
{
  "_id": "68b2c4b97a30392ec22b04f1",
  "id": "68b2c4b97a30392ec22b04f1",
  "name": "GreenCo",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAlbMhtGYkiyXByI6xJzJ3+aJ0Tg211tkZnQa9R0mUBwg=\n-----END PUBLIC KEY-----\n",
  "role": "producer"
}
```

### Account Created (Buyer)
```json
{
  "_id": "68b2c4b97a30392ec22b04f2",
  "id": "68b2c4b97a30392ec22b04f2",
  "name": "SteelCo",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAnSby5FUuFlcdERexCNE9Jv0O8T281XATGSfCpSgk0ws=\n-----END PUBLIC KEY-----\n",
  "role": "buyer"
}
```

### Sensor Registered
```json
{
  "electrolyzer_id": "ELX-001",
  "id": "68b2c4ba7a30392ec22b04f3",
  "name": "StackMeter-01",
  "owner_account_id": "68b2c4b97a30392ec22b04f1",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEATkVs4a0+FvTrHJI38+JaL0qn8rvy9TZQnqehM7G4iFo=\n-----END PUBLIC KEY-----\n"
}
```

### Evidence Uploaded
```json
{
  "created_at": "2025-08-30T09:10:45.021000",
  "filename": "evidence_run1.csv",
  "id": "68b2c0159479f4c224ec46ba",
  "sha256_hex": "867847599370d5c8021adce7b2308b7c79e1e0f9f89256475eba2b4f0f18d0c6",
  "stored_path": "evidence\\867847599370_evidence_run1.csv"
}
```

### Canonical Payload (to be signed by Sensor)
```json
{
  "sensor_id": "68b2c4ba7a30392ec22b04f3",
  "start_time": "2025-08-29T10:00:00",
  "end_time": "2025-08-29T12:00:00",
  "energy_kwh": 1000.0,
  "hydrogen_kg": 20.0,
  "evidence_id": "68b2c0159479f4c224ec46ba"
}
```

### Sensor Signature (hex)
e4c285f44a656adb6dc06acfffdea6e4b109540b83ad3bd6779bbad8b63a9948352cb20fdd12fd0b723b945ea7400da64156203003b56a916ce9ceaa5396c50d

### Event Submitted
```json
{
  "electrolyzer_id": "ELX-001",
  "end_time": "2025-08-29T12:00:00",
  "energy_kwh": 1000.0,
  "evidence_id": "68b2c0159479f4c224ec46ba",
  "hydrogen_kg": 20.0,
  "id": "68b2c4ba7a30392ec22b04f4",
  "overlap_ok": false,
  "payload_canonical": "{\"end_time\":\"2025-08-29T12:00:00\",\"energy_kwh\":1000.0,\"evidence_id\":\"68b2c0159479f4c224ec46ba\",\"hydrogen_kg\":20.0,\"sensor_id\":\"68b2c4ba7a30392ec22b04f3\",\"start_time\":\"2025-08-29T10:00:00\"}",
  "sensor_id": "68b2c4ba7a30392ec22b04f3",
  "sensor_signature_hex": "e4c285f44a656adb6dc06acfffdea6e4b109540b83ad3bd6779bbad8b63a9948352cb20fdd12fd0b723b945ea7400da64156203003b56a916ce9ceaa5396c50d",
  "signature_valid": true,
  "start_time": "2025-08-29T10:00:00",
  "verified": false
}
```

### Credits Minted
```json
[
  {
    "error": "event not verified"
  },
  400
]
```

