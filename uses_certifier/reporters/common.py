"""Funzioni condivise dai formati di uscita."""

BADGES = {"gold": "[ORO]", "silver": "[ARG]", "bronze": "[BRO]",
          "none": "[NO ]"}
KIND_LABELS = {"module": "sorgenti", "class": "classi",
               "function": "metodi e funzioni"}


def badge(level):
    """Bollino testuale breve del livello."""
    return BADGES.get(level, f"[{level[:3].upper()}]")


def describe(violation):
    """Descrizione di una violazione in una riga."""
    text = (f"{violation.rule_id} {violation.title} "
            f"(misurato {violation.value}, soglia {violation.operator} "
            f"{violation.threshold})")
    return text + (" [soppressa]" if violation.suppressed else "")


def with_violations(entity):
    """Filtro predefinito: solo gli elementi con violazioni."""
    return bool(entity.violations)


def everything(entity):
    """Filtro completo: tutti gli elementi."""
    return entity is not None


def summary_rows(cert):
    """Righe (tipo, livello, conteggio) ordinate per tipo e livello."""
    counts = {}
    for entity in cert.entities():
        key = (entity.kind, entity.level)
        counts[key] = counts.get(key, 0) + 1
    order = list(KIND_LABELS)
    return sorted(((k, lvl, n) for (k, lvl), n in counts.items()),
                  key=lambda row: (order.index(row[0]),
                                   cert.scorer.order(row[1])))
