"""Checks that stamps still match the code they were issued for.

A stamp code depends on file path, element, code fingerprint, rules and
level: it is valid only for that exact element. Any change to the code,
a copy to another element or a hand-edited level makes it invalid.
"""
from dataclasses import dataclass, field
from pathlib import Path

from . import analyzers, certificate, markers


@dataclass
class VerifyResult:
    """Valid stamps and the problems found."""

    valid: int = 0
    invalid: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    certificate_ok: bool = True
    signer: object = None

    @property
    def ok(self):
        """True when every stamp is valid."""
        return not (self.invalid or self.missing) and self.certificate_ok

    def check(self, name, written, expected):
        """Record the comparison of a written and an expected code."""
        if written is None:
            self.missing.append(name)
        elif written != expected:
            self.invalid.append(name)
        else:
            self.valid += 1


def verify_certificate(data, root, signer):
    """Compare a JSON certificate with the current sources."""
    result = VerifyResult(signer=signer)
    result.certificate_ok = (
        certificate.certificate_id(data, signer) == data["certificate_id"])
    for stamped in data["files"]:
        current = _current(Path(root) / stamped["path"], stamped["path"])
        for item in certificate.walk(stamped):
            _check_item(result, item, current, data["rules"]["digest"])
    return result


def _check_item(result, item, current, digest):
    """Compare one certificate entry with the current element."""
    entity = current.get((item["kind"], item["name"]))
    name = f"{item['path']}:{item['name']}"
    if entity is None:
        result.check(name, None, None)
        return
    expected = result.signer.stamp(entity, digest, item["level"])
    result.check(name, item["stamp"], expected)


def _current(path, relpath):
    """Current elements of a source by (kind, name); empty if missing."""
    if not path.is_file():
        return {}
    text = markers.strip_stamps(path.read_text(encoding="utf-8"))
    module = analyzers.analyze(path, text, relpath)
    return {(e.kind, e.qualname): e for e in module.walk()}


def verify_inline(cert, root):
    """Compare the stamps written in the sources with fresh ones."""
    result = VerifyResult()
    for module in cert.modules:
        text = (Path(root) / module.path).read_text(encoding="utf-8")
        _check_module(result, module, written_stamps(text))
    return result


def _check_module(result, module, written):
    """Compare the stamps written in one source with fresh ones."""
    for entity in module.walk():
        if entity.synthetic:
            continue
        key = 0 if entity.kind == "module" else entity.first_line
        result.check(f"{module.path}:{entity.qualname}",
                     written.get(key), f"{entity.level} {entity.stamp}")


def written_stamps(text):
    """Codes written in a source, keyed by the 1-based number of the line
    they stamp (0 for the file stamp)."""
    lines = text.splitlines()
    found = {}
    for index, line in enumerate(lines):
        parsed = markers.parse_stamp(line)
        if parsed:
            found[_stamped_line(lines, index, parsed[0])] = \
                f"{parsed[1]} {parsed[2]}"
    return found


def _stamped_line(lines, index, kind):
    """Number of the line a stamp refers to (0 for the file stamp)."""
    if kind == "stamp-file":
        return 0
    return _next_code_line(lines, index) + 1


def _next_code_line(lines, index):
    """Index of the first line after index that is not a marker."""
    index += 1
    while index < len(lines) and markers.kind(lines[index]):
        index += 1
    return index
