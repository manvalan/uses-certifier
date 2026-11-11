"""Command line interface: certify, stamp, verify, rules."""
import argparse
import sys
from pathlib import Path

from . import __version__, certificate, certifier, config, rules, signing
from . import stamper, verify
from .model import NOT_CERTIFIED
from .reporters import FORMATS
from .reporters.common import everything, with_violations

EXIT_OK, EXIT_FAILED, EXIT_USAGE = 0, 1, 2


def main(argv=None):
    """Entry point of the uses-certifier command."""
    args = _parser().parse_args(argv)
    try:
        return args.handler(args)
    except (rules.RulesError, FileNotFoundError) as exc:
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
    _add_rules(sub)
    return parser


def _add_certify(sub):
    """Arguments of the certify command."""
    cmd = sub.add_parser("certify", help="certify a file or a folder")
    _common_options(cmd)
    cmd.add_argument("--format", choices=sorted(FORMATS), default="console")
    cmd.add_argument("--output", help="write the report to a file")
    cmd.add_argument("--certificate", help="write the JSON certificate")
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
    root = Path(args.path)
    base = root if root.is_dir() else root.parent
    project = config.load(base, args.config)
    path = rules.resolve_path(args.rules or project.rules_path)
    return project, rules.load(path, project)


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
    if args.certificate:
        data = certificate.write(cert, args.certificate)
        print(f"Certificate {data['certificate_id']} written to "
              f"{args.certificate}", file=sys.stderr)
    return _exit_code(cert, args.min_level or project.min_level)


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
    _, cert = _certify(args)
    changed = [m.path for m in cert.modules
               if stamper.write(Path(cert.root) / m.path, m)]
    for path in changed:
        print(f"stamped {path}")
    print(f"{len(changed)} files updated, {len(cert.modules)} certified, "
          f"project level: {cert.scorer.label(cert.level)}")
    return EXIT_OK


def run_verify(args):
    """Check stamps in the sources or in a JSON certificate."""
    if args.path.endswith(".json"):
        data = certificate.read(args.path)
        signer = signing.load(args.key_file)
        result = verify.verify_certificate(
            data, args.root or data["root"], signer)
    else:
        _, cert = _certify(args)
        result = verify.verify_inline(cert, cert.root)
    _print_verify(result)
    return EXIT_OK if result.ok else EXIT_FAILED


def _print_verify(result):
    """Print the outcome of a verification."""
    if not result.certificate_ok:
        print("CERTIFICATE ID DOES NOT MATCH ITS CONTENT")
    for name in result.invalid:
        print(f"INVALID   {name}")
    for name in result.missing:
        print(f"MISSING   {name}")
    print(f"Valid stamps: {result.valid}, invalid: {len(result.invalid)}, "
          f"missing: {len(result.missing)}")


def run_rules(args):
    """Print the active rules."""
    _, rulebook = _load(args)
    for rule in rulebook.rules:
        print(f"{rule.id:<8} {rule.severity:<8} {rule.scope:<9} "
              f"{rule.metric} {rule.operator} {rule.threshold}  "
              f"{rule.title}")
    return EXIT_OK
