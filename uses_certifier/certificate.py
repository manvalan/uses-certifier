"""JSON certificate: every element's stamp with its fingerprint.

The certificate is reproducible: the same sources, rules and key always
give byte-identical content, so it can be committed next to the code.
"""
import json
import os
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .model import NOT_CERTIFIED

FORMAT_VERSION = 3


def build(cert, root="."):
    """Certificate structure, ready for JSON; root as seen from the
    certificate's folder."""
    data = {
        "format": FORMAT_VERSION,
        "certifier": {"name": "uses-certifier", "version": __version__},
        "root": root,
        "signed": cert.scorer.signer.keyed,
        "rules": {"rulesets": cert.rulebook.rulesets(),
                  "digest": cert.rulebook.digest},
        "levels": [level["id"] for level in cert.scorer.levels],
        "level": cert.level,
        "summary": summary(cert),
        "failures": cert.failures,
        "files": [entity_dict(m) for m in cert.modules],
    }
    data["certificate_id"] = certificate_id(data, cert.scorer.signer)
    return data


def certificate_id(data, signer):
    """Code of the whole certificate: binds every stamp, rules and level."""
    stamps = [e["stamp"] for f in data["files"] for e in walk(f)]
    return signer.code("certificate", data["rules"]["digest"],
                       data["level"], *stamps)


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
    return save(build_for(cert, path), path)


def build_for(cert, path):
    """Certificate structure for a file at path (root relative to it)."""
    folder = Path(path).resolve().parent
    root = Path(os.path.relpath(Path(cert.root).resolve(), folder))
    return build(cert, root.as_posix())


def save(data, path):
    """Write certificate data to a file; return it."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return data


def read(path):
    """Read a certificate from a file."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def sources_root(path, data):
    """Folder of the certified sources, from the certificate's location."""
    return Path(path).resolve().parent / data["root"]
