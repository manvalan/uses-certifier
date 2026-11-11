"""Command line interface: certify, stamp, verify, rules."""
import argparse
import os
import sys
from pathlib import Path

from . import __version__, certificate, certifier, config, rules, signing
from . import guide, migration, rules_cache, stamper, verify
from .check import check, empty_certificate
from .init import init_project
from .model import NOT_CERTIFIED
from .reporters import FORMATS
from .reporters.common import everything, with_violations
from .reporters.console import summary

EXIT_OK, EXIT_FAILED, EXIT_USAGE = 0, 1, 2


def main(argv=None):
    """Entry point of the uses-certifier command."""
    args = _parser().parse_args(argv)
    try:
        return args.handler(args)
    except (rules.RulesError, rules_cache.FetchError,
            config.ConfigError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE


def _parser():
    """Argument definitions."""
    parser = argparse.ArgumentParser(
        prog="uses-certifier",
        description="Stamps methods, classes and source files using YAML "
                    "rules.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(required=True, metavar="COMMAND")
    _add_certify(sub)
    _add_stamp(sub)
    _add_verify(sub)
    _add_check(sub)
    _add_rules(sub)
    _add_init(sub)
    _add_onboarding(sub)
    return parser


def _add_certify(sub):
    """Arguments of the certify command."""
    cmd = sub.add_parser("certify", help="certify a file or a folder")
    _common_options(cmd)
    cmd.add_argument("--format", choices=sorted(FORMATS), default="console")
    cmd.add_argument("--output", help="write the report to a file")
    cmd.add_argument("--certificate", nargs="?", const="",
                     help="write the JSON certificate (default path: "
                          f"{config.CERTIFICATE} in the project)")
    cmd.add_argument("--min-level", help="minimum required level")
    cmd.add_argument("--verbose", action="store_true",
                     help="also show elements without violations")
    cmd.set_defaults(handler=run_certify)


def _add_stamp(sub):
    """Arguments of the stamp command."""
    cmd = sub.add_parser("stamp", help="write stamps into the sources")
    _common_options(cmd)
    cmd.set_defaults(handler=run_stamp)


def _add_verify(sub):
    """Arguments of the verify command."""
    cmd = sub.add_parser(
        "verify", help="check stamps in the sources, or a JSON certificate")
    _common_options(cmd, target="sources folder or certificate .json")
    cmd.add_argument("--root", help="sources folder for a certificate "
                                    "(default: the one it records)")
    cmd.set_defaults(handler=run_verify)


def _add_check(sub):
    """Arguments of the check command."""
    cmd = sub.add_parser(
        "check", help="fast build check of the sources against the JSON "
                      "certificate (no rules needed)")
    cmd.add_argument("certificate", nargs="?",
                     help="certificate (default: the project's, "
                          f"{config.CERTIFICATE})")
    cmd.add_argument("--min-level", help="also require this level")
    cmd.add_argument("--config", help="project configuration file")
    cmd.add_argument("--key-file", help="secret key that signs the stamps "
                                        f"(or ${signing.KEY_ENV})")
    cmd.set_defaults(handler=run_check)


def _add_init(sub):
    """Arguments of the init command."""
    cmd = sub.add_parser(
        "init", help="add configuration and agent instructions to a project")
    cmd.add_argument("path", nargs="?", default=".", help="project root")
    _level_and_mode(cmd)
    cmd.set_defaults(handler=run_init)


def _level_and_mode(cmd):
    """Options that choose the required level and the project mode."""
    cmd.add_argument("--min-level", default="silver",
                     help="level required by the project (default: silver)")
    cmd.add_argument("--migration", dest="mode", action="store_const",
                     const=config.MIGRATION, default=config.STRICT,
                     help="existing program: build without a full "
                          "certificate and migrate it file by file")


def _add_onboarding(sub):
    """Arguments of fetch-rules, guide and setup."""
    fetch = sub.add_parser("fetch-rules",
                           help="download or update the uses-rules cache")
    fetch.add_argument("--ref", default="main", help="branch or tag")
    fetch.set_defaults(handler=run_fetch_rules)
    show = sub.add_parser("guide", help="explain certification and the "
                                        "rules in force (Markdown)")
    _project_options(show)
    show.set_defaults(handler=run_guide)
    setup = sub.add_parser("setup", help="fetch the rules, init the "
                                         "project and certify it once")
    _project_options(setup)
    _level_and_mode(setup)
    setup.add_argument("--ref", default="main", help="uses-rules branch")
    setup.set_defaults(handler=run_setup)


def _project_options(cmd):
    """Path, rules and configuration options."""
    cmd.add_argument("path", nargs="?", default=".", help="project root")
    cmd.add_argument("--rules", help="clone of uses-rules "
                                     f"(or ${rules.ENV_VAR})")
    cmd.add_argument("--config", help="project configuration file")
    cmd.set_defaults(key_file=None)


def _add_rules(sub):
    """Arguments of the rules command."""
    cmd = sub.add_parser("rules", help="list the active rules")
    cmd.add_argument("path", nargs="?", default=".",
                     help="project whose configuration is read")
    cmd.add_argument("--rules", help="clone of uses-rules "
                                     f"(or ${rules.ENV_VAR})")
    cmd.add_argument("--config", help="project configuration file")
    cmd.set_defaults(handler=run_rules)


def _common_options(cmd, target="file or folder to process"):
    """Options shared by certify, stamp and verify."""
    cmd.add_argument("path", help=target)
    cmd.add_argument("--rules", help="clone of uses-rules "
                                     f"(or ${rules.ENV_VAR})")
    cmd.add_argument("--config", help="project configuration file")
    cmd.add_argument("--key-file", help="secret key that signs the stamps "
                                        f"(or ${signing.KEY_ENV})")


def _load(args):
    """Project configuration and active rules."""
    project = config.load(_project_root(args), args.config)
    path = rules.resolve_path(args.rules or project.rules_path)
    return project, rules.load(path, project)


def _project_root(args):
    """Folder of the project being certified."""
    root = Path(args.path)
    return root if root.is_dir() else root.parent


def _certificate_path(args, project):
    """Certificate to write: the given path, the project's default when
    --certificate has no value, None when it is absent."""
    if args.certificate is None:
        return None
    return args.certificate or project.certificate_path(_project_root(args))


def _certify(args):
    """Certify the path given on the command line."""
    project, rulebook = _load(args)
    signer = signing.load(args.key_file)
    return project, certifier.certify(args.path, rulebook, project, signer)


def run_certify(args):
    """Run the certification and write report and certificate."""
    project, cert = _certify(args)
    select = everything if args.verbose else with_violations
    _emit(FORMATS[args.format](cert, select), args.output)
    policy = migration.Policy.of(project, args.min_level)
    path = _certificate_path(args, project)
    if policy.migration:
        return _certify_migration(cert, policy, path)
    if path:
        _write_certificate(certificate.build_for(cert, path), path)
    return _exit_code(cert, policy.min_level)


def _write_certificate(data, path):
    """Save the certificate and say so."""
    certificate.save(data, path)
    print(f"Certificate {data['certificate_id']} written to {path}",
          file=sys.stderr)


def _certify_migration(cert, policy, path):
    """Migration mode: report the progress, refuse regressions."""
    data = certificate.build_for(cert, path or cert.root)
    if _report_regressions(path, data, policy):
        print("Certificate not written: fix the regressions first",
              file=sys.stderr)
        return EXIT_FAILED
    if path:
        _write_certificate(data, path)
    return _coverage_exit(data, policy)


def _report_regressions(path, data, policy):
    """Print the migrated files that fell back; True when there are."""
    fallen = _regressions(path, data, policy)
    for name in fallen:
        print(f"REGRESSED    {name}: was certified at "
              f"{policy.wanted(data['levels'])}", file=sys.stderr)
    return bool(fallen)


def _regressions(path, data, policy):
    """Migrated files of the existing certificate now below the level."""
    if not path or not Path(path).is_file():
        return []
    return migration.regressions(certificate.read(path), data, policy)


def _coverage_exit(data, policy):
    """Print the migration progress; exit code depending on the
    required coverage."""
    done = len(migration.migrated(data, policy))
    total = len(data["files"]) + len(data["failures"])
    wanted = policy.wanted(data["levels"])
    print(migration.coverage_note(done, total, policy, wanted),
          file=sys.stderr)
    if migration.coverage(done, total) < policy.min_coverage:
        print("Migration coverage below the required "
              f"{policy.min_coverage:g}%", file=sys.stderr)
        return EXIT_FAILED
    return EXIT_OK


def _emit(text, output):
    """Write text to a file or to the terminal."""
    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def _exit_code(cert, wanted):
    """Exit code depending on the minimum required level."""
    if not wanted:
        return EXIT_OK
    reached = cert.scorer.order(cert.level)
    if wanted != NOT_CERTIFIED and reached > cert.scorer.order(wanted):
        print(f"Level {cert.scorer.label(cert.level)} is below the "
              f"required {cert.scorer.label(wanted)}", file=sys.stderr)
        return EXIT_FAILED
    return EXIT_OK


def run_stamp(args):
    """Write fresh stamps into every certified source."""
    project, cert = _certify(args)
    changed = [m.path for m in _to_stamp(cert, project)
               if stamper.write(Path(cert.root) / m.path, m)]
    for path in changed:
        print(f"stamped {path}")
    print(f"{len(changed)} files updated, {len(cert.modules)} certified, "
          f"project level: {cert.scorer.label(cert.level)}")
    return EXIT_OK


def _to_stamp(cert, project):
    """Sources to stamp: all of them, or in migration mode only the
    migrated ones (legacy code is left untouched)."""
    policy = migration.Policy.of(project)
    if not policy.migration:
        return cert.modules
    levels = [level["id"] for level in cert.scorer.levels]
    wanted = policy.wanted(levels)
    return [m for m in cert.modules
            if migration.at_level(m.level, wanted, levels)]


def run_verify(args):
    """Check stamps in the sources or in a JSON certificate."""
    if args.path.endswith(".json"):
        return _check_certificate(args.path, args)
    _, cert = _certify(args)
    result = verify.verify_inline(cert, cert.root)
    _print_verify(result)
    return EXIT_OK if result.ok else EXIT_FAILED


def run_check(args):
    """Build check of the sources against the JSON certificate."""
    path = args.certificate
    if path is None:
        path = config.load(".", args.config).certificate_path(".")
    return _check_certificate(path, args)


def _check_certificate(path, args):
    """Check sources against a certificate and print the outcome."""
    data, root = _read_certificate(path, getattr(args, "root", None))
    project = config.load(root, args.config)
    if data is None:
        data = _no_certificate(path, project)
    policy = migration.Policy.of(project, getattr(args, "min_level", None))
    result = check(data, certifier.discover(root, project),
                   signing.load(args.key_file), policy)
    _print_verify(result)
    return EXIT_OK if result.ok else EXIT_FAILED


def _read_certificate(path, root=None):
    """(certificate data, or None when there is none yet; sources root)."""
    if not Path(path).is_file():
        return None, Path(root or config.find_root(Path(path).parent))
    data = certificate.read(path)
    return data, Path(root or certificate.sources_root(path, data))


def _no_certificate(path, project):
    """An empty certificate for a project being migrated; an error in a
    strict project."""
    if not project.migrating:
        raise FileNotFoundError(f"certificate {path} not found")
    print(f"note: no certificate {path} yet: every file is legacy")
    return empty_certificate()


def _print_notes(result):
    """Notes and whole-certificate problems of a verification."""
    for note in result.notes:
        print(f"note: {note}")
    if not result.certificate_ok:
        print("CERTIFICATE ID DOES NOT MATCH ITS CONTENT")
    if not result.coverage_ok:
        print("MIGRATION COVERAGE BELOW THE REQUIRED MINIMUM")


def _print_verify(result):
    """Print the outcome of a verification."""
    _print_notes(result)
    for kind, names in result.problems.items():
        for name in names:
            print(f"{kind.upper():<12} {name}")
    counts = ", ".join(f"{kind}: {len(names)}"
                       for kind, names in result.problems.items())
    status = "OK" if result.ok else "FAILED"
    print(f"Certification check {status}. Valid: {result.valid}, {counts}")


def run_init(args):
    """Add configuration and agent instructions to a project."""
    _init(args)
    return EXIT_OK


def _init(args):
    """Create or update configuration and agent instructions."""
    root = Path(args.path)
    for path, action in init_project(root, args.min_level, args.mode):
        print(f"{action:<8} {path}")


def run_fetch_rules(args):
    """Download or update the cached rules."""
    print(f"rules ready in {rules_cache.fetch(args.ref)}")
    return EXIT_OK


def run_guide(args):
    """Print the guide for the rules in force."""
    project, rulebook = _load(args)
    print(guide.render(rulebook, project.min_level or "silver"))
    return EXIT_OK


def run_setup(args):
    """Fetch the rules, init the project, certify it once."""
    if not (args.rules or os.environ.get(rules.ENV_VAR)):
        args.rules = str(rules_cache.fetch(args.ref))
    print(f"rules    {rules.resolve_path(args.rules)}")
    _init(args)
    _, cert = _certify(args)
    print("\n".join([""] + summary(cert)))
    print(NEXT_STEPS.format(level=args.min_level))
    return EXIT_OK


NEXT_STEPS = """
Next steps:
  1. Read the rules: uses-certifier guide .
  2. See what to fix: uses-certifier certify . --verbose
  3. Refactor until the project reaches {level}.
  4. Issue the certificate:
     uses-certifier certify . --certificate --min-level {level}
  5. Add `uses-certifier check` as the first build step
     (see docs/build-integration.md in manvalan/uses-certifier)
  6. Commit .uses-certifier.yaml, AGENTS.md, CLAUDE.md,
     certification/ and the build change."""


def run_rules(args):
    """Print the active rules."""
    _, rulebook = _load(args)
    for rule in rulebook.rules:
        print(f"{rule.id:<8} {rule.severity:<8} {rule.scope:<9} "
              f"{rule.metric} {rule.operator} {rule.threshold}  "
              f"{rule.title}")
    return EXIT_OK
