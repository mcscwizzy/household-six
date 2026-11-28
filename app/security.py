"""Local password hashing shared by authentication and account administration."""

import hashlib
import hmac
import secrets


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return salt.hex() + "." + derived.hex()


def verify_password(password, encoded):
    try:
        salt_hex, want = encoded.split(".", 1)
        got = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1, dklen=32).hex()
        return hmac.compare_digest(got, want)
    except (ValueError, TypeError, AttributeError):
        return False
