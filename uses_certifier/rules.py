"""Caricamento dei ruleset YAML e della configurazione di certificazione."""
import os
from dataclasses import asdict, fields
from pathlib import Path

import yaml

from .hashing import json_digest
from .model import Rule

ENV_VAR = "USES_RULES_PATH"
RULE_FIELDS = {f.name for f in fields(Rule)}
REQUIRED = ("id", "name", "title", "scope", "metric", "operator",
            "threshold", "severity")


class RulesError(Exception):
    """Ruleset mancanti o non validi."""


class RuleBook:
    """Regole attive e configurazione dei livelli."""

    def __init__(self, rules, certification):
        self.rules = rules
        self.certification = certification

    @property
    def digest(self):
        """Impronta di regole e livelli: cambia se cambia il giudizio."""
        data = [asdict(r) for r in self.rules]
        return json_digest({"rules": data, "cert": self.certification})

    def rulesets(self):
        """Nomi dei ruleset da cui provengono le regole attive."""
        return sorted({rule.ruleset for rule in self.rules})


def resolve_path(explicit=None):
    """Cartella delle regole: opzione, variabile d'ambiente o errore."""
    chosen = explicit or os.environ.get(ENV_VAR)
    if not chosen:
        raise RulesError(
            "Cartella delle regole non indicata: usa --rules oppure "
            f"la variabile {ENV_VAR} (clone di manvalan/uses-rules).")
    path = Path(chosen)
    if not (path / "rules").is_dir():
        raise RulesError(f"{path} non contiene la cartella rules/")
    return path


def load(root, config):
    """Carica le regole da root applicando la configurazione del progetto."""
    rules = []
    for file in sorted((Path(root) / "rules").glob("*.y*ml")):
        rules += _load_ruleset(file, config.rulesets)
    rules = config.apply_overrides(rules)
    certification = _read_yaml(Path(root) / "certification.yaml")
    return RuleBook([r for r in rules if r.enabled], certification)


def _load_ruleset(file, wanted):
    """Regole di un file, se il ruleset è tra quelli richiesti."""
    data = _read_yaml(file)
    name = data.get("ruleset", file.stem)
    if wanted and name not in wanted:
        return []
    return [_make_rule(raw, name, file) for raw in data.get("rules", [])]


def _make_rule(raw, ruleset, file):
    """Costruisce una regola controllando i campi obbligatori."""
    missing = [key for key in REQUIRED if key not in raw]
    if missing:
        raise RulesError(f"{file.name}: regola {raw.get('id', '?')} "
                         f"senza {', '.join(missing)}")
    known = {k: v for k, v in raw.items() if k in RULE_FIELDS}
    return Rule(ruleset=ruleset, **known)


def _read_yaml(path):
    """Legge un file YAML, segnalando in modo chiaro se manca."""
    if not path.is_file():
        raise RulesError(f"File mancante: {path}")
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}
