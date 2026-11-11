"""Choice of analyser by source file extension."""
from pathlib import Path

from . import generic, python

PYTHON_SUFFIXES = {".py", ".pyw"}


def is_supported(path):
    """True when the certifier can analyse the file."""
    path = Path(path)
    return path.suffix in PYTHON_SUFFIXES or generic.supports(path)


def analyze(path, text, relpath):
    """Analyse a source (stamp lines already removed); return the module
    element."""
    if Path(path).suffix in PYTHON_SUFFIXES:
        return python.analyze(text, relpath)
    return generic.analyze(path, text, relpath)
