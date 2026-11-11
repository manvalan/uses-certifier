"""uses-cert comment markers: suppression directives and stamp lines."""
import re

MARKER = re.compile(r"uses-cert:\s*(ignore-file|ignore|stamp-file|stamp)\b")
OPENERS = ("#", "//", "--", "/*", "%", "!", ";")
STAMP = re.compile(
    r"uses-cert:\s*(stamp-file|stamp)\s+([A-Za-z]+)\s+([0-9A-F-]+)")


def kind(line):
    """Marker kind on the line (ignore, stamp...) or None."""
    match = MARKER.search(line)
    return match.group(1) if match and _is_comment(line, match) else None


def _is_comment(line, match):
    """True when the marker sits in a comment.

    Stamps must be whole-line comments; ignore directives may also
    trail code, as in: x = f()  # uses-cert: ignore[CC-001]
    """
    before = line[:match.start()].rstrip()
    if match.group(1).startswith("stamp"):
        return before.strip() in OPENERS
    return any(before.endswith(opener) for opener in OPENERS)


def is_stamp(line):
    """True for a stamp line written by the certifier."""
    return kind(line) in ("stamp", "stamp-file")


def parse_stamp(line):
    """(kind, level, code) of a stamp line, or None."""
    match = STAMP.search(line)
    if not match or not is_stamp(line):
        return None
    return match.group(1), match.group(2).lower(), match.group(3)


def strip_stamps(text):
    """The source without stamp lines: what the certifier analyses."""
    lines = text.splitlines(keepends=True)
    return "".join(line for line in lines if not is_stamp(line))


def block_above(lines, first_line):
    """0-based index where the marker block right above a line begins."""
    index = first_line - 1
    while index > 0 and kind(lines[index - 1]):
        index -= 1
    return index


def line_map(text):
    """Original 1-based number of each line of the stamp-free source."""
    lines = text.splitlines()
    return [i + 1 for i, line in enumerate(lines) if not is_stamp(line)]
