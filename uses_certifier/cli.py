"""Interfaccia a riga di comando: certify, verify, rules."""
import argparse
import sys
from pathlib import Path

from . import __version__, certificate, certifier, config, rules
from .model import NOT_CERTIFIED
from .reporters import FORMATS
from .reporters.common import everything, with_violations
from .verify import verify

EXIT_OK, EXIT_BELOW_LEVEL, EXIT_USAGE = 0, 1, 2


def main(argv=None):
    """Punto di ingresso del comando uses-certifier."""
    args = _parser().parse_args(argv)
    try:
        return args.handler(args)
    except (rules.RulesError, FileNotFoundError) as exc:
        print(f"errore: {exc}", file=sys.stderr)
        return EXIT_USAGE


def _parser():
    """Definizione degli argomenti."""
    parser = argparse.ArgumentParser(
        prog="uses-certifier",
        description="Bollina metodi, classi e sorgenti secondo regole YAML.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(required=True, metavar="COMANDO")
    _add_certify(sub)
    _add_verify(sub)
    _add_rules(sub)
    return parser


def _add_certify(sub):
    """Argomenti del comando certify."""
    cmd = sub.add_parser("certify", help="certifica un file o una cartella")
    cmd.add_argument("path", help="file o cartella da certificare")
    _rules_options(cmd)
    cmd.add_argument("--format", choices=sorted(FORMATS), default="console")
    cmd.add_argument("--output", help="scrive il rapporto su file")
    cmd.add_argument("--certificate", help="scrive il certificato JSON")
    cmd.add_argument("--min-level", help="livello minimo richiesto")
    cmd.add_argument("--verbose", action="store_true",
                     help="mostra anche gli elementi senza violazioni")
    cmd.set_defaults(handler=run_certify)


def _add_verify(sub):
    """Argomenti del comando verify."""
    cmd = sub.add_parser("verify",
                         help="controlla che il codice certificato non sia "
                              "cambiato")
    cmd.add_argument("certificate", help="certificato JSON")
    cmd.add_argument("--root", help="cartella dei sorgenti (predefinita: "
                                    "quella registrata nel certificato)")
    cmd.set_defaults(handler=run_verify)


def _add_rules(sub):
    """Argomenti del comando rules."""
    cmd = sub.add_parser("rules", help="elenca le regole attive")
    cmd.add_argument("path", nargs="?", default=".",
                     help="progetto di cui leggere la configurazione")
    _rules_options(cmd)
    cmd.set_defaults(handler=run_rules)


def _rules_options(cmd):
    """Opzioni comuni per trovare regole e configurazione."""
    cmd.add_argument("--rules", help="clone di uses-rules "
                                     f"(oppure ${rules.ENV_VAR})")
    cmd.add_argument("--config", help="file di configurazione del progetto")


def _load(args):
    """Configurazione del progetto e regole attive."""
    root = Path(args.path)
    base = root if root.is_dir() else root.parent
    project = config.load(base, args.config)
    path = rules.resolve_path(args.rules or project.rules_path)
    return project, rules.load(path, project)


def run_certify(args):
    """Esegue la certificazione e scrive rapporto e certificato."""
    project, rulebook = _load(args)
    cert = certifier.certify(args.path, rulebook, project)
    select = everything if args.verbose else with_violations
    _emit(FORMATS[args.format](cert, select), args.output)
    if args.certificate:
        certificate.write(cert, args.certificate)
    wanted = args.min_level or project.min_level
    return _exit_code(cert, wanted)


def _emit(text, output):
    """Scrive il testo su file o sul terminale."""
    if output:
        Path(output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def _exit_code(cert, wanted):
    """Codice di uscita in base al livello minimo richiesto."""
    if not wanted:
        return EXIT_OK
    reached = cert.scorer.order(cert.level)
    if wanted != NOT_CERTIFIED and reached > cert.scorer.order(wanted):
        print(f"Livello {cert.scorer.label(cert.level)} sotto il minimo "
              f"richiesto ({cert.scorer.label(wanted)})", file=sys.stderr)
        return EXIT_BELOW_LEVEL
    return EXIT_OK


def run_verify(args):
    """Verifica le impronte del certificato."""
    data = certificate.read(args.certificate)
    result = verify(data, args.root or data["root"])
    for name in result.changed:
        print(f"MODIFICATO  {name}")
    for name in result.missing:
        print(f"MANCANTE    {name}")
    print(f"Bollini validi: {result.valid}, decaduti: "
          f"{len(result.changed) + len(result.missing)}")
    return EXIT_OK if result.ok else EXIT_BELOW_LEVEL


def run_rules(args):
    """Stampa le regole attive."""
    _, rulebook = _load(args)
    for rule in rulebook.rules:
        print(f"{rule.id:<8} {rule.severity:<8} {rule.scope:<9} "
              f"{rule.metric} {rule.operator} {rule.threshold}  "
              f"{rule.title}")
    return EXIT_OK
