"""Writing of stamp comments into the sources.

Every method and class gets a line such as

    # uses-cert: stamp <LEVEL> <CODE>

right above its definition (above decorators and ignore directives), and
every source file gets a stamp-file line at the top. Stamp lines are
removed before analysis, so writing them never changes a fingerprint.
"""
import re
from pathlib import Path

from . import markers

COMMENTS = {"python": "#", "ruby": "#", "perl": "#", "gdscript": "#",
            "lua": "--", "fortran": "!", "erlang": "%"}
HEADER = re.compile(r"^(#!|#.*coding[:=])")
# A line comment among JSX children is rendered as page text, so these
# sources keep no stamps; the JSON certificate still covers them.
UNSTAMPED_SUFFIXES = (".tsx", ".jsx")


def keeps_stamps(module):
    """False for sources where a stamp comment could change the program."""
    return not module.path.endswith(UNSTAMPED_SUFFIXES)


def comment_for(language):
    """Line comment opener of a language."""
    return COMMENTS.get(language, "//")


def stamp_line(entity, indent=""):
    """Stamp comment of an element, without newline."""
    marker = "stamp-file" if entity.kind == "module" else "stamp"
    return (f"{indent}{comment_for(entity.language)} uses-cert: {marker} "
            f"{entity.level.upper()} {entity.stamp}")


def stamped_text(original, module):
    """The source with its old stamps replaced by fresh ones.

    Element line numbers refer to the original text, stamps included.
    """
    stripped_of = {o: s for s, o in enumerate(markers.line_map(original), 1)}
    lines = markers.strip_stamps(original).splitlines(keepends=True)
    newline = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += newline
    for entity in sorted(_targets(module), key=lambda e: -e.first_line):
        _insert(lines, stripped_of[entity.first_line], entity, newline)
    lines.insert(_header_end(lines), stamp_line(module) + newline)
    return "".join(lines)


def _insert(lines, number, entity, newline):
    """Insert an element's stamp above its definition and directives."""
    line = lines[number - 1]
    indent = line[:len(line) - len(line.lstrip())]
    at = markers.block_above(lines, number)
    lines.insert(at, stamp_line(entity, indent) + newline)


def _targets(module):
    """Elements that get an inline stamp: real functions and classes."""
    return [e for e in module.walk()
            if e.kind != "module" and not e.synthetic]


def _header_end(lines):
    """Index after a shebang or encoding line, where the file stamp goes."""
    count = 0
    while count < min(len(lines), 2) and HEADER.match(lines[count]):
        count += 1
    return count


def write(path, module):
    """Rewrite a source with fresh stamps; True when the file changed."""
    path = Path(path)
    original = path.read_text(encoding="utf-8")
    if keeps_stamps(module):
        updated = stamped_text(original, module)
    else:
        updated = markers.strip_stamps(original)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True
