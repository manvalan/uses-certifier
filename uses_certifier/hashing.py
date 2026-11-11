"""Impronte digitali del codice e delle regole."""
import hashlib
import json


def digest(text):
    """SHA-256 esadecimale di una stringa."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def lines_digest(lines):
    """Impronta di un blocco di righe, ignorando gli spazi a fine riga."""
    return digest("\n".join(line.rstrip() for line in lines))


def json_digest(data):
    """Impronta stabile di una struttura serializzabile in JSON."""
    return digest(json.dumps(data, sort_keys=True, default=str))
