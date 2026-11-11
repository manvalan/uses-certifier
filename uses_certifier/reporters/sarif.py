"""Uscita SARIF 2.1.0 per GitHub code scanning e gli IDE."""
import json

from .. import __version__

LEVELS = {"error": "error", "warning": "warning", "info": "note"}
SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"


def render(cert, select=None):
    """Documento SARIF con una voce per violazione non soppressa.

    Il filtro select è accettato per uniformità ed è ignorato.
    """
    run = {
        "tool": {"driver": {
            "name": "uses-certifier", "version": __version__,
            "rules": [_rule(r) for r in cert.rulebook.rules],
        }},
        "results": [_result(module, v) for module in cert.modules
                    for entity in module.walk() for v in entity.violations
                    if not v.suppressed],
    }
    doc = {"$schema": SCHEMA, "version": "2.1.0", "runs": [run]}
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def _rule(rule):
    """Descrizione SARIF di una regola."""
    return {"id": rule.id, "name": rule.name,
            "shortDescription": {"text": rule.title},
            "fullDescription": {"text": rule.rationale or rule.title},
            "properties": {"source": rule.source}}


def _result(module, violation):
    """Voce SARIF di una violazione."""
    location = {"physicalLocation": {
        "artifactLocation": {"uri": module.qualname},
        "region": {"startLine": violation.line},
    }}
    message = (f"{violation.title}: misurato {violation.value}, soglia "
               f"{violation.operator} {violation.threshold}")
    return {"ruleId": violation.rule_id,
            "level": LEVELS[violation.severity],
            "message": {"text": message}, "locations": [location]}
