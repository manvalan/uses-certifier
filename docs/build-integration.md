# Build integration

`uses-certifier check` compares the sources with the committed
`certification/uses-certificate.json`. It needs no rules and no network, runs in well
under a second on typical projects, and exits with code 1 when:

- a method, class or file changed after it was certified (`INVALID`),
- new code is not in the certificate (`UNCERTIFIED`),
- certified code disappeared (`MISSING`),
- an element is below `--min-level` or the `min_level` of
  `.uses-certifier.yaml` (`BELOW_LEVEL`),
- a stamp written in a source does not match the JSON certificate, is
  missing from a stamped source or belongs to no element,
- the certificate was edited by hand,
- in migration mode, a file is not yet at `min_level` (`LEGACY`), or
  the share of migrated files is below `migration_min_coverage`.

Nothing passes by default. The only way to build code that fails the
check is an explicit authorization written by a person in
`certification/authorizations.yaml`, with a reason, an author and an
optional expiry (see "Authorizations" in the README and
`uses-certifier authorize`). Authorized problems are printed as
`AUTHORIZED` on every build. Certificate tampering and the migration
coverage cannot be authorized.

Add it as the first step of the build so that uncertified code never
compiles. Every example assumes `uses-certifier` is installed
(`pip install git+https://github.com/manvalan/uses-certifier`). For
signed certificates, provide the key through `USES_CERT_KEY`; without it
the check still compares fingerprints and says so.

## CMake (C and C++)

The package ships a CMake module (CMake 3.19 or later). Add these lines
to the top-level `CMakeLists.txt`, after `project()`:

```cmake
execute_process(COMMAND uses-certifier cmake-module
                OUTPUT_VARIABLE USES_CERTIFIER_MODULE
                OUTPUT_STRIP_TRAILING_WHITESPACE
                COMMAND_ERROR_IS_FATAL ANY)
include(${USES_CERTIFIER_MODULE})
uses_certifier_check()
```

`uses_certifier_check()` adds the `uses_certification` target, which runs
`uses-certifier check` on every build, and at the end of the
configuration makes every executable and library of the project (in all
subdirectories, including the targets defined after the call) depend on
it. When the check fails nothing compiles, whatever the generator. Configuration fails when `uses-certifier` is not
installed, so the check cannot be skipped by accident; there is no
option to turn it off.

Optional arguments:

| Argument | Default |
|---|---|
| `TARGET name` | `uses_certification` |
| `PROJECT_DIR dir` | `CMAKE_CURRENT_SOURCE_DIR` |
| `CERTIFICATE file` | the project's configured certificate |
| `AUTHORIZATIONS file` | the project's configured authorizations |
| `MIN_LEVEL level` | the project's `min_level` |
| `GUARD targets...` | every executable and library |

Instead of `execute_process`, the module can be vendored (copy
`uses_certifier/cmake/UsesCertifier.cmake`) or fetched with
`FetchContent`; `USES_CERTIFIER_EXECUTABLE` points it to a
`uses-certifier` outside the `PATH`. A failing build prints, for example:

```text
INVALID      src/parser.cpp:Parser::parse
UNCERTIFIED  src/new_feature.cpp
Certification check FAILED. Valid: 412, invalid: 1, ...
```

## Make

```make
.PHONY: certification
certification:
	uses-certifier check

build: certification
	$(CC) ...
```

## npm

```json
{
  "scripts": {
    "prebuild": "uses-certifier check",
    "build": "tsc"
  }
}
```

## Gradle (Kotlin DSL)

```kotlin
val certification by tasks.registering(Exec::class) {
    commandLine("uses-certifier", "check")
}
tasks.named("compileJava") { dependsOn(certification) }
```

## Maven

```xml
<plugin>
  <groupId>org.codehaus.mojo</groupId>
  <artifactId>exec-maven-plugin</artifactId>
  <executions>
    <execution>
      <id>certification</id>
      <phase>validate</phase>
      <goals><goal>exec</goal></goals>
      <configuration>
        <executable>uses-certifier</executable>
        <arguments><argument>check</argument></arguments>
      </configuration>
    </execution>
  </executions>
</plugin>
```

## Python packages

Run it before building the wheel, for example in `tox.ini` or `noxfile.py`:

```ini
[testenv]
commands_pre = uses-certifier check
```

## pre-commit

```yaml
repos:
  - repo: https://github.com/manvalan/uses-certifier
    rev: main
    hooks:
      - id: uses-certifier-check
```

## GitHub Actions

```yaml
- uses: manvalan/uses-certifier@main
  with:
    mode: check
    key: ${{ secrets.USES_CERT_KEY }}   # only for signed certificates
```

## Issuing the certificate

Whoever changes the code (a person or an agent, see `AGENTS.md`) issues
the certificate from the project root and commits it with the code:

```bash
uses-certifier certify . --certificate --min-level silver
uses-certifier check
```

The certificate is reproducible: the same sources, rules and key always
give the same file, so it only changes in a commit when the code or the
rules really changed.
