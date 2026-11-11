import json

from uses_certifier import certificate, certifier, config
from uses_certifier.check import check
from uses_certifier.cli import main
from uses_certifier.init import END, START, init_project
from uses_certifier.migration import Policy
from uses_certifier.signing import Signer

from conftest import RULES

CODE = '''
def add(a, b):
    """Sum."""
    return a + b


class Box:
    """Box."""

    def size(self):
        """Size."""
        return 1
'''


def issue(root, rulebook, signer=None):
    """Certify root and write its certificate inside it."""
    cert = certifier.certify(root, rulebook, config.ProjectConfig(),
                             signer or Signer())
    path = root / config.CERTIFICATE
    path.parent.mkdir(exist_ok=True)
    certificate.write(cert, path)
    return path


def run_check(path, signer=None, min_level=None):
    data = certificate.read(path)
    root = certificate.sources_root(path, data)
    sources = certifier.discover(root, config.ProjectConfig())
    return check(data, sources, signer or Signer(), Policy(min_level or ""))


def test_certificate_is_reproducible(project, rulebook, tmp_path_factory):
    first = issue(project({"a.py": CODE}), rulebook).read_bytes()
    again = issue(project({"a.py": CODE}), rulebook).read_bytes()
    assert first == again
    other = tmp_path_factory.mktemp("copy")
    (other / "a.py").write_text(CODE)
    assert issue(other, rulebook).read_bytes() == first


def test_certificate_lists_every_element(project, rulebook):
    data = certificate.read(issue(project({"a.py": CODE}), rulebook))
    names = [i["name"] for i in certificate.walk(data["files"][0])]
    assert names == ["a.py", "add", "Box", "Box.size"]
    assert data["root"] == ".."
    assert all(i["stamp"] for i in certificate.walk(data["files"][0]))


def test_unchanged_sources_pass(project, rulebook):
    result = run_check(issue(project({"a.py": CODE}), rulebook))
    assert result.ok and result.valid == 4


def test_changed_method_fails(project, rulebook):
    root = project({"a.py": CODE})
    path = issue(root, rulebook)
    (root / "a.py").write_text(CODE.replace("a + b", "a - b"))
    assert run_check(path).invalid == ["a.py:a.py", "a.py:add"]


def test_new_code_is_uncertified(project, rulebook):
    root = project({"a.py": CODE})
    path = issue(root, rulebook)
    (root / "a.py").write_text(CODE + "\n\ndef extra():\n    pass\n")
    (root / "b.py").write_text("X = 1\n")
    result = run_check(path)
    assert result.problems["uncertified"] == ["a.py:extra", "b.py"]


def test_removed_code_is_missing(project, rulebook):
    root = project({"a.py": CODE, "b.py": "X = 1\n"})
    path = issue(root, rulebook)
    (root / "b.py").unlink()
    assert run_check(path).missing == ["b.py"]


def test_hand_edited_certificate_fails(project, rulebook):
    path = issue(project({"a.py": CODE}), rulebook)
    data = json.loads(path.read_text())
    data["files"][0]["children"][0]["level"] = "silver"
    data["level"] = "silver"
    path.write_text(json.dumps(data))
    assert not run_check(path).ok


def test_signed_certificate(project, rulebook):
    root = project({"a.py": CODE})
    path = issue(root, rulebook, Signer(b"secret"))
    assert run_check(path, Signer(b"secret")).ok
    assert not run_check(path, Signer(b"wrong")).ok
    without_key = run_check(path)
    assert without_key.ok and without_key.notes
    (root / "a.py").write_text(CODE.replace("a + b", "b + a"))
    assert not run_check(path).ok


def test_min_level(project, rulebook):
    code = 'def f(a, b, c):\n    """Doc."""\n    return a\n'
    path = issue(project({"a.py": code}), rulebook)
    assert run_check(path, min_level="silver").ok
    result = run_check(path, min_level="gold")
    assert result.problems["below_level"] == ["a.py:a.py (silver)",
                                              "a.py:f (silver)"]


def test_cli_check_from_subfolder(project, capsys):
    root = project({"src/a.py": CODE})
    path = root / "uses-certificate.json"
    assert main(["certify", str(root / "src"), "--rules", str(RULES),
                 "--certificate", str(path)]) == 0
    assert json.loads(path.read_text())["root"] == "src"
    assert main(["check", str(path)]) == 0
    (root / "src" / "a.py").write_text(CODE + "\nY = 2\n")
    assert main(["check", str(path)]) == 1
    assert "INVALID" in capsys.readouterr().out


def test_init_creates_and_updates(tmp_path):
    actions = dict(init_project(tmp_path, "gold"))
    assert set(actions.values()) == {"created"}
    agents = (tmp_path / "AGENTS.md").read_text()
    assert START in agents and "**gold**" in agents
    assert "@AGENTS.md" in (tmp_path / "CLAUDE.md").read_text()
    assert "min_level: gold" in (tmp_path / ".uses-certifier.yaml").read_text()

    (tmp_path / "AGENTS.md").write_text("# Mine\n\n" + agents + "\nmore\n")
    dict(init_project(tmp_path, "silver"))
    updated = (tmp_path / "AGENTS.md").read_text()
    assert updated.startswith("# Mine") and updated.endswith("more\n")
    assert updated.count(START) == 1 and updated.count(END) == 1
    assert "**silver**" in updated


def stamp_and_issue(root, rulebook):
    """Write inline stamps and the certificate, as an agent would."""
    assert main(["stamp", str(root), "--rules", str(RULES)]) == 0
    return issue(root, rulebook)


def test_inline_stamps_match_the_certificate(project, rulebook):
    path = stamp_and_issue(project({"a.py": CODE}), rulebook)
    result = run_check(path)
    assert result.ok and result.valid == 8


def test_hand_edited_inline_stamp_fails(project, rulebook):
    root = project({"a.py": CODE})
    path = stamp_and_issue(root, rulebook)
    text = (root / "a.py").read_text()
    stamp = next(line for line in text.splitlines()
                 if "stamp GOLD" in line and "stamp-file" not in line)
    (root / "a.py").write_text(text.replace(stamp, stamp[:-4] + "0000"))
    assert run_check(path).invalid == ["a.py:add (inline stamp)"]


def test_removed_inline_stamp_is_missing(project, rulebook):
    root = project({"a.py": CODE})
    path = stamp_and_issue(root, rulebook)
    lines = (root / "a.py").read_text().splitlines(keepends=True)
    index = next(i for i, line in enumerate(lines) if "class Box" in line)
    del lines[index - 1]
    (root / "a.py").write_text("".join(lines))
    assert run_check(path).missing == ["a.py:Box (inline stamp)"]


def test_default_certificate_location(project, monkeypatch):
    root = project({"a.py": CODE})
    monkeypatch.chdir(root)
    assert main(["certify", ".", "--rules", str(RULES),
                 "--certificate"]) == 0
    assert (root / "certification" / "uses-certificate.json").is_file()
    assert not (root / "uses-certificate.json").exists()
    assert json.loads((root / config.CERTIFICATE).read_text())["root"] == ".."
    assert main(["check"]) == 0
