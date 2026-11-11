"""Build-time check: do the sources match their certificate?

The certificate is the JSON file and, when the project keeps them, the
stamps written in the sources: both must match the current code. The
check needs neither the rules nor a network: only the certificate, the
sources and, for signed certificates, the key. Without the key the
fingerprints are still compared, but the signatures cannot be checked.

In migration mode only the files already certified at the required level
are checked; the others are legacy (see migration.py).
"""
from . import certifier, migration
from .certificate import certificate_id, walk
from .model import NOT_CERTIFIED
from .signing import Signer
from .verify import VerifyResult, take_stamp, written_stamps


class _Checker:
    """Compares current sources with one certificate."""

    def __init__(self, data, signer, policy):
        self.data = data
        self.signer = _effective_signer(data, signer)
        self.policy = policy
        self.result = VerifyResult()

    def run(self, sources):
        """Check every current source and every certified file."""
        self._check_id()
        sources = list(sources)
        certified = {f["path"]: f for f in self.data["files"]}
        for path, relpath in sources:
            self._check_source(path, relpath, certified.pop(relpath, None))
        for relpath in certified:
            self.result.add("missing", relpath)
        if self.policy.migration:
            self._check_coverage(len(sources))
        return self.result

    def _check_id(self):
        """Check that the certificate was not edited by hand."""
        if self.signer is None:
            self.result.notes.append(
                "signed certificate and no key: signatures not checked, "
                "fingerprints compared instead")
            return
        expected = certificate_id(self.data, self.signer)
        self.result.certificate_ok = expected == self.data["certificate_id"]

    def _check_source(self, path, relpath, entry):
        """Check one source, unless it is legacy code being migrated."""
        if self.policy.migration and not self._migrated(entry):
            return
        if entry is None:
            self.result.add("uncertified", relpath)
            return
        self.result.files_checked += 1
        self._compare(_Source(path, relpath), entry)
        self._check_levels(entry)

    def _migrated(self, entry):
        """True when a certificate entry reached the wanted level."""
        levels = self.data["levels"]
        return entry is not None and migration.at_level(
            entry["level"], self.policy.wanted(levels), levels)

    def _compare(self, source, entry):
        """Compare the elements of one source with its certificate entry."""
        remaining = {(i["kind"], i["name"]): i for i in walk(entry)}
        for key, entity in source.elements.items():
            self._check_element(source, entity, remaining.pop(key, None))
        source.stamps.report_stray(self.result, source.relpath)
        self.result.problems["missing"] += [
            f"{source.relpath}:{name}" for _, name in remaining]

    def _check_element(self, source, entity, item):
        """Compare one current element with its certificate entry."""
        if item is None:
            self.result.add("uncertified",
                            f"{source.relpath}:{entity.qualname}")
            return
        self.result.check(f"{item['path']}:{item['name']}",
                          *self._codes(entity, item))
        source.stamps.check(self.result, entity, item)

    def _codes(self, entity, item):
        """(certified, current) codes; fingerprints when there is no key."""
        if self.signer is None:
            return item["sha256"], entity.source_hash
        digest = self.data["rules"]["digest"]
        return item["stamp"], self.signer.stamp(entity, digest, item["level"])

    def _check_levels(self, entry):
        """Flag the elements of a checked file below the required level."""
        if not self.policy.min_level:
            return
        levels = self.data["levels"]
        for item in walk(entry):
            if not migration.at_level(item["level"], self.policy.min_level,
                                      levels):
                self.result.add("below_level",
                                f"{item['path']}:{item['name']} "
                                f"({item['level']})")

    def _check_coverage(self, total):
        """Report the progress of the migration against its minimum."""
        done = self.result.files_checked
        wanted = self.policy.wanted(self.data["levels"])
        self.result.notes.append(
            migration.coverage_note(done, total, self.policy, wanted))
        self.result.coverage_ok = (migration.coverage(done, total) >=
                                   self.policy.min_coverage)


class _Source:
    """A source file: its current elements and its written stamps."""

    def __init__(self, path, relpath):
        self.relpath = relpath
        try:
            text = path.read_text(encoding="utf-8")
            module = certifier.analyze_file(path, relpath)
        except (SyntaxError, UnicodeDecodeError, ValueError):
            text, module = "", None
        self.elements = {(e.kind, e.qualname): e
                         for e in (module.walk() if module else [])}
        self.stamps = _WrittenStamps(text)


class _WrittenStamps:
    """Stamps written in a source, consumed as its elements are checked.

    A source without a file stamp is not stamped (the project may not
    keep stamps); a stamped source must carry the certificate's code for
    every element, and no stamp may be left over.
    """

    def __init__(self, text):
        self.codes = written_stamps(text)
        self.in_use = 0 in self.codes

    def check(self, result, entity, item):
        """Compare the stamp written above an element with the JSON."""
        if not self.in_use or entity.synthetic:
            return
        line = 0 if entity.kind == "module" else entity.first_line
        expected = f"{item['level']} {item['stamp']}"
        result.check(f"{item['path']}:{item['name']} (inline stamp)",
                     take_stamp(self.codes, line, expected), expected)

    def report_stray(self, result, relpath):
        """Stamps that belong to no current element."""
        if not self.in_use:
            return
        for line in sorted(self.codes):
            result.add("invalid", f"{relpath}:{line} (stray inline stamp)")


def _effective_signer(data, signer):
    """Signer matching how the certificate was issued, or None when the
    certificate is signed and no key is available."""
    if data["signed"]:
        return signer if signer.keyed else None
    return Signer()


def empty_certificate():
    """Certificate of a project that has not been certified yet."""
    data = {"signed": False, "rules": {"digest": ""}, "levels": [],
            "level": NOT_CERTIFIED, "files": [], "failures": {}}
    data["certificate_id"] = certificate_id(data, Signer())
    return data


def check(data, sources, signer, policy=None):
    """Check the sources against a certificate."""
    return _Checker(data, signer, policy or migration.Policy()).run(sources)
