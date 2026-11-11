import ast
import textwrap

from uses_certifier import certifier, config
from uses_certifier.analyzers import pymetrics
from uses_certifier.signing import Signer

BODY = '''
    """Doc {n}."""
    total = 0
    for item in items:
        if item.valid:
            total += item.price
    return total
'''


def func(name, n=1):
    return f"def {name}(items):" + BODY.format(n=n)


def certify(root, rulebook):
    return certifier.certify(root, rulebook, config.ProjectConfig(),
                             Signer())


def counts(cert):
    return {e.qualname: e.metrics["duplicate_count"]
            for e in cert.entities() if e.kind == "function"}


def test_same_body_in_two_files_is_duplicated(project, rulebook):
    root = project({"a.py": func("one", 1),
                    "b.py": "# other\n" + func("two", 2),
                    "c.py": func("short").split("total = 0")[0] + "pass\n"})
    assert counts(certify(root, rulebook)) == {
        "one": 1, "two": 1, "short": 0}


def test_formatting_does_not_hide_copies(project, rulebook):
    other = func("two").replace("total += item.price",
                                "total += (item.price)  # sum")
    root = project({"a.py": func("one"), "b.py": other})
    assert counts(certify(root, rulebook)) == {"one": 1, "two": 1}


def test_java_duplicates(project, rulebook):
    body = "{\n  int s = 0;\n  for (int i : a) {\n    s += i;\n  }\n" \
           "  return s;\n}\n"
    code = "class A {\n  int f(int[] a) " + body + \
           "  int g(int[] a) " + body + "}\n"
    cert = certify(project({"A.java": code}), rulebook)
    assert set(counts(cert).values()) == {1}


def test_commented_code_lines():
    lines = textwrap.dedent("""
        # x = compute(y)
        # print(total)
        # import os
        # This explains why we do it.
        # coding: utf-8
        # see foo() for details
        # type: ignore
        # uses-cert: ignore[CC-001] reason
        value = 1  # trailing comment = fine
    """).splitlines()
    assert pymetrics.commented_code_lines(lines) == 3


def test_short_functions_have_no_fingerprint():
    node = ast.parse("def f():\n    return 1\n").body[0]
    assert pymetrics.body_fingerprint(node) == ""
