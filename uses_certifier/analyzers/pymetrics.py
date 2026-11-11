"""Metrics computed on the AST of Python functions and classes."""
import ast

from .. import markers
from ..hashing import digest

BRANCHES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp,
            ast.ExceptHandler, ast.comprehension, ast.match_case)
BLOCKS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With,
          ast.AsyncWith, ast.Try, ast.Match)
NESTED_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
               ast.Lambda)
SELF_NAMES = ("self", "cls")


def function_metrics(node, is_method):
    """Every AST metric of a function."""
    params = _parameters(node, is_method)
    return {
        "cyclomatic_complexity": cyclomatic_complexity(node),
        "parameter_count": len(params),
        "boolean_parameters": _boolean_parameters(node),
        "max_nesting": max_nesting(node.body),
        "activated_objects": activated_objects(node, params),
        "return_count": _count(node, ast.Return),
        "bare_except_count": sum(
            1 for n in ast.walk(node)
            if isinstance(n, ast.ExceptHandler) and n.type is None),
        "has_docstring": ast.get_docstring(node) is not None,
    }


def cyclomatic_complexity(node):
    """McCabe complexity: one plus every decision point."""
    total = 1
    for child in ast.walk(node):
        if isinstance(child, BRANCHES):
            total += 1 + len(getattr(child, "ifs", []))
        elif isinstance(child, ast.BoolOp):
            total += len(child.values) - 1
    return total


def max_nesting(body, depth=0):
    """Maximum depth of nested blocks (if, for, while, with, try)."""
    deepest = depth
    for stmt in body:
        if isinstance(stmt, NESTED_DEFS) or not isinstance(stmt, BLOCKS):
            continue
        for block in _blocks(stmt):
            deepest = max(deepest, max_nesting(block, depth + 1))
    return deepest


def _blocks(stmt):
    """Nested bodies of a compound statement (elif stays at the level of
    its if)."""
    if isinstance(stmt, ast.If) and _is_elif(stmt.orelse):
        return [stmt.body] + _blocks(stmt.orelse[0])
    if isinstance(stmt, ast.Match):
        return [case.body for case in stmt.cases]
    return _bodies(stmt)


def _bodies(stmt):
    """Non-empty body, else, finally and exception handlers."""
    names = ("body", "orelse", "finalbody")
    found = [getattr(stmt, name, []) for name in names]
    found += [handler.body for handler in getattr(stmt, "handlers", [])]
    return [body for body in found if body]


def _is_elif(orelse):
    """True when the else branch holds only another if (an elif)."""
    return len(orelse) == 1 and isinstance(orelse[0], ast.If)


def activated_objects(node, params):
    """Parameters, local variables and self fields used by the function.

    Comprehension variables, which live only inside their expression, and
    calls to self methods do not count.
    """
    names = set(params)
    skipped = _comprehension_targets(node) | _self_calls(node)
    for child in ast.walk(node):
        if id(child) in skipped:
            continue
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
            names.add(child.id)
        elif _is_self_attribute(child):
            names.add("self." + child.attr)
    return len(names)


def _comprehension_targets(node):
    """Identities of names used as comprehension variables."""
    return {id(name) for comp in ast.walk(node)
            if isinstance(comp, ast.comprehension)
            for name in ast.walk(comp.target)}


def _self_calls(node):
    """Identities of self.method expressions used as calls."""
    return {id(call.func) for call in ast.walk(node)
            if isinstance(call, ast.Call) and _is_self_attribute(call.func)}


def field_count(node):
    """Class fields: class attributes and assigned self attributes."""
    fields = {t.id for stmt in node.body for t in _class_targets(stmt)}
    for child in ast.walk(node):
        if _is_self_attribute(child) and isinstance(child.ctx, ast.Store):
            fields.add(child.attr)
    return len(fields)


def _class_targets(stmt):
    """Names assigned directly in the class body."""
    if isinstance(stmt, ast.AnnAssign):
        targets = [stmt.target]
    elif isinstance(stmt, ast.Assign):
        targets = stmt.targets
    else:
        targets = []
    return [t for t in targets if isinstance(t, ast.Name)]


def _is_self_attribute(node):
    """True for expressions such as self.field."""
    return (isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in SELF_NAMES)


def _parameters(node, is_method):
    """Parameter names, without self or cls for methods."""
    args = node.args
    every = args.posonlyargs + args.args + args.kwonlyargs
    every += [a for a in (args.vararg, args.kwarg) if a]
    names = [a.arg for a in every]
    if is_method and names and names[0] in SELF_NAMES:
        names = names[1:]
    return names


def _boolean_parameters(node):
    """Parameters with a boolean default or annotated as bool."""
    args = node.args
    positional = args.posonlyargs + args.args
    defaults = [None] * (len(positional) - len(args.defaults)) + args.defaults
    pairs = list(zip(positional, defaults))
    pairs += list(zip(args.kwonlyargs, args.kw_defaults))
    return sum(1 for arg, default in pairs if _is_boolean(arg, default))


def _is_boolean(arg, default):
    """True when the parameter is a boolean flag."""
    annotated = isinstance(arg.annotation, ast.Name) and \
        arg.annotation.id == "bool"
    defaulted = isinstance(default, ast.Constant) and \
        isinstance(default.value, bool)
    return annotated or defaulted


def _count(node, kind):
    """Number of nodes of a given type inside the function."""
    return sum(1 for child in ast.walk(node) if isinstance(child, kind))


MIN_DUPLICATE_LINES = 6
CODE_STATEMENTS = (ast.Assign, ast.AugAssign, ast.Return, ast.Import,
                   ast.ImportFrom, ast.Raise, ast.Delete, ast.For,
                   ast.While, ast.If, ast.With, ast.Try)


def body_fingerprint(node):
    """Fingerprint of a function body (without docstring) on its syntax
    tree, or "" when the function is too short to count as duplication."""
    if node.end_lineno - node.lineno + 1 < MIN_DUPLICATE_LINES:
        return ""
    body = node.body
    if ast.get_docstring(node) is not None:
        body = body[1:]
    return digest(ast.dump(ast.Module(body=body, type_ignores=[])))


def commented_code_lines(lines):
    """Number of comment lines that contain Python code."""
    return sum(1 for line in lines if _is_commented_code(line.strip()))


def _is_commented_code(text):
    """True for a full-line comment whose content parses as a statement."""
    if not text.startswith("#") or markers.kind(text):
        return False
    try:
        tree = ast.parse(text.lstrip("#").strip())
    except SyntaxError:
        return False
    return any(_is_code(statement) for statement in tree.body)


def _is_code(statement):
    """True for statements that are clearly code, not prose."""
    if isinstance(statement, ast.Expr):
        return isinstance(statement.value, ast.Call)
    return isinstance(statement, CODE_STATEMENTS)
