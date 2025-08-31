# app_keys.py
from flask import Blueprint, jsonify
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
import base64, binascii

bp_keys = Blueprint("keys", __name__, url_prefix="/api/v1/keys")

@bp_keys.post("/ed25519")
def generate_ed25519():
    # 1) generate
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()

    # 2) 32-byte seed for Ed25519 (RAW)
    private_seed = priv.private_bytes(
        encoding=Encoding.Raw,
        format=PrivateFormat.Raw,
        encryption_algorithm=NoEncryption()
    )  # 32 bytes

    # 3) SPKI PUBLIC KEY PEM (matches Python cryptography & your backend)
    public_pem = pub.public_bytes(
        encoding=Encoding.PEM,
        format=PublicFormat.SubjectPublicKeyInfo
    ).decode("ascii")

    # (optional) raw public key for debug
    public_raw = pub.public_bytes(
        encoding=Encoding.Raw,
        format=PublicFormat.Raw
    )

    return jsonify({
        "private_seed_hex": binascii.hexlify(private_seed).decode("ascii"),
        "public_key_pem": public_pem,
        "public_key_raw_b64": base64.b64encode(public_raw).decode("ascii"),
    })
