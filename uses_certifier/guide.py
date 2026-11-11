"""Guide for agents and people: how certification works and which rules
apply, generated from the rules actually in force."""
from .init import START, END, template

SCOPES = {"function": "method", "class": "class", "module": "file"}

INTRO = """# uses-certifier guide

uses-certifier gives every method, class and source file a level and a
stamp code. Each element starts at 100 points and loses points for every
rule it breaks. It then receives the first level it satisfies. A class is
worth the worst of itself and its methods, a file the worst of what it
contains, the project its worst file.

Each stamp code is bound to the file path, the element, the SHA-256 of its
code, the rules in force and its level: it is valid for that element only.
The certificate `certification/uses-certificate.json` lists the code of
every element and `uses-certifier check` fails the build when the code
no longer matches it.
"""


def render(rulebook, min_level):
    """Markdown guide for the given rules and required level."""
    parts = [INTRO, _levels(rulebook.certification), _rules(rulebook),
             _principles(rulebook.principles), _workflow(min_level)]
    return "\n".join(parts)


def _levels(certification):
    """Scoring and level table."""
    penalties = certification.get("scoring", {}).get("penalties", {})
    cost = ", ".join(f"{sev} -{pts}" for sev, pts in penalties.items())
    out = ["## Levels", "", f"Points lost per violation: {cost}.", "",
           "| Level | Minimum score | Max errors | Max warnings |",
           "|---|---|---|---|"]
    for level in certification.get("levels", []):
        out.append(f"| {level.get('label', level['id'])} "
                   f"| {level.get('min_score', 0)} "
                   f"| {level.get('max_errors', 'any')} "
                   f"| {level.get('max_warnings', 'any')} |")
    return "\n".join(out + [""])


def _rules(rulebook):
    """Table of the active rules with their reasons."""
    out = ["## Rules in force", "",
           f"Rulesets: {', '.join(rulebook.rulesets())}.", "",
           "| Id | Applies to | Rule | Limit | Severity | Why |",
           "|---|---|---|---|---|---|"]
    for rule in rulebook.rules:
        langs = f" ({', '.join(rule.languages)})" if rule.languages else ""
        why = " ".join((rule.rationale or "").split())
        out.append(f"| {rule.id} | {SCOPES[rule.scope]}{langs} "
                   f"| {rule.title} | {rule.metric} {rule.operator} "
                   f"{rule.threshold} | {rule.severity} | {why} |")
    return "\n".join(out + [""])


PRINCIPLES_INTRO = """## Design principles

These are not measured by the certifier. Apply them whenever you write or
change code, answer each check question for the code you touched, and
report every case where you did not follow one, with the reason.
"""


def _principles(principles):
    """Every design principle with how to apply and check it."""
    if not principles:
        return ""
    out, category = [PRINCIPLES_INTRO], None
    for item in principles:
        if item.get("category_title") and item["category_title"] != category:
            category = item["category_title"]
            out += [f"### {category}", ""]
        out += _principle(item)
    return "\n".join(out)


def _principle(item):
    """Markdown block of one design principle."""
    summary = " ".join(item["summary"].split())
    out = [f"#### {item['id']} {item['title']}", "", summary, ""]
    out += [f"- {' '.join(step.split())}" for step in item.get("apply", [])]
    out += ["", f"**Check:** {item['check']}"]
    if item.get("measured_by"):
        out += ["", f"Partly measured by: {', '.join(item['measured_by'])}"]
    example = item.get("example")
    if example:
        out += ["", f"- Avoid: `{example['avoid']}`",
                f"- Prefer: `{example['prefer']}`"]
    source = f"Source: {item['source']}" if item.get("source") else ""
    return out + ["", source, ""] if source else out + [""]


def _workflow(min_level):
    """The agent instructions, without their section markers."""
    text = template("agents-section.md", min_level)
    return text.replace(START, "").replace(END, "").strip() + "\n"
