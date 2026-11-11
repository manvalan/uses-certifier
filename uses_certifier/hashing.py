"""Fingerprints of code and rules."""
import hashlib
import json


def digest(text):
    """Hex SHA-256 of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def lines_digest(lines):
    """Fingerprint of a block of lines, ignoring trailing whitespace."""
    return digest("\n".join(line.rstrip() for line in lines))


def json_digest(data):
    """Stable fingerprint of a JSON-serialisable structure."""
    return digest(json.dumps(data, sort_keys=True, default=str))
