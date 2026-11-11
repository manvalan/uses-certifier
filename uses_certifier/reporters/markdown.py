"""Rapporto Markdown, adatto a commenti di pull request e wiki."""
from .common import KIND_LABELS, badge, describe, summary_rows, \
    with_violations


def render(cert, select=with_violations):
    """Testo Markdown del rapporto."""
    out = _header(cert) + ["", "## Sorgenti", ""]
    for module in cert.modules:
        out += _module_section(module, select)
    return "\n".join(out) + "\n"


def _header(cert):
    """Titolo, livello del progetto e tabella riassuntiva."""
    out = ["# Certificazione del codice", "",
           f"**Livello del progetto: {cert.scorer.label(cert.level)}**", "",
           f"Regole: {', '.join(cert.rulebook.rulesets())} "
           f"(impronta `{cert.rulebook.digest[:12]}`)", "",
           "| Elementi | Livello | Quanti |", "|---|---|---|"]
    for kind, level, count in summary_rows(cert):
        out.append(f"| {KIND_LABELS[kind]} | "
                   f"{cert.scorer.label(level)} | {count} |")
    return out


def _module_section(module, select):
    """Sezione di un sorgente con gli elementi da segnalare."""
    out = [f"### {badge(module.level)} `{module.qualname}`", ""]
    shown = [e for e in module.walk() if select(e)]
    for entity in shown:
        out.append(f"- {badge(entity.level)} {entity.kind} "
                   f"`{entity.qualname}` (riga {entity.start_line}, "
                   f"punteggio {entity.score})")
        out += [f"  - {describe(v)}" for v in entity.violations]
    return out + ([""] if shown else ["Nessuna violazione.", ""])
