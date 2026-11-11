# Build integration

`uses-certifier check` compares the sources with the committed
`uses-certificate.json`. It needs no rules and no network, runs in well
under a second on typical projects, and exits with code 1 when:

- a method, class or file changed after it was certified (`INVALID`),
- new code is not in the certificate (`UNCERTIFIED`),
- certified code disappeared (`MISSING`),
- an element is below `--min-level` or the `min_level` of
  `.uses-certifier.yaml` (`BELOW_LEVEL`),
- the certificate was edited by hand.

Add it as the first step of the build so that uncertified code never
compiles. Every example assumes `uses-certifier` is installed
(`pip install git+https://github.com/manvalan/uses-certifier`). For
signed certificates, provide the key through `USES_CERT_KEY`; without it
the check still compares fingerprints and says so.

## Make

```make
.PHONY: certification
certification:
	uses-certifier check

build: certification
	$(CC) ...
```

## CMake

```cmake
add_custom_target(certification ALL
  COMMAND uses-certifier check ${CMAKE_SOURCE_DIR}/uses-certificate.json
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
  COMMENT "Checking code certification")
add_dependencies(my_target certification)
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
uses-certifier certify . --certificate uses-certificate.json --min-level silver
uses-certifier check
```

The certificate is reproducible: the same sources, rules and key always
give the same file, so it only changes in a commit when the code or the
rules really changed.
