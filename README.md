# uses-certifier

Certifier for all the software we produce. It reads the sources, applies
the YAML rules of [uses-rules](https://github.com/manvalan/uses-rules) and
**stamps every method, every class and every source file** with a level
(Gold, Silver, Bronze or Not certified), a score and a code that is valid
only for that exact element. The build then refuses code that does not
match its certificate.

The rules come from *Code That Fits in Your Head* (Mark Seemann): rule of
seven, 80/24 rule, activated objects, nesting. On top of those come the
rules of *Clean Code*, PEP 8 / PEP 257, and 27 design principles from
The Pragmatic Programmer, Clean Architecture, Refactoring and Working
Effectively with Legacy Code.

> **AI agents:** to put a project under certification, follow
> [AGENT_SETUP.md](AGENT_SETUP.md). In short:
> `pip install git+https://github.com/manvalan/uses-certifier`, then
> `uses-certifier setup .` and `uses-certifier guide .` in the project root.

## Contents

- [How it works](#how-it-works)
- [Quick start](#quick-start)
- [Commands](#commands)
- [How elements are scored](#how-elements-are-scored)
- [The stamp](#the-stamp) and [the JSON certificate](#the-json-certificate)
- [Build check](#build-check), [CMake](#cmake-c-and-c) and
  [authorizations](#authorizations)
- [Migrating existing programs](#migrating-existing-programs)
- [Design principles](#design-principles) and
  [instructions for agents](#instructions-for-agents)
- [Justified exceptions](#justified-exceptions),
  [configuration](#project-configuration),
  [GitHub Actions](#in-github-actions)
- [Supported languages and approximations](#approximations)
- [Development](#development)

## How it works

Certification has three actors, each with one job:

```text
 uses-rules (YAML)       uses-certifier certify     build
 rules, principles  -->  stamps + certificate  -->  uses-certifier check
        |                (committed with code)      (first build step)
        v
 developer or agent
 writes code that passes the rules
```

1. **Who writes the code** (a developer or an AI agent) follows the rules.
   `uses-certifier init` writes the instructions for agents into
   `AGENTS.md`, so asking an agent for certified code is enough.
2. **The certifier** (`uses-certifier certify`) measures every element,
   awards a level and issues the certificate: an inline stamp above each
   method and class, and `certification/uses-certificate.json` with the
   fingerprint and code of every method, class and file.
3. **The build** (`uses-certifier check`, or `uses_certifier_check()` in
   CMake) verifies that sources, stamps and certificate still match.
   Code that changed after certification, or was never certified, does
   not build, unless a person authorizes it explicitly in
   `certification/authorizations.yaml`.

## Quick start

Requires Python 3.10 or later and git.

```bash
pip install git+https://github.com/manvalan/uses-certifier
uses-certifier fetch-rules      # caches manvalan/uses-rules locally
```

The rules are looked up in this order: `--rules`, `USES_RULES_PATH`,
`rules_path` in `.uses-certifier.yaml`, then the cache filled by
`fetch-rules` (`~/.cache/uses-certifier/uses-rules`, or
`USES_RULES_CACHE`).

**A new project.** From the project root:

```bash
uses-certifier setup . --min-level gold   # config, AGENTS.md, first run
uses-certifier certify . --verbose        # what to fix, element by element
uses-certifier certify . --certificate --min-level gold
uses-certifier stamp .                    # optional inline stamps
uses-certifier check                      # what the build will run
git add certification/ .uses-certifier.yaml AGENTS.md CLAUDE.md
```

**An existing program.** Certify it file by file:

```bash
uses-certifier setup . --min-level gold --migration
uses-certifier certify . --certificate --min-level gold
uses-certifier authorize --reason "legacy, migration planned" --by Ann
```

The last command, run by a person, lets the files that are not yet
certified build while they are migrated. See
[Migrating existing programs](#migrating-existing-programs).

**A C or C++ project with CMake.** Add after `project()`:

```cmake
execute_process(COMMAND uses-certifier cmake-module
                OUTPUT_VARIABLE USES_CERTIFIER_MODULE
                OUTPUT_STRIP_TRAILING_WHITESPACE
                COMMAND_ERROR_IS_FATAL ANY)
include(${USES_CERTIFIER_MODULE})
uses_certifier_check()
```

From then on every executable and library depends on the certification
check. See [CMake](#cmake-c-and-c).

## Commands

| Command | What it does |
|---|---|
| `certify PATH` | Measures and scores every element and prints the violations (`--verbose`, `--format markdown\|sarif`, `--output`) |
| `certify . --certificate --min-level L` | Also writes `certification/uses-certificate.json`; fails below level `L` |
| `stamp PATH` | Writes or refreshes the inline stamps |
| `verify PATH` | Checks that every inline stamp matches its code |
| `check` | Build check: sources and stamps against the committed certificate; needs no rules |
| `authorize --reason R --by NAME [--expires DATE]` | Lets the files that fail `check` build (people only) |
| `cmake-module` | Prints the path of the CMake module |
| `init PATH [--min-level L] [--migration]` | Adds `.uses-certifier.yaml`, `AGENTS.md` and `CLAUDE.md` |
| `setup PATH` | `fetch-rules`, `init` and a first `certify` in one go |
| `fetch-rules [--ref REF]` | Downloads uses-rules into the local cache |
| `guide PATH` | Explains certification, every rule and every principle in force (Markdown) |
| `rules PATH` | Lists the active rules |

Every command that needs the rules accepts `--rules PATH`; commands that
issue or check codes accept `--key-file` (see
[signed codes](#a-code-valid-only-for-that-element)). Examples:

```bash
uses-certifier certify src/
uses-certifier certify src/ --format markdown --output report.md
uses-certifier certify src/ --format sarif --output report.sarif
uses-certifier verify src/
uses-certifier guide . > CERTIFICATION.md
```

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
over from deleted code fails the build. Each problem is printed on its
own line (`INVALID`, `UNCERTIFIED`, `MISSING`, `BELOW_LEVEL`, `LEGACY`,
`AUTHORIZED`) and the command ends with `Certification check OK` or
`Certification check FAILED`. Run it as the first build step; see
[docs/build-integration.md](docs/build-integration.md) for CMake, Make,
npm, Gradle, Maven, Python, pre-commit and GitHub Actions.

### CMake (C and C++)

The package ships a CMake module (CMake 3.19 or later).
`uses-certifier cmake-module` prints its path; include it and call
`uses_certifier_check()` as shown in the [quick start](#quick-start).
The function adds the `uses_certification` target, which runs
`uses-certifier check` on every build, and makes every executable and
library of the project (in all subdirectories, including targets defined
after the call) depend on it. When the check fails nothing compiles.
Configuration fails when `uses-certifier` is not installed, and there is
no option to turn the check off. Optional arguments (`TARGET`,
`PROJECT_DIR`, `CERTIFICATE`, `AUTHORIZATIONS`, `MIN_LEVEL`, `GUARD`) and
vendoring are described in
[docs/build-integration.md](docs/build-integration.md#cmake-c-and-c).

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

Tests and the certifier's own certificate must pass before a merge:

```bash
pip install -e ".[test]"
pytest
uses-certifier certify . --certificate --min-level gold
uses-certifier check
```

Changes follow [AGENTS.md](AGENTS.md), which applies to people as well.
[docs/bugs-found-adopting-boardlab.md](docs/bugs-found-adopting-boardlab.md)
records the problems found adopting the certifier on a real project.

| Module | Purpose |
|---|---|
| `analyzers/` | elements and metrics (Python through the AST, other languages through lizard) |
| `rules.py`, `config.py` | loading of YAML rules and project configuration |
| `evaluator.py` | comparison of metrics and thresholds |
| `scoring.py`, `signing.py` | score, level and stamp code |
| `markers.py`, `suppressions.py`, `stamper.py` | stamp and ignore comments in the sources |
| `certificate.py`, `check.py`, `verify.py` | JSON certificate, build check, stamp verification |
| `authorization.py`, `migration.py` | authorizations and file-by-file migration |
| `cmake/` | CMake module (`UsesCertifier.cmake`) |
| `init.py`, `guide.py`, `rules_cache.py`, `templates/` | project setup, agent guide, rules download |
| `reporters/` | console, Markdown and SARIF output |
