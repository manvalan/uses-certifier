"""Explicit authorizations for code that builds without a valid
certificate.

By default the build check fails on any code that is not certified, is
certified below the required level, or no longer matches its
certificate. Only a person can let such code build, by listing it in the
authorizations file (certification/authorizations.yaml by default). Each
entry names the files (fnmatch pattern relative to the project root),
the reason and who authorized it, and may expire. Authorized problems
are printed on every build and expired or unused entries are reported,
so nothing passes silently.
"""
from dataclasses import asdict, dataclass
from datetime import date
from fnmatch import fnmatch
from pathlib import Path

import yaml

from .config import ConfigError

REQUIRED = ("path", "reason", "authorized_by")
HEADER = """\
# Code allowed to build without a valid uses-certifier certificate.
# Only a person may add or extend an entry, and every entry is printed
# on each build. Remove an entry as soon as its files are certified.
# See https://github.com/manvalan/uses-certifier#authorizations
"""


@dataclass(frozen=True)
class Authorization:
    """Permission for some files to build without a valid certificate."""

    path: str
    reason: str
    authorized_by: str
    expires: date | None = None

    @classmethod
    def parse(cls, entry):
        """Authorization from one YAML entry; ConfigError when the entry
        lacks a field or has a malformed expiry date."""
        missing = [key for key in REQUIRED if not _text(entry, key)]
        if missing:
            raise ConfigError(f"authorization {entry!r} lacks: "
                              f"{', '.join(missing)}")
        return cls(*(_text(entry, key) for key in REQUIRED),
                   _expiry(entry))

    def covers(self, relpath):
        """True when the authorization applies to the file."""
        return fnmatch(relpath, self.path)

    def expired(self, today):
        """True when the authorization is no longer valid on today."""
        return self.expires is not None and today > self.expires

    def describe(self):
        """Reason, author and expiry, as printed by the build."""
        until = f", until {self.expires}" if self.expires else ""
        return f"{self.reason} (authorized by {self.authorized_by}{until})"


def _text(entry, key):
    """Stripped text of a field of an entry ('' when absent)."""
    return str(entry.get(key) or "").strip()


def _expiry(entry):
    """Expiry date of an entry, None when it never expires."""
    expires = entry.get("expires")
    if expires is None or isinstance(expires, date):
        return expires
    raise ConfigError(f"authorization for {entry['path']}: expires must "
                      f"be a date (YYYY-MM-DD), not {expires!r}")


def load(path):
    """Authorizations listed in a file; none when it does not exist."""
    path = Path(path)
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [Authorization.parse(entry) for entry in _entries(data, path)]


def _entries(data, path):
    """The list of entries of an authorizations file."""
    entries = data.get("authorizations") if isinstance(data, dict) else 0
    if isinstance(entries, list) and all(
            isinstance(entry, dict) for entry in entries):
        return entries
    raise ConfigError(f"{path}: expected a list of entries under "
                      "'authorizations'")


def save(path, authorizations):
    """Write the authorizations file."""
    entries = [{k: v for k, v in asdict(a).items() if v is not None}
               for a in authorizations]
    text = yaml.safe_dump({"authorizations": entries}, sort_keys=False,
                          allow_unicode=True)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(HEADER + text, encoding="utf-8")


def problem_file(name):
    """File of a problem, such as src/a.cpp for 'src/a.cpp:run (silver)'."""
    return name.split(":", 1)[0]


def problem_files(result):
    """Files with at least one problem in a check result, sorted."""
    return sorted({problem_file(name)
                   for names in result.problems.values() for name in names})


class Gate:
    """Lets the problems of authorized files through, and only those."""

    def __init__(self, authorizations, today):
        self.active = [a for a in authorizations if not a.expired(today)]
        self.expired = [a for a in authorizations if a.expired(today)]
        self.used = set()

    def admit(self, result):
        """Move the problems of authorized files from result.problems to
        result.authorized, and note expired or unused authorizations."""
        for kind, names in result.problems.items():
            result.problems[kind] = [
                name for name in names
                if not self._admitted(result, kind, name)]
        result.notes.extend(self._notes())
        return result

    def _admitted(self, result, kind, name):
        """Record the problem as authorized when an entry covers it."""
        grant = next((a for a in self.active
                      if a.covers(problem_file(name))), None)
        if grant is not None:
            self.used.add(grant)
            result.authorized.append((kind, name, grant))
        return grant is not None

    def _notes(self):
        """Expired and unused authorizations, one note each."""
        notes = [f"authorization for {a.path} expired on {a.expires}"
                 for a in self.expired]
        notes += [f"authorization for {a.path} is no longer needed: "
                  "remove it" for a in self.active if a not in self.used]
        return notes
