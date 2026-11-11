from uses_certifier import analyzers, suppressions

PY = '''"""Modulo."""


class Shop:
    """Negozio."""

    # uses-cert: ignore[T-001]
    @property
    def total(self):
        return 1

    def add(self, item):
        def inner():
            return item
        return inner


def helper():
    pass
'''

JAVA = """
public class Cart {
    public int total(int a, int b) {
        if (a > b) { return a; }
        return b;
    }
    public void clear() { }
}
"""


def test_python_tree():
    module = analyzers.analyze("shop.py", PY, "shop.py")
    names = [(e.kind, e.qualname) for e in module.walk()]
    assert names == [
        ("module", "shop.py"), ("class", "Shop"),
        ("function", "Shop.total"), ("function", "Shop.add"),
        ("function", "helper"),
    ]
    shop = module.children[0]
    assert shop.metrics["method_count"] == 2
    assert shop.children[0].suppressions == {"T-001"}


def test_java_methods_grouped_by_class():
    module = analyzers.analyze("Cart.java", JAVA, "Cart.java")
    assert module.language == "java"
    cart = module.children[0]
    assert cart.kind == "class" and cart.name == "Cart"
    total = cart.children[0]
    assert total.metrics["cyclomatic_complexity"] == 2
    assert total.metrics["parameter_count"] == 2


def test_supported_extensions():
    assert analyzers.is_supported("a.py")
    assert analyzers.is_supported("a.cpp")
    assert not analyzers.is_supported("a.txt")


def test_directives():
    assert suppressions.parse_directive("# uses-cert: ignore") == (
        "ignore", {"*"})
    assert suppressions.parse_directive(
        "// uses-cert: ignore-file[A-001, B-002]") == (
        "ignore-file", {"A-001", "B-002"})
    assert suppressions.parse_directive("x = 1") is None
