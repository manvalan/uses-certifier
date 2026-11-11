"""Metriche testuali comuni a tutti i linguaggi."""
# uses-cert: ignore-file[CC-010] il file cerca proprio quelle parole
import re

from .. import suppressions
from ..hashing import digest
from ..model import Entity

TODO = re.compile(r"\b(TODO|FIXME|XXX)\b")


def max_width(lines):
    """Larghezza della riga più lunga."""
    return max((len(line.rstrip("\r\n")) for line in lines), default=0)


def todo_count(lines):
    """Numero di righe con TODO, FIXME o XXX."""
    return sum(1 for line in lines if TODO.search(line))


def module_entity(text, relpath, language):
    """Crea l'elemento che rappresenta l'intero sorgente."""
    lines = text.splitlines()
    return Entity(
        kind="module", name=relpath, qualname=relpath, language=language,
        start_line=1, end_line=len(lines), source_hash=digest(text),
        metrics={"length_lines": len(lines), "max_line_width":
                 max_width(lines), "todo_count": todo_count(lines)},
        suppressions=suppressions.file_ids(lines),
    )
