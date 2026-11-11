"""Loading of YAML rulesets and of the certification settings."""
import os
from dataclasses import asdict, fields
from pathlib import Path

import yaml

from . import rules_cache
from .hashing import json_digest
from .model import Rule

ENV_VAR = "USES_RULES_PATH"
RULE_FIELDS = {f.name for f in fields(Rule)}
REQUIRED = ("id", "name", "title", "scope", "metric", "operator",
            "threshold", "severity")


class RulesError(Exception):
    """Missing or invalid rulesets."""


class RuleBook:
    """Active rules and level settings."""

    def __init__(self, rules, certification, principles=()):
        self.rules = rules
        self.certification = certification
        self.principles = list(principles)

    @property
    def digest(self):
        """Fingerprint of rules and levels: changes with the yardstick."""
        data = [asdict(r) for r in self.rules]
        return json_digest({"rules": data, "cert": self.certification})

    def rulesets(self):
        """Names of the rulesets the active rules come from."""
        return sorted({rule.ruleset for rule in self.rules})


def resolve_path(explicit=None):
    """Rules folder: option, environment variable, fetched cache, or an
    error."""
    chosen = explicit or os.environ.get(ENV_VAR) or rules_cache.cached()
    if not chosen:
        raise RulesError(
            "Rules not found: run `uses-certifier fetch-rules`, or use "
            f"--rules or the {ENV_VAR} variable (a clone of "
            "manvalan/uses-rules).")
    path = Path(chosen)
    if not (path / "rules").is_dir():
        raise RulesError(f"{path} has no rules/ folder")
    return path


def load(root, config):
    """Load the rules from root, applying the project configuration."""
    rules = []
    for file in sorted((Path(root) / "rules").glob("*.y*ml")):
        rules += _load_ruleset(file, config.rulesets)
    rules = config.apply_overrides(rules)
    certification = _read_yaml(Path(root) / "certification.yaml")
    return RuleBook([r for r in rules if r.enabled], certification,
                    load_principles(root))


def load_principles(root):
    """Design principles of every file in principles/ (may be none).

    They are guidance for people and agents: they are not measured and
    do not take part in the rules fingerprint.
    """
    found = []
    for file in sorted((Path(root) / "principles").glob("*.y*ml")):
        found += _read_yaml(file).get("principles", [])
    return found


def _load_ruleset(file, wanted):
    """Rules of a file, when its ruleset is among the requested ones."""
    data = _read_yaml(file)
    name = data.get("ruleset", file.stem)
    if wanted and name not in wanted:
        return []
    return [_make_rule(raw, name, file) for raw in data.get("rules", [])]


def _make_rule(raw, ruleset, file):
    """Build a rule, checking the mandatory fields."""
    missing = [key for key in REQUIRED if key not in raw]
    if missing:
        raise RulesError(f"{file.name}: rule {raw.get('id', '?')} "
                         f"lacks {', '.join(missing)}")
    known = {k: v for k, v in raw.items() if k in RULE_FIELDS}
    return Rule(ruleset=ruleset, **known)


def _read_yaml(path):
    """Read a YAML file, reporting clearly when it is missing."""
    if not path.is_file():
        raise RulesError(f"Missing file: {path}")
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
