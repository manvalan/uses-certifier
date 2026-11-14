# uses-certifier

Certifier for the software we produce. It analyses the sources, applies the
YAML rules of [uses-rules](https://github.com/manvalan/uses-rules) and
**stamps every method, every class and every source file** with a level
(Gold, Silver, Bronze or Not certified), a score and a unique code that is
valid only for that exact element.

The rules come from *Code That Fits in Your Head* (Mark Seemann): rule of
seven, 80/24 rule, activated objects, nesting. On top of those come the
rules of *Clean Code* and PEP 8 / PEP 257.

> **AI agents:** to put a project under certification, follow
> [AGENT_SETUP.md](AGENT_SETUP.md). In short:
> `pip install git+https://github.com/manvalan/uses-certifier`, then
> `uses-certifier setup .` and `uses-certifier guide .` in the project root.

## Installation

```bash
pip install git+https://github.com/manvalan/uses-certifier
uses-certifier fetch-rules      # caches manvalan/uses-rules locally
```

The rules are looked up in this order: `--rules`, `USES_RULES_PATH`,
`rules_path` in `.uses-certifier.yaml`, then the cache filled by
`fetch-rules` (`~/.cache/uses-certifier/uses-rules`, or
`USES_RULES_CACHE`).

Requires Python 3.10 or later.

## Usage

```bash
# Certify a folder and show the elements with violations
uses-certifier certify src/

# Write the stamps into the sources
uses-certifier stamp src/

# Check that every stamp still matches its code
uses-certifier verify src/

# Write the JSON certificate and fail when the project is below Silver
uses-certifier certify . --certificate --min-level silver

# Build check: do the sources still match the committed certificate?
uses-certifier check

# Let the files that fail the check build anyway (people only)
uses-certifier authorize --reason "legacy, migration planned" --by Ann

# Path of the CMake module that runs the check on every build
uses-certifier cmake-module

# Add configuration and agent instructions to a project
uses-certifier init . --min-level silver

# All at once: fetch the rules, init, certify and print the next steps
uses-certifier setup . --min-level silver

# Explain certification and every rule in force (Markdown)
uses-certifier guide .

# Markdown report (pull requests) or SARIF (GitHub code scanning)
uses-certifier certify src/ --format markdown --output report.md
uses-certifier certify src/ --format sarif --output report.sarif

# List the rules active for the project
uses-certifier rules .
```

Every command that needs the rules accepts `--rules PATH`.

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

`--certificate` writes `certification/uses-certificate.json`: all the
certification files live in the `certification/` folder of the project,
committed with the sources, never scattered among them (the location can
be changed with `certificate:` in `.uses-certifier.yaml`, or by giving
`--certificate` a path). For every file, class and method it records metrics,
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
When a source carries stamps, every stamp must also match the code
recorded in the JSON certificate: a stamp edited by hand, removed or left
over from deleted code fails the build. See [docs/build-integration.md](docs/build-integration.md) for
CMake (C and C++), Make, npm, Gradle, Maven, Python, pre-commit and
GitHub Actions.

## Authorizations

Code that fails the check does not build by default. A person can let
it build, file by file, in `certification/authorizations.yaml` (the
`authorizations` key of `.uses-certifier.yaml` moves it):

```yaml
authorizations:
  - path: src/legacy/*.cpp        # fnmatch pattern, relative to the root
    reason: legacy parser, rewrite planned for Q1
    authorized_by: Ann
    expires: 2027-03-31           # optional
```

Every entry needs a reason and an author. `uses-certifier authorize
--reason ... --by ... [--expires YYYY-MM-DD]` appends one entry for each
file that currently fails the check, so new files stay blocked. On every
build `check` prints each authorized problem as `AUTHORIZED`, reports
expired entries (which stop working) and entries no longer needed. The
certificate tampering and migration coverage checks cannot be
authorized. Agents never add or extend authorizations: the file is
reviewed like code.

## Migrating existing programs

Programs written before certification can adopt it gradually:

```bash
uses-certifier init . --min-level gold --migration
```

writes `mode: migration` in `.uses-certifier.yaml`. In this mode:

- a source file certified at `min_level` is *migrated*, and from then on
  `check` verifies it as strictly as in a normal project;
- the other files are *legacy*: they are recorded in the certificate,
  `stamp` leaves them untouched and `check` reports them as `LEGACY`.
  They build only while they are authorized (see "Authorizations";
  `uses-certifier authorize` lists all of them at once when the
  migration starts). New files are never legacy: they must be certified;
- `certify` refuses to write the certificate when a migrated file falls
  back below `min_level`, so the migration only moves forward;
- `check` and `certify` print the coverage (migrated files out of all
  sources); `migration_min_coverage` makes the build fail below a
  percentage, and is raised as the migration proceeds.

When every file is migrated, switch to `mode: strict`.

## Design principles

Besides the measured rules, uses-rules holds 27 design principles in
`principles/`, from The Pragmatic Programmer, Clean Code, Clean
Architecture, Refactoring, Working Effectively with Legacy Code and Code
That Fits in Your Head (DRY, orthogonality, broken windows, command query
separation, two hats, seams, characterization tests and more). Most of
them cannot be measured; `uses-certifier guide` presents them by category
with how to apply them, a check question and examples, and the agent
instructions require agents to apply them and report where they did not.
Where part of a principle is measurable it has a rule: duplicated
function bodies (CC-011, DRY) and commented-out code (CC-012, broken
windows).

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
- **Duplicated code**: functions of 6 lines or more whose bodies are
  identical anywhere in the certified tree. Python bodies are compared on
  the syntax tree (formatting and comments ignored, names included);
  other languages on their trimmed, non-blank lines.
- **Commented-out code** (Python): full-line comments whose content
  parses as an assignment, call, import, return or control statement.

## The certifier certifies itself

CI runs the certifier on its own code and requires the Gold level, and
checks the committed `certification/uses-certificate.json` like any adopting project.

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
| `init.py`, `guide.py`, `rules_cache.py`, `templates/` | project setup, agent guide, rules download |
| `reporters/` | console, Markdown and SARIF output |
