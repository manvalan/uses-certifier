"""Applicazione delle regole agli elementi analizzati."""
import operator

from . import suppressions
from .model import Violation

OPERATORS = {
    "<=": operator.le, "<": operator.lt, ">=": operator.ge,
    ">": operator.gt, "==": operator.eq, "!=": operator.ne,
}


def evaluate(module, rules):
    """Calcola le violazioni di ogni elemento del sorgente."""
    file_wide = module.suppressions
    for entity in module.walk():
        suppressed = entity.suppressions | file_wide
        entity.violations = [
            _violation(rule, entity, suppressed)
            for rule in rules if _applies(rule, entity)
            and not _passes(rule, entity.metrics[rule.metric])
        ]


def _applies(rule, entity):
    """Vero se la regola riguarda questo elemento."""
    if rule.scope != entity.kind or rule.metric not in entity.metrics:
        return False
    if rule.languages and entity.language not in rule.languages:
        return False
    return rule.applies_to != "public" or entity.is_public


def _passes(rule, value):
    """Vero se il valore misurato rispetta la soglia."""
    return OPERATORS[rule.operator](value, rule.threshold)


def _violation(rule, entity, suppressed):
    """Violazione della regola da parte dell'elemento."""
    return Violation(
        rule_id=rule.id, severity=rule.severity, title=rule.title,
        metric=rule.metric, value=entity.metrics[rule.metric],
        threshold=rule.threshold, operator=rule.operator,
        line=entity.start_line,
        suppressed=suppressions.is_suppressed(rule.id, suppressed),
    )
