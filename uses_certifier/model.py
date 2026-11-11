"""Strutture dati condivise dal certificatore."""
from dataclasses import dataclass, field
from typing import Any, Optional

NOT_CERTIFIED = "none"


# uses-cert: ignore[CC-008] i campi rispecchiano il formato YAML
@dataclass
class Rule:
    """Una regola letta da un ruleset YAML."""

    id: str
    name: str
    title: str
    scope: str
    metric: str
    operator: str
    threshold: Any
    severity: str
    ruleset: str = ""
    applies_to: str = "all"
    languages: Optional[list] = None
    enabled: bool = True
    source: str = ""
    rationale: str = ""


# uses-cert: ignore[CC-008] dati di sola lettura, uno per colonna
@dataclass
class Violation:
    """Una regola non rispettata da un elemento."""

    rule_id: str
    severity: str
    title: str
    metric: str
    value: Any
    threshold: Any
    operator: str
    line: int
    suppressed: bool = False


# uses-cert: ignore[CC-008] contenitore di dati del certificato
@dataclass
class Entity:
    """Un elemento bollinabile: funzione, classe o sorgente."""

    kind: str
    name: str
    qualname: str
    language: str
    start_line: int
    end_line: int
    source_hash: str
    metrics: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    suppressions: set = field(default_factory=set)
    violations: list = field(default_factory=list)
    score: int = 100
    level: str = NOT_CERTIFIED
    stamp: str = ""

    @property
    def is_public(self):
        """Vero se il nome non inizia con un trattino basso."""
        return not self.name.startswith("_")

    def walk(self):
        """Restituisce l'elemento e tutti i discendenti."""
        yield self
        for child in self.children:
            yield from child.walk()
