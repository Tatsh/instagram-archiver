"""See https://www.sphinx-doc.org/en/master/usage/configuration.html"""
from datetime import UTC, datetime
from operator import itemgetter
from pathlib import Path
from typing import Final
import sys

import tomlkit

with (Path(__file__).parent.parent / 'pyproject.toml').open() as f:
    poetry = tomlkit.load(f).unwrap()['tool']['poetry']
    authors, name, version = itemgetter('authors', 'name', 'version')(poetry)
# region Path setup
# If extensions (or modules to document with autodoc) are in another directory, add these
# directories to sys.path here. If the directory is relative to the documentation root, use
# str(Path().parent.parent) to make it absolute, like shown here.
sys.path.insert(0, str(Path(__file__).parent.parent))
# endregion
author: Final[str] = authors[0]
copyright: Final[str] = str(datetime.now(UTC).year)  # noqa: A001
project: Final[str] = name
release: Final[str] = f'v{version}'
extensions: Final[list[str]] = (['sphinx.ext.autodoc', 'sphinx.ext.napoleon'] +
                                (['sphinx_click'] if poetry.get('scripts') else []))
exclude_patterns: Final[list[str]] = []
master_doc: Final[str] = 'index'
html_static_path: Final[list[str]] = []
html_theme: Final[str] = 'sphinxdoc'
templates_path: Final[list[str]] = ['_templates']
