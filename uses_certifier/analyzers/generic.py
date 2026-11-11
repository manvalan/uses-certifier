"""Analysis of other languages through lizard."""
import re

import lizard

from .. import suppressions
from ..hashing import lines_digest
from ..model import Entity
from .text import max_width, module_entity

SEPARATOR = re.compile(r"::|\.")


def supports(path):
    """True when lizard has a reader for the file extension."""
    return lizard.get_reader_for(str(path)) is not None


def language_of(path):
    """Language name according to lizard (e.g. java, cpp, javascript)."""
    reader = lizard.get_reader_for(str(path))
    return reader.language_names[0] if reader else "unknown"


def analyze(path, text, relpath):
    """Analyse a non-Python source and return the module element."""
    module = module_entity(text, relpath, language_of(path))
    result = lizard.analyze_file.analyze_source_code(str(path), text)
    lines = text.splitlines()
    functions = [_function(f, lines, module)
                 for f in result.function_list]
    module.children = _group_by_class(functions, module)
    return module


def _function(info, lines, module):
    """Function element from lizard's information."""
    span = lines[info.start_line - 1:info.end_line]
    return Entity(
        kind="function", name=SEPARATOR.split(info.name)[-1],
        qualname=info.name, language=module.language, path=module.path,
        first_line=info.start_line, start_line=info.start_line,
        end_line=info.end_line, source_hash=lines_digest(span),
        suppressions=suppressions.for_definition(
            lines, info.start_line, info.start_line),
        metrics={
            "cyclomatic_complexity": info.cyclomatic_complexity,
            "parameter_count": info.parameter_count,
            "length_lines": info.end_line - info.start_line + 1,
            "max_line_width": max_width(span),
        },
    )


def _group_by_class(functions, module):
    """Group methods under classes derived from their qualified names."""
    classes, top = {}, []
    for func in functions:
        owner = func.qualname[:-len(func.name)].rstrip(":.")
        if not owner:
            top.append(func)
            continue
        classes.setdefault(owner, []).append(func)
    return top + [_class(name, methods, module)
                  for name, methods in classes.items()]


def _class(qualname, methods, module):
    """Synthetic class element rebuilt from its methods."""
    start = min(m.start_line for m in methods)
    end = max(m.end_line for m in methods)
    return Entity(
        kind="class", name=SEPARATOR.split(qualname)[-1], qualname=qualname,
        language=module.language, path=module.path, first_line=start,
        start_line=start, end_line=end, synthetic=True,
        source_hash=lines_digest(m.source_hash for m in methods),
        children=methods,
        metrics={
            "method_count": len(methods),
            "weighted_complexity": sum(
                m.metrics["cyclomatic_complexity"] for m in methods),
            "length_lines": end - start + 1,
        },
    )
