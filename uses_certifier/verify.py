"""Checks that stamps written in the sources still match their code.

A stamp code depends on file path, element, code fingerprint, rules and
level: it is valid only for that exact element. Any change to the code,
a copy to another element or a hand-edited level makes it invalid.
"""
from dataclasses import dataclass, field
from pathlib import Path

from . import markers

PROBLEMS = {
    "invalid": "code changed since it was certified, or stamp tampered",
    "missing": "certified element no longer present, or stamp missing",
    "uncertified": "element not covered by the certificate",
    "below_level": "certified below the required level",
}


def _empty_problems():
    """One empty list per kind of problem."""
    return {kind: [] for kind in PROBLEMS}


@dataclass
class VerifyResult:
    """Valid stamps and the problems found, by kind."""

    valid: int = 0
    problems: dict = field(default_factory=_empty_problems)
    certificate_ok: bool = True
    notes: list = field(default_factory=list)

    @property
    def ok(self):
        """True when every stamp is valid and nothing is uncovered."""
        return self.certificate_ok and not any(self.problems.values())

    @property
    def invalid(self):
        """Elements whose stamp does not match their code."""
        return self.problems["invalid"]

    @property
    def missing(self):
        """Elements without stamp, or stamps without element."""
        return self.problems["missing"]

    def add(self, kind, name):
        """Record a problem."""
        self.problems[kind].append(name)

    def check(self, name, written, expected):
        """Record the comparison of a written and an expected code."""
        if written is None:
            self.add("missing", name)
        elif written != expected:
            self.add("invalid", name)
        else:
            self.valid += 1


def verify_inline(cert, root):
    """Compare the stamps written in the sources with fresh ones."""
    result = VerifyResult()
    for module in cert.modules:
        text = (Path(root) / module.path).read_text(encoding="utf-8")
        _check_module(result, module, written_stamps(text))
    return result


def _check_module(result, module, written):
    """Compare the stamps written in one source with fresh ones."""
    for entity in module.walk():
        if entity.synthetic:
            continue
        key = 0 if entity.kind == "module" else entity.first_line
        result.check(f"{module.path}:{entity.qualname}",
                     written.get(key), f"{entity.level} {entity.stamp}")


def written_stamps(text):
    """Codes written in a source, keyed by the 1-based number of the line
    they stamp (0 for the file stamp)."""
    lines = text.splitlines()
    found = {}
    for index, line in enumerate(lines):
        parsed = markers.parse_stamp(line)
        if parsed:
            found[_stamped_line(lines, index, parsed[0])] = \
                f"{parsed[1]} {parsed[2]}"
    return found


def _stamped_line(lines, index, kind):
    """Number of the line a stamp refers to (0 for the file stamp)."""
    if kind == "stamp-file":
        return 0
    return _next_code_line(lines, index) + 1


def _next_code_line(lines, index):
    """Index of the first line after index that is not a marker."""
    index += 1
    while index < len(lines) and markers.kind(lines[index]):
        index += 1
    return index
