# uses-certifier

Certifier for the software we produce. It analyses the sources, applies the
YAML rules of [uses-rules](https://github.com/manvalan/uses-rules) and
**stamps every method, every class and every source file** with a level
(Gold, Silver, Bronze or Not certified), a score and a unique code that is
valid only for that exact element.

The rules come from *Code That Fits in Your Head* (Mark Seemann): rule of
seven, 80/24 rule, activated objects, nesting. On top of those come the
rules of *Clean Code* and PEP 8 / PEP 257.

## Installation

```bash
pip install git+https://github.com/manvalan/uses-certifier
git clone https://github.com/manvalan/uses-rules
```

Requires Python 3.10 or later.

## Usage

```bash
# Certify a folder and show the elements with violations
uses-certifier certify src/ --rules ../uses-rules

# Write the stamps into the sources
uses-certifier stamp src/ --rules ../uses-rules

# Check that every stamp still matches its code
uses-certifier verify src/ --rules ../uses-rules

# Write the JSON certificate and fail when the project is below Silver
uses-certifier certify . --rules ../uses-rules \
    --certificate uses-certificate.json --min-level silver

# Build check: do the sources still match the committed certificate?
uses-certifier check

# Add configuration and agent instructions to a project
uses-certifier init . --min-level silver

# Markdown report (pull requests) or SARIF (GitHub code scanning)
uses-certifier certify src/ --rules ../uses-rules --format markdown --output report.md
uses-certifier certify src/ --rules ../uses-rules --format sarif --output report.sarif

# List the rules active for the project
uses-certifier rules . --rules ../uses-rules
```

Instead of `--rules` you can set the `USES_RULES_PATH` variable.

## How elements are scored

1. **Analysis.** Python is read through its AST. Other languages (C, C++,
   C#, Java, JavaScript, TypeScript, Go, Rust, Kotlin, Swift, PHP, Ruby,
   Scala, Lua...) through [lizard](https://github.com/terryyin/lizard).
   Every element gets the metrics listed in the uses-rules README.
2. **Rules.** Each rule compares a metric with a threshold. Every
   violation costs 20 points (error), 7 (warning) or 2 (info), starting
   from 100.
3. **Level.** Each element receives the first level of
   `certification.yaml` it satisfies: Gold (≥ 95, no errors, no warnings),
   Silver (≥ 80, no errors), Bronze (≥ 60, no errors), otherwise Not
   certified. A class is worth the worst of itself and its methods, a
   source file the worst of what it contains, the project its worst file.

Example (illustrative codes):

```
[NONE]   orders.py (score 100, stamp 9E16-B88B-D922-31F6)
    [GOLD]   function total l.4 score 100 1660-9C18-FDBD-A0E2
    [NONE]   function discount l.9 score 67 51D7-626A-D417-789E
        - CTF-001 Cyclomatic complexity of at most 7 (measured 8, threshold <= 7)
        - CTF-006 At most 4 parameters (measured 5, threshold <= 4)
        - CC-001 Preferably at most 3 arguments (measured 5, threshold <= 3)
```

## The stamp

`uses-certifier stamp` writes a comment above every method and class, and
one at the top of every source file:

```python
# uses-cert: stamp-file GOLD 9E16-B88B-D922-31F6
"""Orders."""


# uses-cert: stamp GOLD 8B52-FCD3-6006-4E36
class Cart:
    """A cart."""

    # uses-cert: stamp GOLD 51D7-626A-D417-789E
    def total(self, a, b):
        """Total."""
        return a + b
```

The comment syntax follows the language (`#`, `//`, `--`...). Running
`stamp` again replaces the old stamps; stamp lines are removed before
analysis, so they never change a fingerprint or a metric.

### A code valid only for that element

Each code is computed from:

- the file path and the element's kind and qualified name,
- the SHA-256 fingerprint of the element's code,
- the fingerprint of the rules and levels in force,
- the level awarded.

So a code belongs to one element only. If the code changes, if the stamp is
copied onto another method, if the level is edited by hand or if the rules
change, `uses-certifier verify` reports the stamp as `INVALID`. Elements
without a stamp are reported as `MISSING`.

**Signed codes.** Without a key, codes are SHA-256 fingerprints: unique,
but anyone with the tool can recompute them. With a secret key in
`USES_CERT_KEY` (or `--key-file`) they become HMAC-SHA256 signatures that
cannot be forged without the key. Use a key, kept as a CI secret, when
stamps must prove that the official pipeline issued them.

### The JSON certificate

`--certificate` writes `uses-certificate.json`, meant to be committed next
to the sources. For every file, class and method it records metrics,
violations, score, level, SHA-256 fingerprint and stamp code. The
certificate itself has a `certificate_id` that binds every stamp, the
rules and the level: changing anything in the file breaks it.

The certificate is **reproducible**: the same method, class and file with
the same rules (and key) always get the same code, and the whole file is
byte-identical. It holds no date and no absolute path; `root` is the
sources folder relative to the certificate. Always certify from the same
folder (normally the project root), because the file path is part of
each code.

## Build check

`uses-certifier check` compares the sources with the certificate without
needing the rules. It fails when code changed after certification, when
new code is not certified, when certified code disappeared, when an
element is below the required level, or when the certificate was edited.
See [docs/build-integration.md](docs/build-integration.md) for Make,
CMake, npm, Gradle, Maven, Python, pre-commit and GitHub Actions.

## Instructions for agents

`uses-certifier init` adds to a project:

- `.uses-certifier.yaml` with the required level,
- a certification section in `AGENTS.md` (created, appended or
  refreshed between `uses-certifier:start` / `end` markers) that tells
  coding agents how to write code that passes the rules, how to issue
  the certificate and what they must never do,
- `CLAUDE.md` pointing Claude to `AGENTS.md`.

This repository uses them itself: see [AGENTS.md](AGENTS.md).

## Justified exceptions

When a rule makes no sense in a specific case, suppress it with a comment
above the definition (or above its decorators), always giving a reason:

```python
# uses-cert: ignore[CC-008] fields mirror the YAML format
@dataclass
class Rule:
    ...
```

`# uses-cert: ignore-file[CC-010]` applies to the whole source file.
Suppressed violations stay in the certificate with `"suppressed": true`,
so they remain visible in review.

## Project configuration

A `.uses-certifier.yaml` file in the project root picks the rulesets,
excludes paths, adjusts thresholds and sets the minimum level. See
[`.uses-certifier.example.yaml`](.uses-certifier.example.yaml).

## In GitHub Actions

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
  with: {python-version: "3.12"}
# Fast check of the committed certificate (no rules needed)
- uses: manvalan/uses-certifier@main
  with:
    mode: check
    key: ${{ secrets.USES_CERT_KEY }}
# Full certification with the current rules and a report in the job summary
- uses: manvalan/uses-certifier@main
  with:
    min-level: silver
    key: ${{ secrets.USES_CERT_KEY }}
```

In `certify` mode the action fetches uses-rules, certifies, writes the
report into the job summary and leaves the issued certificate in
`$RUNNER_TEMP/uses-certificate.json` (it never overwrites the committed
one). If uses-rules is private, pass a `token` with read access to it.

## Approximations

- With lizard, classes are rebuilt from method names (`Class::method`,
  `Class.method`) and get no inline stamp. Nesting, activated objects,
  docstrings, flag arguments and fields are computed for Python only.
- **Activated objects** (Python): parameters, local variables and `self`
  fields used by the method. Comprehension variables and calls to `self`
  methods do not count.
- **Nesting**: `if`, `for`, `while`, `with`, `try`, `match`; an `elif`
  stays at the level of its `if`.

## The certifier certifies itself

CI runs the certifier on its own code and requires the Gold level, and
checks the committed `uses-certificate.json` like any adopting project.

## Development

```bash
pip install -e ".[test]"
pytest
```

| Module | Purpose |
|---|---|
| `analyzers/` | elements and metrics (Python through the AST, other languages through lizard) |
| `rules.py`, `config.py` | loading of YAML rules and project configuration |
| `evaluator.py` | comparison of metrics and thresholds |
| `scoring.py`, `signing.py` | score, level and stamp code |
| `markers.py`, `suppressions.py`, `stamper.py` | stamp and ignore comments in the sources |
| `certificate.py`, `check.py`, `verify.py` | JSON certificate, build check, stamp verification |
| `init.py`, `templates/` | project setup and agent instructions |
| `reporters/` | console, Markdown and SARIF output |
