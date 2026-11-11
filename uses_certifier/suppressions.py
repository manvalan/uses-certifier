"""Lettura delle direttive uses-cert: ignore[...] nei commenti."""
import re

DIRECTIVE = re.compile(r"uses-cert:\s*(ignore-file|ignore)(?:\[([^\]]*)\])?")
ALL = "*"


def parse_directive(line):
    """Restituisce (tipo, insieme di id) o None se la riga non ne ha."""
    match = DIRECTIVE.search(line)
    if not match:
        return None
    kind, ids = match.group(1), match.group(2)
    if not ids:
        return kind, {ALL}
    return kind, {item.strip() for item in ids.split(",") if item.strip()}


def ids_in_range(lines, first, last):
    """Id soppressi da direttive ignore tra le righe first e last (da 1)."""
    found = set()
    for line in lines[max(first - 1, 0):last]:
        parsed = parse_directive(line)
        if parsed and parsed[0] == "ignore":
            found |= parsed[1]
    return found


def file_ids(lines):
    """Id soppressi per l'intero sorgente da direttive ignore-file."""
    found = set()
    for line in lines:
        parsed = parse_directive(line)
        if parsed and parsed[0] == "ignore-file":
            found |= parsed[1]
    return found


def is_suppressed(rule_id, suppressed):
    """Vero se la regola è tra quelle soppresse."""
    return ALL in suppressed or rule_id in suppressed
