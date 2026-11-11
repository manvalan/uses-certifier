"""Analisi dei sorgenti Python tramite AST."""
import ast

from .. import suppressions
from ..hashing import lines_digest
from ..model import Entity
from . import pymetrics
from .text import max_width, module_entity

DEFS = (ast.FunctionDef, ast.AsyncFunctionDef)


class _Source:
    """Righe del sorgente e percorso relativo, condivisi dall'analisi."""

    def __init__(self, text, relpath):
        self.lines = text.splitlines()
        self.relpath = relpath

    def span(self, node):
        """Righe di un nodo, dalla definizione all'ultima istruzione."""
        return self.lines[node.lineno - 1:node.end_lineno]

    def entity(self, node, kind, qualname):
        """Crea l'elemento base per un nodo funzione o classe."""
        first = min([d.lineno for d in node.decorator_list] + [node.lineno])
        return Entity(
            kind=kind, name=node.name, qualname=qualname, language="python",
            start_line=node.lineno, end_line=node.end_lineno,
            source_hash=lines_digest(self.lines[first - 1:node.end_lineno]),
            suppressions=suppressions.ids_in_range(
                self.lines, first - 1, node.lineno),
        )


def analyze(text, relpath):
    """Analizza un sorgente Python e restituisce l'elemento modulo."""
    module = module_entity(text, relpath, "python")
    tree = ast.parse(text, filename=relpath)
    module.metrics["has_docstring"] = ast.get_docstring(tree) is not None
    module.children = _children(tree, _Source(text, relpath), "")
    return module


def _children(node, src, prefix):
    """Elementi funzione e classe definiti direttamente sotto un nodo."""
    found = []
    for child in ast.iter_child_nodes(node):
        qualname = prefix + getattr(child, "name", "")
        if isinstance(child, DEFS):
            found.append(_function(child, src, qualname, bool(prefix)))
        elif isinstance(child, ast.ClassDef):
            found.append(_class(child, src, qualname))
    return found


def _function(node, src, qualname, is_method):
    """Elemento funzione con le sue metriche."""
    entity = src.entity(node, "function", qualname)
    entity.metrics = pymetrics.function_metrics(node, is_method)
    entity.metrics["length_lines"] = node.end_lineno - node.lineno + 1
    entity.metrics["max_line_width"] = max_width(src.span(node))
    return entity


def _class(node, src, qualname):
    """Elemento classe con i suoi metodi e le sue metriche."""
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
