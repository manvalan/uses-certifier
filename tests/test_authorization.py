from datetime import date

import pytest

from uses_certifier import authorization
from uses_certifier.authorization import Authorization, Gate
from uses_certifier.cli import main
from uses_certifier.config import AUTHORIZATIONS as AUTH
from uses_certifier.config import CERTIFICATE as CERT, ConfigError
from uses_certifier.verify import VerifyResult

from conftest import RULES

GOOD = 'def add(a, b):\n    """Sum."""\n    return a + b\n'
TODAY = date(2026, 11, 14)


def grant(path, expires=None):
    return Authorization(path, "legacy parser", "Ann", expires)


def failing(*names):
    result = VerifyResult()
    for name in names:
        result.add("uncertified", name)
    return result


def certified(project):
    root = project({"a.py": GOOD, "b.py": GOOD.replace("add", "plus")})
    path = root / CERT
    assert main(["certify", str(root), "--rules", str(RULES),
                 "--certificate", str(path)]) == 0
    return root, path


def test_parse_requires_reason_and_author():
    with pytest.raises(ConfigError, match="reason, authorized_by"):
        Authorization.parse({"path": "a.py"})


def test_parse_rejects_malformed_dates():
    with pytest.raises(ConfigError, match="YYYY-MM-DD"):
        Authorization.parse({"path": "a.py", "reason": "r",
                             "authorized_by": "Ann", "expires": "soon"})


def test_load_rejects_other_shapes(tmp_path):
    path = tmp_path / "auth.yaml"
    path.write_text("authorizations: a.py\n")
    with pytest.raises(ConfigError, match="list of entries"):
        authorization.load(path)


def test_missing_file_authorizes_nothing(tmp_path):
    assert authorization.load(tmp_path / "none.yaml") == []


def test_gate_lets_through_only_covered_files():
    result = Gate([grant("legacy/*")], TODAY).admit(
        failing("legacy/a.cpp:run", "src/b.cpp"))
    assert result.problems["uncertified"] == ["src/b.cpp"]
    assert result.authorized == [("uncertified", "legacy/a.cpp:run",
                                  grant("legacy/*"))]


def test_expired_authorizations_stop_working():
    result = Gate([grant("a.py", date(2026, 11, 13))], TODAY).admit(
        failing("a.py"))
    assert not result.ok
    assert "expired on 2026-11-13" in result.notes[0]


def test_unused_authorizations_are_reported():
    result = Gate([grant("a.py")], TODAY).admit(VerifyResult())
    assert result.ok
    assert result.notes == ["authorization for a.py is no longer needed: "
                            "remove it"]


def test_changed_code_needs_authorization(project, capsys):
    root, path = certified(project)
    (root / "a.py").write_text(GOOD.replace("a + b", "a - b"))
    assert main(["check", str(path)]) == 1
    capsys.readouterr()
    assert main(["authorize", str(path), "--reason", "hotfix",
                 "--by", "Ann", "--expires", "2099-01-31"]) == 0
    assert "1 file(s) authorized" in capsys.readouterr().out
    assert main(["check", str(path)]) == 0
    out = capsys.readouterr().out
    assert ("AUTHORIZED   invalid a.py:add: hotfix (authorized by Ann, "
            "until 2099-01-31)") in out
    saved = authorization.load(root / AUTH)
    assert saved == [Authorization("a.py", "hotfix", "Ann",
                                   date(2099, 1, 31))]


def test_authorize_keeps_existing_entries(project):
    root, path = certified(project)
    (root / "a.py").write_text(GOOD + "\nX = 1\n")
    authorization.save(root / AUTH, [grant("b.py")])
    assert main(["authorize", str(path), "--reason", "r",
                 "--by", "Ann"]) == 0
    paths = [a.path for a in authorization.load(root / AUTH)]
    assert paths == ["b.py", "a.py"]


def test_authorizations_file_from_the_command_line(project, tmp_path):
    root, path = certified(project)
    (root / "c.py").write_text("Y = 2\n")
    other = tmp_path / "elsewhere.yaml"
    authorization.save(other, [grant("c.py")])
    assert main(["check", str(path)]) == 1
    assert main(["check", str(path), "--authorizations", str(other)]) == 0
