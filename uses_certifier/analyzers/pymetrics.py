"""Metriche calcolate sull'AST di funzioni e classi Python."""
import ast

BRANCHES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp,
            ast.ExceptHandler, ast.comprehension, ast.match_case)
BLOCKS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With,
          ast.AsyncWith, ast.Try, ast.Match)
NESTED_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
               ast.Lambda)
SELF_NAMES = ("self", "cls")


def function_metrics(node, is_method):
    """Tutte le metriche AST di una funzione."""
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
    """Complessità di McCabe: uno più ogni punto di decisione."""
    total = 1
    for child in ast.walk(node):
        if isinstance(child, BRANCHES):
            total += 1 + len(getattr(child, "ifs", []))
        elif isinstance(child, ast.BoolOp):
            total += len(child.values) - 1
    return total


def max_nesting(body, depth=0):
    """Profondità massima dei blocchi annidati (if, for, while, with, try)."""
    deepest = depth
    for stmt in body:
        if isinstance(stmt, NESTED_DEFS) or not isinstance(stmt, BLOCKS):
            continue
        for block in _blocks(stmt):
            deepest = max(deepest, max_nesting(block, depth + 1))
    return deepest


def _blocks(stmt):
    """Corpi annidati di un'istruzione composta (elif resta allo stesso
    livello dell'if)."""
    if isinstance(stmt, ast.If) and _is_elif(stmt.orelse):
        return [stmt.body] + _blocks(stmt.orelse[0])
    if isinstance(stmt, ast.Match):
        return [case.body for case in stmt.cases]
    return _bodies(stmt)


def _bodies(stmt):
    """Corpo, else, finally e gestori di eccezione non vuoti."""
    names = ("body", "orelse", "finalbody")
    found = [getattr(stmt, name, []) for name in names]
    found += [handler.body for handler in getattr(stmt, "handlers", [])]
    return [body for body in found if body]


def _is_elif(orelse):
    """Vero se il ramo else contiene solo un altro if (cioè un elif)."""
    return len(orelse) == 1 and isinstance(orelse[0], ast.If)


def activated_objects(node, params):
    """Parametri, variabili locali e campi di self usati dalla funzione.

    Non contano le variabili delle comprehension, che vivono solo
    nell'espressione, né le chiamate ai metodi di self.
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
    """Identità dei nomi usati come variabile di una comprehension."""
    return {id(name) for comp in ast.walk(node)
            if isinstance(comp, ast.comprehension)
            for name in ast.walk(comp.target)}


def _self_calls(node):
    """Identità delle espressioni self.metodo usate come chiamata."""
    return {id(call.func) for call in ast.walk(node)
            if isinstance(call, ast.Call) and _is_self_attribute(call.func)}


def field_count(node):
    """Campi della classe: attributi di classe e attributi di self assegnati."""
    fields = {t.id for stmt in node.body for t in _class_targets(stmt)}
    for child in ast.walk(node):
        if _is_self_attribute(child) and isinstance(child.ctx, ast.Store):
            fields.add(child.attr)
    return len(fields)


def _class_targets(stmt):
    """Nomi assegnati direttamente nel corpo della classe."""
    if isinstance(stmt, ast.AnnAssign):
        targets = [stmt.target]
    elif isinstance(stmt, ast.Assign):
        targets = stmt.targets
    else:
        targets = []
    return [t for t in targets if isinstance(t, ast.Name)]


def _is_self_attribute(node):
    """Vero per espressioni come self.campo."""
    return (isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in SELF_NAMES)


def _parameters(node, is_method):
    """Nomi dei parametri, escluso self o cls per i metodi."""
    args = node.args
    every = args.posonlyargs + args.args + args.kwonlyargs
    every += [a for a in (args.vararg, args.kwarg) if a]
    names = [a.arg for a in every]
    if is_method and names and names[0] in SELF_NAMES:
        names = names[1:]
    return names


def _boolean_parameters(node):
    """Parametri con default booleano o annotati come bool."""
    args = node.args
    positional = args.posonlyargs + args.args
    defaults = [None] * (len(positional) - len(args.defaults)) + args.defaults
    pairs = list(zip(positional, defaults))
    pairs += list(zip(args.kwonlyargs, args.kw_defaults))
    return sum(1 for arg, default in pairs if _is_boolean(arg, default))


def _is_boolean(arg, default):
    """Vero se il parametro è un flag booleano."""
    annotated = isinstance(arg.annotation, ast.Name) and \
        arg.annotation.id == "bool"
    defaulted = isinstance(default, ast.Constant) and \
        isinstance(default.value, bool)
    return annotated or defaulted


def _count(node, kind):
    """Numero di nodi di un certo tipo dentro la funzione."""
    return sum(1 for child in ast.walk(node) if isinstance(child, kind))
