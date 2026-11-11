"""Configuration of the project being certified (.uses-certifier.yaml)."""
from dataclasses import dataclass, field, replace
from fnmatch import fnmatch
from pathlib import Path

import yaml

FILENAME = ".uses-certifier.yaml"
DEFAULT_EXCLUDE = [
    ".git/*", "*/.git/*", "*/node_modules/*", "node_modules/*",
    "*/__pycache__/*", "*venv/*", "build/*", "dist/*", "*.min.js",
]
STRICT, MIGRATION = "strict", "migration"


class ConfigError(ValueError):
    """The project configuration is not valid."""


@dataclass
class ProjectConfig:
    """Project choices: rulesets, exclusions, thresholds, minimum level
    and mode (strict, or migration for existing programs)."""

    rulesets: list = field(default_factory=list)
    exclude: list = field(default_factory=list)
    overrides: dict = field(default_factory=dict)
    min_level: str = ""
    rules_path: str = ""
    mode: str = STRICT
    migration_min_coverage: float = 0

    def __post_init__(self):
        if self.mode not in (STRICT, MIGRATION):
            raise ConfigError(f"unknown mode {self.mode!r}: use "
                             f"{STRICT} or {MIGRATION}")

    @property
    def migrating(self):
        """True while an existing program is being migrated."""
        return self.mode == MIGRATION

    def is_excluded(self, relpath):
        """True when the relative path matches an exclusion."""
        patterns = DEFAULT_EXCLUDE + self.exclude
        return any(fnmatch(relpath, pattern) for pattern in patterns)

    def apply_overrides(self, rules):
        """Apply the per-id rule changes."""
        return [replace(r, **self.overrides.get(r.id, {})) for r in rules]


def load(root, explicit=None):
    """Read the project configuration, when present."""
    path = Path(explicit) if explicit else Path(root) / FILENAME
    if not path.is_file():
        return ProjectConfig()
    with open(path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    known = ProjectConfig.__dataclass_fields__
    return ProjectConfig(**{k: v for k, v in data.items() if k in known})
