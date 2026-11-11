"""Stamp codes: unique to one element, one version of its code and one
version of the rules.

With a secret key (USES_CERT_KEY or --key-file) codes are HMAC-SHA256
signatures that cannot be forged without the key. Without a key they are
plain SHA-256 fingerprints: unique, but anyone can recompute them.
"""
import hashlib
import hmac
import os
from pathlib import Path

KEY_ENV = "USES_CERT_KEY"
GROUPS, GROUP_SIZE = 4, 4


class Signer:
    """Computes stamp and certificate codes."""

    def __init__(self, key=b""):
        self.key = key

    @property
    def keyed(self):
        """True when codes are signed with a secret key."""
        return bool(self.key)

    def code(self, *parts):
        """Code such as 7F3A-9C1E-2B4D-5A60 for the given parts."""
        message = "\x1f".join(str(part) for part in parts).encode("utf-8")
        if self.keyed:
            raw = hmac.new(self.key, message, hashlib.sha256).hexdigest()
        else:
            raw = hashlib.sha256(message).hexdigest()
        raw = raw.upper()
        return "-".join(raw[i * GROUP_SIZE:(i + 1) * GROUP_SIZE]
                        for i in range(GROUPS))

    def stamp(self, entity, rules_digest, level):
        """Stamp code of one element at one level."""
        return self.code("stamp", entity.path, entity.kind, entity.qualname,
                         entity.source_hash, rules_digest, level)


def load(key_file=None):
    """Signer from a key file, the environment variable, or unkeyed."""
    if key_file:
        return Signer(Path(key_file).read_bytes().strip())
    return Signer(os.environ.get(KEY_ENV, "").encode("utf-8"))
