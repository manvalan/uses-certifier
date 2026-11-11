import json

from uses_certifier import certificate, certifier, config, rules, verify
from uses_certifier.cli import main
from uses_certifier.reporters import FORMATS
from uses_certifier.signing import Signer

from conftest import RULES

GOOD = '''
def add(a, b):
    """Sum."""
    return a + b
'''

COMPLEX = '''
def pick(a, b, c):
    """Pick."""
    if a:
        return 1
    if b:
        return 2
    if c:
        return 3
    return 4
'''


def certify(root, rulebook, cfg=None, signer=None):
    return certifier.certify(root, rulebook, cfg or config.ProjectConfig(),
                             signer or Signer())


def test_clean_code_is_gold(project, rulebook):
    cert = certify(project({"a.py": GOOD}), rulebook)
    assert cert.level == "gold"
    assert all(e.level == "gold" for e in cert.entities())


def test_error_means_not_certified_and_propagates(project, rulebook):
    cert = certify(project({"a.py": GOOD + COMPLEX}), rulebook)
    module = cert.modules[0]
    add, pick = module.children
    assert add.level == "gold"
    assert pick.level == "none"
    assert pick.score == 100 - 20 - 7
    assert module.level == "none" and cert.level == "none"


def test_warning_gives_silver(project, rulebook):
    code = 'def f(a, b, c):\n    """Doc."""\n    return a\n'
    cert = certify(project({"a.py": code}), rulebook)
    assert cert.modules[0].children[0].level == "silver"


def test_suppression_restores_level(project, rulebook):
    code = "# uses-cert: ignore[T-001, T-002] known case\n" + COMPLEX.lstrip()
    cert = certify(project({"a.py": code}), rulebook)
    pick = cert.modules[0].children[0]
    assert all(v.suppressed for v in pick.violations)
    assert pick.level == "gold"


def test_overrides_and_exclusions(project):
    root = project({"a.py": COMPLEX, "tests/t.py": COMPLEX})
    cfg = config.ProjectConfig(exclude=["tests/*"],
                               overrides={"T-001": {"threshold": 10}})
    cert = certify(root, rules.load(RULES, cfg), cfg)
    assert [m.qualname for m in cert.modules] == ["a.py"]
    assert cert.modules[0].children[0].level == "silver"


def test_syntax_error_is_reported(project, rulebook):
    cert = certify(project({"bad.py": "def (:"}), rulebook)
    assert "bad.py" in cert.failures
    assert cert.level == "none"


def test_codes_are_unique_per_element(project, rulebook):
    same = GOOD.replace("add", "same")
    cert = certify(project({"a.py": same, "b.py": same}), rulebook)
    codes = [e.stamp for e in cert.entities()]
    assert len(set(codes)) == len(codes)


def test_key_changes_codes(project, rulebook):
    root = project({"a.py": GOOD})
    plain = certify(root, rulebook).modules[0].stamp
    keyed = certify(root, rulebook, signer=Signer(b"k")).modules[0].stamp
    assert plain != keyed


def test_certificate_and_verify(project, rulebook):
    root = project({"a.py": GOOD + COMPLEX})
    signer = Signer(b"secret")
    cert = certify(root, rulebook, signer=signer)
    data = json.loads(json.dumps(certificate.build(cert)))
    assert data["signed"] and data["certificate_id"]
    assert verify.verify_certificate(data, root, signer).ok
    assert not verify.verify_certificate(data, root, Signer(b"other")).ok

    path = root / "a.py"
    path.write_text(path.read_text().replace("return 4", "return 5"))
    result = verify.verify_certificate(data, root, signer)
    assert result.invalid == ["a.py", "pick"]
    assert result.valid == 1


def test_tampered_certificate_is_detected(project, rulebook):
    root = project({"a.py": GOOD + COMPLEX})
    signer = Signer(b"secret")
    data = certificate.build(certify(root, rulebook, signer=signer))
    data["level"] = "gold"
    assert not verify.verify_certificate(data, root, signer).certificate_ok


def test_all_formats_render(project, rulebook):
    cert = certify(project({"a.py": GOOD + COMPLEX}), rulebook)
    for render in FORMATS.values():
        assert "T-001" in render(cert)


def test_cli_exit_codes(project, capsys):
    root = project({"a.py": GOOD + COMPLEX})
    base = ["certify", str(root), "--rules", str(RULES)]
    assert main(base) == 0
    assert main(base + ["--min-level", "bronze"]) == 1
    assert main(["certify", str(root), "--rules", str(root)]) == 2
    out = root / "cert.json"
    assert main(["certify", str(root / "a.py"), "--rules", str(RULES),
                 "--certificate", str(out)]) == 0
    assert main(["verify", str(out)]) == 0
    capsys.readouterr()
