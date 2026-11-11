"""Helpers shared by the output formats."""

KIND_LABELS = {"module": "source files", "class": "classes",
               "function": "methods and functions"}


def badge(level):
    """Short text badge of the level."""
    return f"[{level.upper()}]".ljust(8)


def describe(violation):
    """One-line description of a violation."""
    text = (f"{violation.rule_id} {violation.title} "
            f"(measured {violation.value}, threshold {violation.operator} "
            f"{violation.threshold})")
    return text + (" [suppressed]" if violation.suppressed else "")


def with_violations(entity):
    """Default filter: only elements with violations."""
    return bool(entity.violations)


def everything(entity):
    """Full filter: every element."""
    return entity is not None


def summary_rows(cert):
    """(kind, level, count) rows sorted by kind and level."""
    counts = {}
    for entity in cert.entities():
        key = (entity.kind, entity.level)
        counts[key] = counts.get(key, 0) + 1
    order = list(KIND_LABELS)
    return sorted(((k, lvl, n) for (k, lvl), n in counts.items()),
                  key=lambda row: (order.index(row[0]),
                                   cert.scorer.order(row[1])))
