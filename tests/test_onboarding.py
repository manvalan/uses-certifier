import subprocess

import pytest

from uses_certifier import guide, rules_cache
from uses_certifier.cli import main

from conftest import RULES


@pytest.fixture
def rules_repo(tmp_path, monkeypatch):
    """A local git repository with the test rules, and an empty cache."""
    repo = tmp_path / "rules-repo"
    subprocess.run(["cp", "-r", str(RULES), str(repo)], check=True)
    for args in (["init", "-q", "-b", "main"], ["add", "."],
                 ["-c", "user.name=t", "-c", "user.email=t@t",
                  "commit", "-q", "-m", "rules"]):
        subprocess.run(["git", "-C", str(repo), *args], check=True)
    monkeypatch.setenv(rules_cache.CACHE_ENV, str(tmp_path / "cache"))
    monkeypatch.delenv("USES_RULES_PATH", raising=False)
    monkeypatch.setattr(rules_cache, "REPO_URL", str(repo))
    return repo


def test_fetch_and_update(rules_repo):
    assert rules_cache.cached() is None
    path = rules_cache.fetch(url=str(rules_repo))
    assert (path / "rules" / "sample.yaml").is_file()
    assert rules_cache.cached() == path
    assert rules_cache.fetch(url=str(rules_repo)) == path


def test_fetch_error_is_readable(rules_repo, tmp_path):
    with pytest.raises(rules_cache.FetchError):
        rules_cache.fetch(url=str(tmp_path / "nowhere"))


def test_setup_then_certify_without_rules_option(rules_repo, project,
                                                 capsys):
    root = project({"a.py": 'def f():\n    """Doc."""\n'})
    assert main(["setup", str(root), "--min-level", "gold"]) == 0
    out = capsys.readouterr().out
    assert "Project level: Gold" in out and "Next steps" in out
    assert (root / "AGENTS.md").is_file()
    assert main(["certify", str(root)]) == 0


def test_guide_lists_rules_and_workflow(rulebook):
    text = guide.render(rulebook, "gold")
    assert "| T-001 | method | Complexity |" in text
    assert "| Gold | 95 | 0 | 0 |" in text
    assert "uses-certifier check" in text and "**gold**" in text
    assert "uses-certifier:start" not in text
    assert "#### DP-001 Command Query Separation" in text
    assert "**Check:** Does a method both change state" in text


def test_principles_do_not_change_the_rules_digest(tmp_path):
    import shutil
    from uses_certifier import config, rules
    copy = tmp_path / "rules"
    shutil.copytree(RULES, copy)
    before = rules.load(copy, config.ProjectConfig())
    shutil.rmtree(copy / "principles")
    after = rules.load(copy, config.ProjectConfig())
    assert before.principles and not after.principles
    assert before.digest == after.digest


def test_cli_guide(project, capsys):
    root = project({"a.py": "X = 1\n"})
    assert main(["guide", str(root), "--rules", str(RULES)]) == 0
    assert "## Rules in force" in capsys.readouterr().out


def test_guide_groups_principles_by_category(rulebook):
    text = guide.render(rulebook, "gold")
    assert "### Design and structure" in text
    assert "Partly measured by: T-001" in text
