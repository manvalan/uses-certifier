"""Readable terminal report."""
from .common import KIND_LABELS, badge, describe, summary_rows, \
    with_violations


def render(cert, select=with_violations):
    """Report text for the terminal."""
    out = [f"Certification of {cert.root}",
           f"Rules: {', '.join(cert.rulebook.rulesets())}", ""]
    for module in cert.modules:
        out += _module_lines(module, select)
    for relpath, reason in cert.failures.items():
        out.append(f"{badge('none')} {relpath}: cannot be analysed "
                   f"({reason})")
    out += [""] + summary(cert)
    return "\n".join(out) + "\n"


def _module_lines(module, select):
    """Lines of a source file and of its elements worth showing."""
    out = [f"{badge(module.level)} {module.qualname} "
           f"(score {module.score}, stamp {module.stamp})"]
    out += [f"        - {describe(v)}" for v in module.violations]
    for entity in module.walk():
        if entity.kind != "module" and select(entity):
            out += _entity_lines(entity)
    return out


def _entity_lines(entity):
    """Lines of an element with its violations."""
    head = (f"    {badge(entity.level)} {entity.kind} {entity.qualname} "
            f"l.{entity.start_line} score {entity.score} {entity.stamp}")
    return [head] + [f"        - {describe(v)}" for v in entity.violations]


def summary(cert):
    """Summary by kind and level, with the project level."""
    out = ["Summary:"]
    for kind, level, count in summary_rows(cert):
        out.append(f"  {KIND_LABELS[kind]:<22} "
                   f"{cert.scorer.label(level):<14} {count}")
    out.append(f"Project level: {cert.scorer.label(cert.level)}")
    return out
