"""Fixture comuni dei test."""
import textwrap
from pathlib import Path

import pytest

from uses_certifier import config, rules

RULES = Path(__file__).parent / "fixtures" / "rules"


@pytest.fixture
def rulebook():
    """Regole di prova."""
    return rules.load(RULES, config.ProjectConfig())


@pytest.fixture
def project(tmp_path):
    """Crea file in una cartella temporanea: project({'a.py': '...'})."""
    def make(files):
        for name, text in files.items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(textwrap.dedent(text), encoding="utf-8")
        return tmp_path
    return make
