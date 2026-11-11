<!-- uses-certifier:start -->
## Code certification (uses-certifier)

Every method, class and source file in this project is certified with
[uses-certifier](https://github.com/manvalan/uses-certifier) against the
rules in [uses-rules](https://github.com/manvalan/uses-rules). The
certificate `uses-certificate.json` sits next to the sources and must
always match the code. The build fails when it does not.

Required level: **{min_level}**. These instructions apply whenever you
write or change code in this project, and whenever you are asked for
certified code.

The certificate has two parts: the JSON file with the code of every
method, class and file, and (when the project keeps them) the
`uses-cert: stamp` comments in the sources. `uses-certifier check`, the
first build step, verifies that both match the current code.

### Setup

- Install: `pip install git+https://github.com/manvalan/uses-certifier`
- Download the rules: `uses-certifier fetch-rules` (they are cached and
  used automatically; `USES_RULES_PATH` or `--rules` override them).
- Read the rules and how certification works: `uses-certifier guide .`

### Write code that passes the rules

- Methods: at most 24 lines, cyclomatic complexity at most 7, at most
  4 parameters, nesting at most 3, at most 7 activated objects
  (parameters, locals and fields used).
- Lines at most 80 characters. No bare `except:`. No boolean flag
  parameters. Docstrings on public functions and classes.
- Classes: at most 12 methods, at most 7 fields, at most 300 lines.
- Prefer extracting small, well-named methods and parameter objects over
  long or deeply nested code.
- List every active rule with `uses-certifier rules .`.

### Follow the design principles

Besides the measured rules, apply the design principles listed by
`uses-certifier guide .` (DP-001 and following), drawn from The Pragmatic
Programmer, Clean Code, Clean Architecture, Refactoring, Working
Effectively with Legacy Code and Code That Fits in Your Head. In short:

- Design: DRY, orthogonal components, no broken windows, tracer bullets,
  functional core and imperative shell, command query separation, parse
  don't validate, objects that protect their invariants.
- Writing: intention-revealing names, small functions at one level of
  abstraction, code as documentation (comments say why), the Boy Scout
  rule, tell don't ask, explicit errors.
- Architecture: single responsibility, dependencies pointing inward,
  explicit dependencies, composition over inheritance.
- Improvement: the two hats (never refactor and change behaviour in the
  same step), small verifiable steps, recognise code smells, rule of three.
- Safety: tests before changing existing code, seams to isolate
  dependencies, characterization tests for legacy code, tests first.

Most of them cannot be measured: answer each check question for the code
you touched.

### After every change

1. Run `uses-certifier certify . --verbose` and fix every violation in
   the code you touched until the project reaches **{min_level}**.
2. Regenerate the certificate:
   `uses-certifier certify . --certificate uses-certificate.json --min-level {min_level}`
3. If the project keeps stamps in the sources, refresh them:
   `uses-certifier stamp .`
4. Run `uses-certifier check`. It must print `Certification check OK`.
5. Commit `uses-certificate.json` (and the stamps) in the same commit as
   the code they certify.

### Existing programs being migrated

When `.uses-certifier.yaml` says `mode: migration`, the program is
being certified file by file. The build accepts *legacy* files (not yet
at **{min_level}**) and checks strictly the *migrated* ones.

- Every new file you create must reach **{min_level}**.
- Every file you change should leave your hands at **{min_level}** (the
  Boy Scout rule). Write characterization tests before refactoring legacy
  code. When that is not practical, say so in your report.
- A migrated file must never fall below **{min_level}**: `certify`
  refuses to write the certificate when one does.
- Never lower `migration_min_coverage`. When every file is migrated,
  propose switching to `mode: strict`.

### Never

- Edit `uses-certificate.json` or `uses-cert: stamp` comments by hand.
- Lower thresholds, disable rules or remove files from certification in
  `.uses-certifier.yaml` to make the check pass.
- Add `uses-cert: ignore[...]` without a concrete reason on the same
  line. Every suppression you add must be listed in your final report.
- Commit or hand over code for which `uses-certifier check` fails.

### Report

When you finish, state the project level (and, in migration mode, the
coverage printed by `uses-certifier check`), every element below
{min_level} that you touched, every suppression you added with its reason, and every
design principle you did not follow in the code you touched, with the
reason.
<!-- uses-certifier:end -->
