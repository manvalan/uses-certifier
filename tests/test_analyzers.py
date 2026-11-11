from uses_certifier import analyzers, markers, suppressions

PY = '''"""Module."""


class Shop:
    """Shop."""

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
    total = shop.children[0]
    assert total.suppressions == {"T-001"}
    assert (total.first_line, total.start_line) == (8, 9)


def test_python_type_alias_statement_is_skipped():
    text = "type Logger = int | None\n\n\ndef log():\n    pass\n"
    module = analyzers.analyze("alias.py", text, "alias.py")
    names = [(e.kind, e.qualname) for e in module.walk()]
    assert names == [("module", "alias.py"), ("function", "log")]


def test_java_methods_grouped_by_class():
    module = analyzers.analyze("Cart.java", JAVA, "Cart.java")
    assert module.language == "java"
    cart = module.children[0]
    assert cart.kind == "class" and cart.name == "Cart" and cart.synthetic
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
    assert suppressions.parse_directive(
        "x = f()  # uses-cert: ignore[A-001]") == ("ignore", {"A-001"})
    assert suppressions.parse_directive('s = "uses-cert: ignore"') is None
    assert suppressions.parse_directive("x = 1") is None


def test_stamp_lines():
    line = "    # uses-cert: stamp GOLD 7F3A-9C1E-2B4D-5A60"
    assert markers.parse_stamp(line) == ("stamp", "gold",
                                         "7F3A-9C1E-2B4D-5A60")
    assert markers.is_stamp("// uses-cert: stamp-file NONE 0000-1111")
    assert not markers.is_stamp('x = "# uses-cert: stamp GOLD 1"')
    text = "a\n# uses-cert: stamp GOLD 12\nb\n"
    assert markers.strip_stamps(text) == "a\nb\n"
    assert markers.line_map(text) == [1, 3]
