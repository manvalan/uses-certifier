from uses_certifier import certifier, config, markers, stamper, verify
from uses_certifier.signing import Signer

from conftest import RULES
from uses_certifier.cli import main

CODE = '''#!/usr/bin/env python
"""Module."""
import functools


class Cart:
    """Cart."""

    # uses-cert: ignore[T-002] legacy
    @functools.cache
    def total(self, a, b, c):
        """Total."""
        return a + b + c


def helper(x):
    """Helper."""
    return x
'''


def certify(root, rulebook):
    return certifier.certify(root, rulebook, config.ProjectConfig(),
                             Signer())


def stamp(root, rulebook):
    cert = certify(root, rulebook)
    for module in cert.modules:
        stamper.write(root / module.path, module)
    return cert


def test_stamp_places_lines(project, rulebook):
    root = project({"a.py": CODE})
    stamp(root, rulebook)
    lines = (root / "a.py").read_text().splitlines()
    assert lines[0] == "#!/usr/bin/env python"
    assert markers.parse_stamp(lines[1])[0] == "stamp-file"
    total = lines.index("    @functools.cache")
    assert lines[total - 1] == "    # uses-cert: ignore[T-002] legacy"
    assert lines[total - 2].startswith("    # uses-cert: stamp ")
    assert markers.parse_stamp(lines[lines.index("class Cart:") - 1])


def test_stamping_is_stable_and_verifiable(project, rulebook):
    root = project({"a.py": CODE})
    first = stamp(root, rulebook)
    text = (root / "a.py").read_text()
    second = stamp(root, rulebook)
    assert (root / "a.py").read_text() == text
    assert [e.stamp for e in first.entities()] == \
        [e.stamp for e in second.entities()]
    result = verify.verify_inline(certify(root, rulebook), root)
    assert result.ok and result.valid == 4


def test_changed_code_invalidates_only_its_stamps(project, rulebook):
    root = project({"a.py": CODE})
    stamp(root, rulebook)
    path = root / "a.py"
    path.write_text(path.read_text().replace("return x", "return x * 2"))
    result = verify.verify_inline(certify(root, rulebook), root)
    assert result.invalid == ["a.py:a.py", "a.py:helper"]
    assert result.valid == 2


def test_copied_stamp_is_invalid(project, rulebook):
    root = project({"a.py": "def f():\n    pass\n\n\ndef g():\n    pass\n"})
    stamp(root, rulebook)
    path = root / "a.py"
    lines = path.read_text().splitlines()
    stamps = [i for i, line in enumerate(lines) if "stamp GOLD" in line]
    lines[stamps[1]] = lines[stamps[0]]
    path.write_text("\n".join(lines) + "\n")
    result = verify.verify_inline(certify(root, rulebook), root)
    assert result.invalid == ["a.py:g"]


def test_line_numbers_point_to_real_lines(project, rulebook):
    root = project({"a.py": CODE})
    cert = stamp(root, rulebook)
    cert = certify(root, rulebook)
    lines = (root / "a.py").read_text().splitlines()
    helper = cert.modules[0].children[1]
    assert lines[helper.start_line - 1] == "def helper(x):"


def test_java_stamps(project, rulebook):
    code = "class A {\n  int f(int x) {\n    return x;\n  }\n}\n"
    root = project({"A.java": code})
    stamp(root, rulebook)
    text = (root / "A.java").read_text()
    assert text.startswith("// uses-cert: stamp-file ")
    assert "  // uses-cert: stamp " in text
    assert verify.verify_inline(certify(root, rulebook), root).ok


def test_cli_stamp_and_verify(project, capsys):
    root = project({"a.py": CODE})
    args = ["--rules", str(RULES)]
    assert main(["stamp", str(root)] + args) == 0
    assert main(["verify", str(root)] + args) == 0
    (root / "a.py").write_text((root / "a.py").read_text() + "\nX = 1\n")
    assert main(["verify", str(root)] + args) == 1
    capsys.readouterr()
