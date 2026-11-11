<!-- uses-certifier:start -->
## Code certification (uses-certifier)

Every method, class and source file in this project is certified with
[uses-certifier](https://github.com/manvalan/uses-certifier) against the
rules in [uses-rules](https://github.com/manvalan/uses-rules). The
certificate `uses-certificate.json` sits next to the sources and must
always match the code. The build fails when it does not.

Required level: **{min_level}**.

### Setup

- Install: `pip install git+https://github.com/manvalan/uses-certifier`
- Rules: set `USES_RULES_PATH` to a clone of
  `https://github.com/manvalan/uses-rules`, or clone it next to this
  project and pass `--rules ../uses-rules`.

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

### Never

- Edit `uses-certificate.json` or `uses-cert: stamp` comments by hand.
- Lower thresholds, disable rules or remove files from certification in
  `.uses-certifier.yaml` to make the check pass.
- Add `uses-cert: ignore[...]` without a concrete reason on the same
  line. Every suppression you add must be listed in your final report.
- Commit or hand over code for which `uses-certifier check` fails.

### Report

When you finish, state the project level, every element below Gold that
you touched, and every suppression you added, with its reason.
<!-- uses-certifier:end -->
