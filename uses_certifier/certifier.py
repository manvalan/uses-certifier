"""Certification of a tree of sources."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from . import analyzers, duplicates, evaluator, markers
from .model import NOT_CERTIFIED
from .scoring import Scorer


@dataclass
class Certification:
    """Result of certifying a project."""

    root: str
    rulebook: object
    scorer: Scorer
    modules: list = field(default_factory=list)
    failures: dict = field(default_factory=dict)

    @property
    def level(self):
        """Project level: the worst of its source files."""
        levels = [m.level for m in self.modules]
        if self.failures or not levels:
            return NOT_CERTIFIED
        return self.scorer.worst(levels)

    def entities(self):
        """Every certified element."""
        for module in self.modules:
            yield from module.walk()


def certify(root, rulebook, config, signer):
    """Analyse, evaluate and stamp every source under root."""
    result = _empty_result(Path(root), rulebook, signer)
    for path, relpath in discover(root, config):
        _analyze_into(result, path, relpath)
    _evaluate_all(result)
    return result


def _evaluate_all(result):
    """Apply the rules and stamp every analysed source."""
    duplicates.mark(result.modules)
    for module in result.modules:
        evaluator.evaluate(module, result.rulebook.rules)
        result.scorer.score_tree(module)


def _empty_result(root, rulebook, signer):
    """Empty result; for a single file the root is its folder."""
    base = root.parent if root.is_file() else root
    scorer = Scorer(rulebook.certification, rulebook.digest, signer)
    return Certification(str(base), rulebook, scorer)


def _analyze_into(result, path, relpath):
    """Add an analysed source, or the reason it was rejected."""
    try:
        module = analyze_file(path, relpath)
    except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
        result.failures[relpath] = f"{type(exc).__name__}: {exc}"
        return
    result.modules.append(module)


def analyze_file(path, relpath):
    """Analyse a source file; line numbers refer to the real file."""
    original = Path(path).read_text(encoding="utf-8")
    module = analyzers.analyze(path, markers.strip_stamps(original), relpath)
    _to_original_lines(module, markers.line_map(original))
    _number_duplicate_names(module)
    return module


def _number_duplicate_names(module):
    """Give repeated names (anonymous callbacks, property setters) an
    ordinal, so that each element keeps its own certificate entry."""
    seen = {}
    for entity in module.walk():
        key = (entity.kind, entity.qualname)
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            entity.qualname = f"{entity.qualname}#{seen[key]}"


def _to_original_lines(module, numbers):
    """Turn line numbers of the stamp-free source into real ones."""
    def real(number):
        return numbers[number - 1] if 0 < number <= len(numbers) else number
    for entity in module.walk():
        entity.first_line = real(entity.first_line)
        entity.start_line = real(entity.start_line)
        entity.end_line = real(entity.end_line)


def discover(root, config):
    """Supported sources under root, honouring exclusions."""
    root = Path(root)
    if root.is_file():
        yield root, root.name
        return
    for path in sorted(_walk(root)):
        relpath = path.relative_to(root).as_posix()
        if analyzers.is_supported(path) and not config.is_excluded(relpath):
            yield path, relpath


def _walk(root):
    """Every file under root, skipping hidden folders."""
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            yield Path(folder) / name
