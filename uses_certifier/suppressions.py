"""Reading of uses-cert: ignore[...] directives in comments."""
import re

from . import markers

IDS = re.compile(r"uses-cert:\s*(ignore-file|ignore)(?:\[([^\]]*)\])?")
ALL = "*"


def parse_directive(line):
    """Return (kind, set of ids) or None when the line has no directive."""
    if markers.kind(line) not in ("ignore", "ignore-file"):
        return None
    match = IDS.search(line)
    kind, ids = match.group(1), match.group(2)
    if not ids:
        return kind, {ALL}
    return kind, {item.strip() for item in ids.split(",") if item.strip()}


def for_definition(lines, first_line, def_line):
    """Ids suppressed for a definition: the marker block above it and
    the lines from its decorators to its definition line (1-based)."""
    start = markers.block_above(lines, first_line)
    return _collect(lines[start:def_line], "ignore")


def file_ids(lines):
    """Ids suppressed for the whole source by ignore-file directives."""
    return _collect(lines, "ignore-file")


def _collect(lines, wanted):
    """Union of the ids of every directive of the wanted kind."""
    found = set()
    for line in lines:
        parsed = parse_directive(line)
        if parsed and parsed[0] == wanted:
            found |= parsed[1]
    return found


def is_suppressed(rule_id, suppressed):
    """True when the rule is among the suppressed ones."""
    return ALL in suppressed or rule_id in suppressed
