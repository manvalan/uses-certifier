"""Formati di uscita del certificatore."""
from . import console, markdown, sarif

FORMATS = {
    "console": console.render,
    "markdown": markdown.render,
    "sarif": sarif.render,
}
