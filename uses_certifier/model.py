"""Data structures shared by the certifier."""
from dataclasses import dataclass, field
from typing import Any, Optional

NOT_CERTIFIED = "none"


# uses-cert: ignore[CC-008] fields mirror the YAML rule format
@dataclass
class Rule:
    """A rule read from a YAML ruleset."""

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


# uses-cert: ignore[CC-008] read-only record, one field per column
@dataclass
class Violation:
    """A rule an element does not satisfy."""

    rule_id: str
    severity: str
    title: str
    metric: str
    value: Any
    threshold: Any
    operator: str
    line: int
    suppressed: bool = False


# uses-cert: ignore[CC-008] data holder for the certificate
@dataclass
class Entity:
    """A stampable element: function, class or source file.

    Line numbers refer to the source with stamp lines removed.
    first_line includes decorators; start_line is the definition line.
    A synthetic class is rebuilt from method names and has no declaration
    of its own in the source.
    """

    kind: str
    name: str
    qualname: str
    language: str
    path: str
    first_line: int
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
    synthetic: bool = False

    @property
    def is_public(self):
        """True when the name does not start with an underscore."""
        return not self.name.startswith("_")

    def walk(self):
        """Yield the element and all of its descendants."""
        yield self
        for child in self.children:
            yield from child.walk()
