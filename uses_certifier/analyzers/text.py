"""Text metrics shared by every language."""
# uses-cert: ignore-file[CC-010] this file looks for exactly those words
import re

from .. import suppressions
from ..hashing import lines_digest
from ..model import Entity

TODO = re.compile(r"\b(TODO|FIXME|XXX)\b")


def max_width(lines):
    """Width of the longest line."""
    return max((len(line.rstrip("\r\n")) for line in lines), default=0)


def todo_count(lines):
    """Number of lines containing TODO, FIXME or XXX."""
    return sum(1 for line in lines if TODO.search(line))


def module_entity(text, relpath, language):
    """Element representing the whole source file."""
    lines = text.splitlines()
    return Entity(
        kind="module", name=relpath, qualname=relpath, language=language,
        path=relpath, first_line=1, start_line=1, end_line=len(lines),
        source_hash=lines_digest(lines),
        metrics={"length_lines": len(lines), "max_line_width":
                 max_width(lines), "todo_count": todo_count(lines)},
        suppressions=suppressions.file_ids(lines),
    )
