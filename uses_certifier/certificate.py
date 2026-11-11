"""Certificato JSON: il bollino di ogni elemento con la sua impronta."""
import json
from dataclasses import asdict
from datetime import datetime, timezone

from . import __version__
from .model import NOT_CERTIFIED

FORMAT_VERSION = 1


def build(cert):
    """Struttura del certificato pronta per JSON."""
    return {
        "format": FORMAT_VERSION,
        "certifier": {"name": "uses-certifier", "version": __version__},
        "issued_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "root": cert.root,
        "rules": {"rulesets": cert.rulebook.rulesets(),
                  "digest": cert.rulebook.digest},
        "level": cert.level,
        "summary": summary(cert),
        "failures": cert.failures,
        "files": [entity_dict(m) for m in cert.modules],
    }


def summary(cert):
    """Conteggio degli elementi per tipo e per livello."""
    counts = {}
    for entity in cert.entities():
        per_kind = counts.setdefault(entity.kind, {})
        per_kind[entity.level] = per_kind.get(entity.level, 0) + 1
    return counts


def entity_dict(entity):
    """Un elemento con figli, metriche, violazioni e bollino."""
    return {
        "kind": entity.kind, "name": entity.qualname,
        "language": entity.language,
        "lines": [entity.start_line, entity.end_line],
        "sha256": entity.source_hash, "metrics": entity.metrics,
        "violations": [asdict(v) for v in entity.violations],
        "score": entity.score, "level": entity.level,
        "certified": entity.level != NOT_CERTIFIED, "stamp": entity.stamp,
        "children": [entity_dict(c) for c in entity.children],
    }


def write(cert, path):
    """Scrive il certificato su file."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(build(cert), handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def read(path):
    """Legge un certificato da file."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
