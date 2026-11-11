"""Output formats of the certifier."""
from . import console, markdown, sarif

FORMATS = {
    "console": console.render,
    "markdown": markdown.render,
    "sarif": sarif.render,
}
