# Part of J2J (http://JRuDevels.org)

# At-rest encryption of guest account passwords in the database,
# keyed by a master password from the config file ([database]
# master_password). Stored values carry an explicit "enc1:" prefix so
# plaintext rows written before the feature existed (or while no
# master password is configured) are always distinguishable.

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PREFIX = "enc1:"
# OWASP-recommended PBKDF2-HMAC-SHA256 work factor for this use case.
ITERATIONS = 600_000


class CryptoError(ValueError):
    """Raised when a stored value cannot be decrypted with the
    configured master password."""


def looks_encrypted(value):
    return isinstance(value, str) and value.startswith(PREFIX)


def generate_salt():
    return base64.b16encode(os.urandom(16)).decode("ascii").lower()


def derive_key(master, salt):
    """Derive the urlsafe-b64 Fernet key from *master* and the hex
    *salt* stored alongside the database."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32,
        salt=salt.encode("ascii"), iterations=ITERATIONS)
    return base64.urlsafe_b64encode(kdf.derive(master.encode("utf-8")))


def encrypt(key, plaintext):
    token = Fernet(key).encrypt(plaintext.encode("utf-8"))
    return PREFIX + token.decode("ascii")


def decrypt(key, stored):
    if not looks_encrypted(stored):
        raise CryptoError("value is not encrypted")
    try:
        return Fernet(key).decrypt(stored[len(PREFIX):].encode("ascii")) \
            .decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError):
        raise CryptoError("decryption failed (wrong master password or "
                          "corrupted value)")
