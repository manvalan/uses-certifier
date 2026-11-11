"""Adds certification configuration and agent instructions to a project."""
import re
from importlib import resources
from pathlib import Path

from .config import FILENAME, STRICT

START, END = "<!-- uses-certifier:start -->", "<!-- uses-certifier:end -->"
SECTION = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)


def template(name, min_level, mode=STRICT):
    """Text of a bundled template with level and mode filled in."""
    text = resources.files(__package__).joinpath("templates", name)
    text = text.read_text(encoding="utf-8")
    return text.replace("{min_level}", min_level).replace("{mode}", mode)


def init_project(root, min_level, mode=STRICT):
    """Create or update the project files; yield (path, action).

    mode is strict for certified projects, migration for existing
    programs that are certified file by file.
    """
    root = Path(root)
    settings = template("uses-certifier.yaml", min_level, mode)
    yield _create(root / FILENAME, settings)
    section = template("agents-section.md", min_level)
    yield _merge_section(root / "AGENTS.md", section)
    yield _ensure_claude(root / "CLAUDE.md", template("CLAUDE.md", min_level))


def _create(path, text):
    """Write the file only when it does not exist yet."""
    if path.exists():
        return path, "kept"
    path.write_text(text, encoding="utf-8")
    return path, "created"


def _merge_section(path, section):
    """Add or replace the certification section of AGENTS.md."""
    if not path.exists():
        path.write_text("# Agent instructions\n\n" + section, "utf-8")
        return path, "created"
    text = path.read_text(encoding="utf-8")
    if START in text:
        updated = SECTION.sub(lambda _: section.strip(), text)
    else:
        updated = text.rstrip() + "\n\n" + section
    path.write_text(updated, encoding="utf-8")
    return path, "updated" if updated != text else "kept"


def _ensure_claude(path, text):
    """Make CLAUDE.md point Claude to AGENTS.md."""
    if not path.exists():
        path.write_text(text, encoding="utf-8")
        return path, "created"
    current = path.read_text(encoding="utf-8")
    if "AGENTS.md" in current:
        return path, "kept"
    path.write_text(current.rstrip() + "\n\n@AGENTS.md\n", encoding="utf-8")
    return path, "updated"
