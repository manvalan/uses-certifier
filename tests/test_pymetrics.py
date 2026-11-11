import ast
import textwrap

from uses_certifier.analyzers import pymetrics


def metrics(code, is_method=False):
    node = ast.parse(textwrap.dedent(code)).body[0]
    return pymetrics.function_metrics(node, is_method)


def test_cyclomatic_complexity_counts_branches_and_boolean_operators():
    m = metrics("""
        def f(a, b):
            if a and b:
                return 1
            for x in a:
                while x:
                    x -= 1
            return [y for y in b if y]
    """)
    # 1 + if + and + for + while + comprehension + comprehension if
    assert m["cyclomatic_complexity"] == 7


def test_elif_does_not_increase_nesting():
    m = metrics("""
        def f(a):
            if a == 1:
                pass
            elif a == 2:
                pass
            elif a == 3:
                if a:
                    pass
    """)
    assert m["max_nesting"] == 2


def test_nesting_counts_try_with_and_loops():
    m = metrics("""
        def f(a):
            with a:
                try:
                    for x in a:
                        pass
                except ValueError:
                    pass
    """)
    assert m["max_nesting"] == 3


def test_method_parameters_exclude_self():
    m = metrics("def f(self, a, *args, b, **kw): pass", is_method=True)
    assert m["parameter_count"] == 4


def test_boolean_parameters():
    m = metrics("def f(a, b=True, *, c: bool, d=1): pass")
    assert m["boolean_parameters"] == 2


def test_activated_objects():
    m = metrics("""
        def f(self, a):
            b = a + self.x
            self.y = [z for z in b]
            self.helper()
            return b
    """, is_method=True)
    # a, b, self.x, self.y (non z, non self.helper)
    assert m["activated_objects"] == 4


def test_bare_except_and_returns():
    m = metrics("""
        def f():
            try:
                return 1
            except:
                return 2
    """)
    assert m["bare_except_count"] == 1
    assert m["return_count"] == 2


def test_field_count():
    node = ast.parse(textwrap.dedent("""
        class C:
            a: int
            b = 1
            def __init__(self):
                self.c = 1
                self.a = 2
    """)).body[0]
    assert pymetrics.field_count(node) == 3
