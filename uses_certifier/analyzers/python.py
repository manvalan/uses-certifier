"""Analysis of Python sources through the AST."""
import ast

from .. import suppressions
from ..hashing import lines_digest
from ..model import Entity
from . import pymetrics
from .text import max_width, module_entity

DEFS = (ast.FunctionDef, ast.AsyncFunctionDef)


class _Source:
    """Source lines and relative path, shared during the analysis."""

    def __init__(self, text, relpath):
        self.lines = text.splitlines()
        self.relpath = relpath

    def span(self, node):
        """Lines of a node, from its definition to its last statement."""
        return self.lines[node.lineno - 1:node.end_lineno]

    def entity(self, node, kind, qualname):
        """Base element for a function or class node."""
        first = min([d.lineno for d in node.decorator_list] + [node.lineno])
        return Entity(
            kind=kind, name=node.name, qualname=qualname, language="python",
            path=self.relpath, first_line=first, start_line=node.lineno,
            end_line=node.end_lineno,
            source_hash=lines_digest(self.lines[first - 1:node.end_lineno]),
            suppressions=suppressions.for_definition(
                self.lines, first, node.lineno),
        )


def analyze(text, relpath):
    """Analyse a Python source and return the module element."""
    module = module_entity(text, relpath, "python")
    tree = ast.parse(text, filename=relpath)
    module.metrics["has_docstring"] = ast.get_docstring(tree) is not None
    module.metrics["commented_code_lines"] = pymetrics.commented_code_lines(
        text.splitlines())
    module.children = _children(tree, _Source(text, relpath), "")
    return module


def _children(node, src, prefix):
    """Function and class elements defined directly under a node."""
    found = []
    for child in ast.iter_child_nodes(node):
        qualname = prefix + getattr(child, "name", "")
        if isinstance(child, DEFS):
            found.append(_function(child, src, qualname, bool(prefix)))
        elif isinstance(child, ast.ClassDef):
            found.append(_class(child, src, qualname))
    return found


def _function(node, src, qualname, is_method):
    """Function element with its metrics."""
    entity = src.entity(node, "function", qualname)
    entity.metrics = pymetrics.function_metrics(node, is_method)
    entity.metrics["length_lines"] = node.end_lineno - node.lineno + 1
    entity.metrics["max_line_width"] = max_width(src.span(node))
    entity.body_hash = pymetrics.body_fingerprint(node)
    return entity


def _class(node, src, qualname):
    """Class element with its methods and metrics."""
    entity = src.entity(node, "class", qualname)
    entity.children = _children(node, src, qualname + ".")
    methods = [c for c in entity.children if c.kind == "function"]
    entity.metrics = {
        "length_lines": node.end_lineno - node.lineno + 1,
        "method_count": len(methods),
        "weighted_complexity": sum(
            m.metrics["cyclomatic_complexity"] for m in methods),
        "field_count": pymetrics.field_count(node),
        "has_docstring": ast.get_docstring(node) is not None,
    }
    return entity
