"""Detection of duplicated function bodies across the project (DRY)."""
from collections import defaultdict


def mark(modules):
    """Set duplicate_count on every function: how many other functions in
    the project have the same body fingerprint."""
    groups = defaultdict(list)
    functions = [e for m in modules for e in m.walk()
                 if e.kind == "function"]
    for function in functions:
        if function.body_hash:
            groups[function.body_hash].append(function)
    for function in functions:
        copies = groups.get(function.body_hash, [function])
        function.metrics["duplicate_count"] = len(copies) - 1
