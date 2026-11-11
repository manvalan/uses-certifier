import json

from uses_certifier.cli import main

from conftest import RULES

GOOD = 'def add(a, b):\n    """Sum."""\n    return a + b\n'
LEGACY = 'def f(a, b, c):\n    """Doc."""\n    return a\n'


def migrating(project, files, coverage=0):
    """A project in migration mode that requires gold."""
    config = ("min_level: gold\nmode: migration\n"
              f"migration_min_coverage: {coverage}\n")
    return project({".uses-certifier.yaml": config, **files})


def certify(root):
    path = root / "uses-certificate.json"
    code = main(["certify", str(root), "--rules", str(RULES),
                 "--certificate", str(path)])
    return code, path


def test_build_without_certificate(project, capsys):
    root = migrating(project, {"a.py": LEGACY})
    assert main(["check", str(root / "uses-certificate.json")]) == 0
    out = capsys.readouterr().out
    assert "no certificate" in out and "0 of 1" in out


def test_strict_build_needs_a_certificate(project):
    root = project({"a.py": GOOD})
    assert main(["check", str(root / "uses-certificate.json")]) == 2


def test_only_migrated_files_are_checked(project, capsys):
    root = migrating(project, {"a.py": GOOD, "b.py": LEGACY})
    code, path = certify(root)
    assert code == 0
    (root / "b.py").write_text(LEGACY + "\nX = 1\n")
    (root / "c.py").write_text("Y = 2\n")
    assert main(["check", str(path)]) == 0
    assert "1 of 3" in capsys.readouterr().out
    (root / "a.py").write_text(GOOD + "\nX = 1\n")
    assert main(["check", str(path)]) == 1


def test_minimum_coverage(project, capsys):
    root = migrating(project, {"a.py": GOOD, "b.py": LEGACY}, coverage=60)
    code, path = certify(root)
    assert code == 1 and path.is_file()
    assert main(["check", str(path)]) == 1
    assert "COVERAGE" in capsys.readouterr().out
    (root / "b.py").write_text(GOOD.replace("add", "plus"))
    assert certify(root)[0] == 0
    assert main(["check", str(path)]) == 0


def test_migrated_file_cannot_fall_back(project, capsys):
    root = migrating(project, {"a.py": GOOD, "b.py": LEGACY})
    _, path = certify(root)
    before = path.read_text()
    (root / "a.py").write_text(LEGACY)
    assert certify(root)[0] == 1
    assert "REGRESSED    a.py" in capsys.readouterr().err
    assert path.read_text() == before


def test_stamp_leaves_legacy_files_alone(project):
    root = migrating(project, {"a.py": GOOD, "b.py": LEGACY})
    assert main(["stamp", str(root), "--rules", str(RULES)]) == 0
    assert "uses-cert: stamp" in (root / "a.py").read_text()
    assert (root / "b.py").read_text() == LEGACY


def test_init_migration(tmp_path):
    assert main(["init", str(tmp_path), "--migration"]) == 0
    settings = (tmp_path / ".uses-certifier.yaml").read_text()
    assert "mode: migration" in settings
    assert "migration" in (tmp_path / "AGENTS.md").read_text()


def test_unknown_mode(project):
    root = project({".uses-certifier.yaml": "mode: lax\n", "a.py": GOOD})
    assert main(["check", str(root / "uses-certificate.json")]) == 2
    assert json is not None
