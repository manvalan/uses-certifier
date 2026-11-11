"""Scelta dell'analizzatore in base all'estensione del sorgente."""
from pathlib import Path

from . import generic, python

PYTHON_SUFFIXES = {".py", ".pyw"}


def is_supported(path):
    """Vero se il certificatore sa analizzare il file."""
    path = Path(path)
    return path.suffix in PYTHON_SUFFIXES or generic.supports(path)


def analyze(path, text, relpath):
    """Analizza un sorgente e restituisce l'elemento modulo."""
    if Path(path).suffix in PYTHON_SUFFIXES:
        return python.analyze(text, relpath)
    return generic.analyze(path, text, relpath)
