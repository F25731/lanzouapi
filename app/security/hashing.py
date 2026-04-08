from __future__ import annotations

import base64
import hashlib
import hmac
import os


DEFAULT_ITERATIONS = 260000


def hash_secret(secret: str, iterations: int = DEFAULT_ITERATIONS) -> str:
    salt = base64.urlsafe_b64encode(os.urandom(16)).decode("utf-8").rstrip("=")
    digest = _pbkdf2(secret, salt, iterations)
    return "pbkdf2_sha256${0}${1}${2}".format(iterations, salt, digest)


def verify_secret(secret: str, encoded: str) -> bool:
    try:
        algorithm, iterations_raw, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = _pbkdf2(secret, salt, int(iterations_raw))
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


def _pbkdf2(secret: str, salt: str, iterations: int) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
