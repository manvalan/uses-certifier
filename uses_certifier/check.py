"""Build-time check: do the sources match their JSON certificate?

Needs neither the rules nor a network: only the certificate, the sources
and, for signed certificates, the key. Without the key the fingerprints
are still compared, but the signatures cannot be checked.
"""
from . import analyzers, markers
from .certificate import certificate_id, walk
from .signing import Signer
from .verify import VerifyResult


class _Checker:
    """Compares current sources with one certificate."""

    def __init__(self, data, signer):
        self.data = data
        self.signer = _effective_signer(data, signer)
        self.result = VerifyResult()

    def run(self, sources, min_level=None):
        """Check every current source and every certified file."""
        self._check_id()
        certified = {f["path"]: f for f in self.data["files"]}
        for path, relpath in sources:
            self._check_file(path, relpath, certified.pop(relpath, None))
        for relpath in certified:
            self.result.add("missing", relpath)
        if min_level:
            self._check_levels(min_level)
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

    def _check_file(self, path, relpath, stamped):
        """Compare the elements of one source with its certificate entry."""
        if stamped is None:
            self.result.add("uncertified", relpath)
            return
        certified = {(i["kind"], i["name"]): i for i in walk(stamped)}
        for key, entity in _current(path, relpath).items():
            self._check_element(relpath, entity, certified.pop(key, None))
        self.result.problems["missing"] += [
            f"{relpath}:{name}" for _, name in certified]

    def _check_element(self, relpath, entity, item):
        """Compare one current element with its certificate entry."""
        if item is None:
            self.result.add("uncertified", f"{relpath}:{entity.qualname}")
            return
        name = f"{item['path']}:{item['name']}"
        self.result.check(name, *self._codes(entity, item))

    def _codes(self, entity, item):
        """(certified, current) codes; fingerprints when there is no key."""
        if self.signer is None:
            return item["sha256"], entity.source_hash
        digest = self.data["rules"]["digest"]
        return item["stamp"], self.signer.stamp(entity, digest, item["level"])

    def _check_levels(self, min_level):
        """Flag certified elements below the required level."""
        levels = self.data["levels"] + ["none"]
        limit = levels.index(min_level)
        for item in (i for f in self.data["files"] for i in walk(f)):
            if levels.index(item["level"]) > limit:
                self.result.add("below_level",
                                f"{item['path']}:{item['name']} "
                                f"({item['level']})")


def _effective_signer(data, signer):
    """Signer matching how the certificate was issued, or None when the
    certificate is signed and no key is available."""
    if data["signed"]:
        return signer if signer.keyed else None
    return Signer()


def _current(path, relpath):
    """Current elements of a source by (kind, name); empty if unreadable."""
    try:
        text = markers.strip_stamps(path.read_text(encoding="utf-8"))
        module = analyzers.analyze(path, text, relpath)
    except (SyntaxError, UnicodeDecodeError, ValueError):
        return {}
    return {(e.kind, e.qualname): e for e in module.walk()}


def check(data, sources, signer, min_level=None):
    """Check the sources against a certificate."""
    return _Checker(data, signer).run(sources, min_level)
