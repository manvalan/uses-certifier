"""Verifica che il codice non sia cambiato dopo la certificazione."""
from dataclasses import dataclass, field
from pathlib import Path

from . import analyzers


@dataclass
class VerifyResult:
    """Elementi ancora validi e bollini decaduti."""

    valid: int = 0
    changed: list = field(default_factory=list)
    missing: list = field(default_factory=list)

    @property
    def ok(self):
        """Vero se nessun bollino è decaduto."""
        return not self.changed and not self.missing


def verify(certificate, root):
    """Confronta le impronte del certificato con i sorgenti attuali."""
    result = VerifyResult()
    for stamped in certificate["files"]:
        path = Path(root) / stamped["name"]
        if not path.is_file():
            result.missing.append(stamped["name"])
            continue
        _compare(stamped, _current_hashes(path, stamped["name"]), result)
    return result


def _current_hashes(path, relpath):
    """Impronte attuali degli elementi di un sorgente, per nome."""
    text = path.read_text(encoding="utf-8")
    module = analyzers.analyze(path, text, relpath)
    return {(e.kind, e.qualname): e.source_hash for e in module.walk()}


def _compare(stamped, current, result):
    """Confronta ricorsivamente un elemento certificato e i suoi figli."""
    key = (stamped["kind"], stamped["name"])
    if key not in current:
        result.missing.append(stamped["name"])
    elif current[key] != stamped["sha256"]:
        result.changed.append(stamped["name"])
    else:
        result.valid += 1
    for child in stamped["children"]:
        _compare(child, current, result)
