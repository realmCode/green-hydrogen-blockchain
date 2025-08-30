# Phase-1 Client Run Report

- Timestamp: `2025-08-30T09:10:42.085029`
- Base URL: `http://127.0.0.1:5000`

## Account Created
```json
{
  "_id": "68b2c0149479f4c224ec46b8",
  "id": "68b2c0149479f4c224ec46b8",
  "name": "GreenCo",
  "public_key_pem": "PRODUCER-PLACEHOLDER",
  "role": "producer"
}
```

## Sensor Registered
```json
{
  "electrolyzer_id": "ELX-001",
  "id": "68b2c0149479f4c224ec46b9",
  "name": "StackMeter-01",
  "owner_account_id": "68b2c0149479f4c224ec46b8",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEARHlDm2qWgkWJwU8Udo/nMuNZn1DSlubI0kJHIOTwQ5I=\n-----END PUBLIC KEY-----\n"
}
```

## Evidence Uploaded
```json
{
  "created_at": "2025-08-30T09:10:45.021091",
  "filename": "evidence_run1.csv",
  "id": "68b2c0159479f4c224ec46ba",
  "sha256_hex": "867847599370d5c8021adce7b2308b7c79e1e0f9f89256475eba2b4f0f18d0c6",
  "stored_path": "evidence\\867847599370_evidence_run1.csv"
}
```

## Canonical Payload (Signed by Sensor)
```json
{
  "sensor_id": "68b2c0149479f4c224ec46b9",
  "start_time": "2025-08-29T10:00:00",
  "end_time": "2025-08-29T12:00:00",
  "energy_kwh": 1000.0,
  "hydrogen_kg": 20.0,
  "evidence_id": "68b2c0159479f4c224ec46ba"
}
```

**Sensor Signature (hex):** `5618f8e910a5beb0c3863a9abbc0ced9dcfa0e2a3c33e05c84acbdec475f3b0bb6bd863a6525b2e064dc8bf7f45dc549a8a8607454a2e1c2293445e1c4017201`

## Event Submitted
```json
{
  "electrolyzer_id": "ELX-001",
  "end_time": "2025-08-29T12:00:00",
  "energy_kwh": 1000.0,
  "evidence_id": "68b2c0159479f4c224ec46ba",
  "hydrogen_kg": 20.0,
  "id": "68b2c0159479f4c224ec46bb",
  "overlap_ok": true,
  "payload_canonical": "{\"end_time\":\"2025-08-29T12:00:00\",\"energy_kwh\":1000.0,\"evidence_id\":\"68b2c0159479f4c224ec46ba\",\"hydrogen_kg\":20.0,\"sensor_id\":\"68b2c0149479f4c224ec46b9\",\"start_time\":\"2025-08-29T10:00:00\"}",
  "sensor_id": "68b2c0149479f4c224ec46b9",
  "sensor_signature_hex": "5618f8e910a5beb0c3863a9abbc0ced9dcfa0e2a3c33e05c84acbdec475f3b0bb6bd863a6525b2e064dc8bf7f45dc549a8a8607454a2e1c2293445e1c4017201",
  "signature_valid": true,
  "start_time": "2025-08-29T10:00:00",
  "verified": true
}
```

## All Events (Latest First)
```json
[
  {
    "electrolyzer_id": "ELX-001",
    "end_time": "2025-08-29T12:00:00",
    "energy_kwh": 1000.0,
    "evidence_id": "68b2c0159479f4c224ec46ba",
    "hydrogen_kg": 20.0,
    "id": "68b2c0159479f4c224ec46bb",
    "overlap_ok": true,
    "payload_canonical": "{\"end_time\":\"2025-08-29T12:00:00\",\"energy_kwh\":1000.0,\"evidence_id\":\"68b2c0159479f4c224ec46ba\",\"hydrogen_kg\":20.0,\"sensor_id\":\"68b2c0149479f4c224ec46b9\",\"start_time\":\"2025-08-29T10:00:00\"}",
    "sensor_id": "68b2c0149479f4c224ec46b9",
    "sensor_signature_hex": "5618f8e910a5beb0c3863a9abbc0ced9dcfa0e2a3c33e05c84acbdec475f3b0bb6bd863a6525b2e064dc8bf7f45dc549a8a8607454a2e1c2293445e1c4017201",
    "signature_valid": true,
    "start_time": "2025-08-29T10:00:00",
    "verified": true
  }
]
```

