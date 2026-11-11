"""Configurazione del progetto da certificare (.uses-certifier.yaml)."""
from dataclasses import dataclass, field, replace
from fnmatch import fnmatch
from pathlib import Path

import yaml

FILENAME = ".uses-certifier.yaml"
DEFAULT_EXCLUDE = [
    ".git/*", "*/.git/*", "*/node_modules/*", "node_modules/*",
    "*/__pycache__/*", "*venv/*", "build/*", "dist/*", "*.min.js",
]


@dataclass
class ProjectConfig:
    """Scelte del progetto: ruleset, esclusioni, soglie e livello minimo."""

    rulesets: list = field(default_factory=list)
    exclude: list = field(default_factory=list)
    overrides: dict = field(default_factory=dict)
    min_level: str = ""
    rules_path: str = ""

    def is_excluded(self, relpath):
        """Vero se il percorso relativo corrisponde a un'esclusione."""
        patterns = DEFAULT_EXCLUDE + self.exclude
        return any(fnmatch(relpath, pattern) for pattern in patterns)

    def apply_overrides(self, rules):
        """Applica le modifiche alle regole indicate per id."""
        return [replace(r, **self.overrides.get(r.id, {})) for r in rules]


def load(root, explicit=None):
    """Legge la configurazione del progetto, se presente."""
    path = Path(explicit) if explicit else Path(root) / FILENAME
    if not path.is_file():
        return ProjectConfig()
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    known = ProjectConfig.__dataclass_fields__
    return ProjectConfig(**{k: v for k, v in data.items() if k in known})
