"""Sphinx configuration for idl_parser."""

import os
import sys
from importlib.metadata import PackageNotFoundError, version as _pkg_version

# Allow building from a source checkout without installing the package.
sys.path.insert(0, os.path.abspath(".."))

project = "idl_parser"
author = "Yuki Suga"
copyright = "Yuki Suga"

try:
    release = _pkg_version("idl_parser")
except PackageNotFoundError:
    release = "unknown"
version = ".".join(release.split(".")[:3])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "member-order": "bysource",
}
autosummary_generate = True

exclude_patterns = ["_build"]

html_theme = "furo"
html_title = f"idl_parser {version}"
