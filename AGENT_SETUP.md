# Adopting uses-certifier: instructions for AI agents

You were given the link to this repository to put a project under code
certification. Follow these steps in the root of that project. Ask the
user only for the required level if they did not give one; otherwise use
`silver`.

## 1. Install

```bash
pip install git+https://github.com/manvalan/uses-certifier
```

Requires Python 3.10+ and git. If `pip` installs into a user folder, make
sure `uses-certifier` is on `PATH` (or use `python -m uses_certifier`).

## 2. Set up the project

```bash
uses-certifier setup . --min-level silver
```

This downloads the rules from
[uses-rules](https://github.com/manvalan/uses-rules) into a local cache,
creates `.uses-certifier.yaml`, adds a certification section to
`AGENTS.md`, creates or updates `CLAUDE.md`, and certifies the project
once to show where it stands.

For a program written before certification, add `--migration`: the
build then accepts the files not yet certified and the project is
migrated file by file (see "Migrating existing programs" in the README).
In that case step 4 applies to the files you create or change, not to
the whole project.

## 3. Learn the rules and how certification works

```bash
uses-certifier guide .
```

Read the whole output. It explains scoring, levels, stamp codes and the
certificate, lists every rule in force with its limit and its reason,
presents the design principles (which the certifier cannot measure, but
you must apply and report on), and repeats the workflow you must follow
from now on. The same workflow is in
the project's `AGENTS.md`.

## 4. Reach the required level

```bash
uses-certifier certify . --verbose
```

Refactor the code until the project reaches the required level: extract
methods, introduce parameter objects, flatten nesting with guard clauses,
split large classes. Let the design principles guide each refactoring. Keep behaviour unchanged and run the project's tests
after each step.

If the project is large, fix one file at a time and tell the user how far
you got. Do not lower thresholds or disable rules in
`.uses-certifier.yaml`; exclude only generated or third-party code (and say
so). Use `uses-cert: ignore[ID] reason` only for a concrete, explained
case, and list every one in your report.

## 5. Issue the certificate

```bash
uses-certifier certify . --certificate --min-level silver
uses-certifier check
```

Optionally write the stamps into the sources with `uses-certifier stamp .`.
If the user has a signing key, it is provided through `USES_CERT_KEY`;
never write the key into the repository.

## 6. Add the build check

Make `uses-certifier check` the first step of the project's build, using
the snippet for its build system from
[docs/build-integration.md](docs/build-integration.md) (Make, CMake, npm,
Gradle, Maven, Python, pre-commit, GitHub Actions).

## 7. Commit and report

Commit `.uses-certifier.yaml`, `AGENTS.md`, `CLAUDE.md`,
`certification/`, the build change and the refactors. Then report:
the project level, what you changed to get there, every element still
below Gold, every exclusion and suppression with its reason, the design
principles the code still does not follow, and how the build now runs
the check.
