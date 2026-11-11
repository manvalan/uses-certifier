"""JSON certificate: every element's stamp with its fingerprint."""
import json
from dataclasses import asdict
from datetime import datetime, timezone

from . import __version__
from .model import NOT_CERTIFIED

FORMAT_VERSION = 2


def build(cert):
    """Certificate structure, ready for JSON."""
    signer = cert.scorer.signer
    data = {
        "format": FORMAT_VERSION,
        "certifier": {"name": "uses-certifier", "version": __version__},
        "issued_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "root": cert.root,
        "signed": signer.keyed,
        "rules": {"rulesets": cert.rulebook.rulesets(),
                  "digest": cert.rulebook.digest},
        "level": cert.level,
        "summary": summary(cert),
        "failures": cert.failures,
        "files": [entity_dict(m) for m in cert.modules],
    }
    data["certificate_id"] = certificate_id(data, signer)
    return data


def certificate_id(data, signer):
    """Code of the whole certificate: binds every stamp, rules and date."""
    stamps = [e["stamp"] for f in data["files"] for e in walk(f)]
    return signer.code("certificate", data["rules"]["digest"],
                       data["issued_at"], data["level"], *stamps)


def walk(item):
    """An element of the certificate and all its descendants."""
    yield item
    for child in item["children"]:
        yield from walk(child)


def summary(cert):
    """Element count by kind and level."""
    counts = {}
    for entity in cert.entities():
        per_kind = counts.setdefault(entity.kind, {})
        per_kind[entity.level] = per_kind.get(entity.level, 0) + 1
    return counts


def entity_dict(entity):
    """An element with children, metrics, violations and stamp."""
    return {
        "kind": entity.kind, "name": entity.qualname, "path": entity.path,
        "language": entity.language,
        "lines": [entity.first_line, entity.end_line],
        "sha256": entity.source_hash, "metrics": entity.metrics,
        "violations": [asdict(v) for v in entity.violations],
        "score": entity.score, "level": entity.level,
        "certified": entity.level != NOT_CERTIFIED, "stamp": entity.stamp,
        "children": [entity_dict(c) for c in entity.children],
    }


def write(cert, path):
    """Write the certificate to a file; return its data."""
    data = build(cert)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return data


def read(path):
    """Read a certificate from a file."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
