"""Certificazione di un albero di sorgenti."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from . import analyzers, evaluator
from .model import NOT_CERTIFIED
from .scoring import Scorer


@dataclass
class Certification:
    """Risultato della certificazione di un progetto."""

    root: str
    rulebook: object
    scorer: Scorer
    modules: list = field(default_factory=list)
    failures: dict = field(default_factory=dict)

    @property
    def level(self):
        """Livello del progetto: il peggiore tra i sorgenti."""
        levels = [m.level for m in self.modules]
        if self.failures or not levels:
            return NOT_CERTIFIED
        return self.scorer.worst(levels)

    def entities(self):
        """Tutti gli elementi certificati."""
        for module in self.modules:
            yield from module.walk()


def certify(root, rulebook, config):
    """Analizza, valuta e bollina tutti i sorgenti sotto root."""
    result = _empty_result(Path(root), rulebook)
    for path, relpath in discover(root, config):
        _certify_into(result, path, relpath)
    return result


def _empty_result(root, rulebook):
    """Risultato vuoto; per un singolo file la radice è la sua cartella."""
    base = root.parent if root.is_file() else root
    scorer = Scorer(rulebook.certification, rulebook.digest)
    return Certification(str(base), rulebook, scorer)


def _certify_into(result, path, relpath):
    """Aggiunge al risultato un sorgente certificato o il motivo del rifiuto."""
    try:
        module = certify_file(path, relpath, result.rulebook, result.scorer)
    except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
        result.failures[relpath] = f"{type(exc).__name__}: {exc}"
        return
    result.modules.append(module)


def certify_file(path, relpath, rulebook, scorer):
    """Analizza, valuta e bollina un singolo sorgente."""
    text = Path(path).read_text(encoding="utf-8")
    module = analyzers.analyze(path, text, relpath)
    evaluator.evaluate(module, rulebook.rules)
    scorer.score_tree(module)
    return module


def discover(root, config):
    """Sorgenti supportati sotto root, esclusioni comprese."""
    root = Path(root)
    if root.is_file():
        yield root, root.name
        return
    for path in sorted(_walk(root)):
        relpath = path.relative_to(root).as_posix()
        if analyzers.is_supported(path) and not config.is_excluded(relpath):
            yield path, relpath


def _walk(root):
    """Tutti i file sotto root, saltando le cartelle nascoste."""
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            yield Path(folder) / name
