"""Markdown report, for pull request comments and wikis."""
from .common import KIND_LABELS, badge, describe, summary_rows, \
    with_violations


def render(cert, select=with_violations):
    """Markdown text of the report."""
    out = _header(cert) + ["", "## Source files", ""]
    for module in cert.modules:
        out += _module_section(module, select)
    return "\n".join(out) + "\n"


def _header(cert):
    """Title, project level and summary table."""
    out = ["# Code certification", "",
           f"**Project level: {cert.scorer.label(cert.level)}**", "",
           f"Rules: {', '.join(cert.rulebook.rulesets())} "
           f"(fingerprint `{cert.rulebook.digest[:12]}`)", "",
           "| Elements | Level | Count |", "|---|---|---|"]
    for kind, level, count in summary_rows(cert):
        out.append(f"| {KIND_LABELS[kind]} | "
                   f"{cert.scorer.label(level)} | {count} |")
    return out


def _module_section(module, select):
    """Section of a source file with the elements worth showing."""
    out = [f"### {badge(module.level).strip()} `{module.qualname}` "
           f"`{module.stamp}`", ""]
    shown = [e for e in module.walk() if select(e)]
    for entity in shown:
        out.append(f"- {badge(entity.level).strip()} {entity.kind} "
                   f"`{entity.qualname}` (line {entity.start_line}, "
                   f"score {entity.score}, `{entity.stamp}`)")
        out += [f"  - {describe(v)}" for v in entity.violations]
    return out + ([""] if shown else ["No violations.", ""])
