"""SARIF 2.1.0 output for GitHub code scanning and IDEs."""
import json

from .. import __version__

LEVELS = {"error": "error", "warning": "warning", "info": "note"}
SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"


def render(cert, select=None):
    """SARIF document with one result per unsuppressed violation.

    The select filter is accepted for uniformity and ignored.
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
    """SARIF description of a rule."""
    return {"id": rule.id, "name": rule.name,
            "shortDescription": {"text": rule.title},
            "fullDescription": {"text": rule.rationale or rule.title},
            "properties": {"source": rule.source}}


def _result(module, violation):
    """SARIF result of a violation."""
    location = {"physicalLocation": {
        "artifactLocation": {"uri": module.qualname},
        "region": {"startLine": violation.line},
    }}
    message = (f"{violation.title}: measured {violation.value}, threshold "
               f"{violation.operator} {violation.threshold}")
    return {"ruleId": violation.rule_id,
            "level": LEVELS[violation.severity],
            "message": {"text": message}, "locations": [location]}
