"""Rapporto leggibile nel terminale."""
from .common import KIND_LABELS, badge, describe, summary_rows, \
    with_violations


def render(cert, select=with_violations):
    """Testo del rapporto per il terminale."""
    out = [f"Certificazione di {cert.root}",
           f"Regole: {', '.join(cert.rulebook.rulesets())}", ""]
    for module in cert.modules:
        out += _module_lines(module, select)
    for relpath, reason in cert.failures.items():
        out.append(f"{badge('none')} {relpath}: non analizzabile ({reason})")
    out += [""] + _summary(cert)
    return "\n".join(out) + "\n"


def _module_lines(module, select):
    """Righe di un sorgente e dei suoi elementi da segnalare."""
    out = [f"{badge(module.level)} {module.qualname} "
           f"(punteggio {module.score})"]
    for entity in module.walk():
        if select(entity):
            out += _entity_lines(entity)
    return out


def _entity_lines(entity):
    """Righe di un elemento con le sue violazioni."""
    head = (f"    {badge(entity.level)} {entity.kind} {entity.qualname} "
            f"r.{entity.start_line} punteggio {entity.score}")
    return [head] + [f"        - {describe(v)}" for v in entity.violations]


def _summary(cert):
    """Riepilogo per tipo e livello, con il livello del progetto."""
    out = ["Riepilogo:"]
    for kind, level, count in summary_rows(cert):
        out.append(f"  {KIND_LABELS[kind]:<20} "
                   f"{cert.scorer.label(level):<16} {count}")
    out.append(f"Livello del progetto: {cert.scorer.label(cert.level)}")
    return out
