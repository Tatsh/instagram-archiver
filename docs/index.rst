Instagram Archiver
==================

.. only:: html

   .. image:: https://img.shields.io/pypi/pyversions/instagram-archiver.svg?color=blue&logo=python&logoColor=white
      :target: https://www.python.org/
      :alt: Python versions

   .. image:: https://img.shields.io/pypi/v/instagram-archiver
      :target: https://pypi.org/project/instagram-archiver/
      :alt: PyPI Version

   .. image:: https://img.shields.io/github/v/tag/Tatsh/instagram-archiver
      :target: https://github.com/Tatsh/instagram-archiver/tags
      :alt: GitHub tag (with filter)

   .. image:: https://img.shields.io/github/license/Tatsh/instagram-archiver
      :target: https://github.com/Tatsh/instagram-archiver/blob/master/LICENSE.txt
      :alt: License

   .. image:: https://img.shields.io/github/commits-since/Tatsh/instagram-archiver/v0.3.3/master
      :target: https://github.com/Tatsh/instagram-archiver/compare/v0.3.3...master
      :alt: GitHub commits since latest release (by SemVer including pre-releases)

   .. image:: https://github.com/Tatsh/instagram-archiver/actions/workflows/codeql.yml/badge.svg
      :target: https://github.com/Tatsh/instagram-archiver/actions/workflows/codeql.yml
      :alt: CodeQL

   .. image:: https://github.com/Tatsh/instagram-archiver/actions/workflows/qa.yml/badge.svg
      :target: https://github.com/Tatsh/instagram-archiver/actions/workflows/qa.yml
      :alt: QA

   .. image:: https://github.com/Tatsh/instagram-archiver/actions/workflows/tests.yml/badge.svg
      :target: https://github.com/Tatsh/instagram-archiver/actions/workflows/tests.yml
      :alt: Tests

   .. image:: https://coveralls.io/repos/github/Tatsh/instagram-archiver/badge.svg?branch=master
      :target: https://coveralls.io/github/Tatsh/instagram-archiver?branch=master
      :alt: Coverage Status

   .. image:: https://readthedocs.org/projects/instagram-archiver/badge/?version=latest
      :target: https://instagram-archiver.readthedocs.org/?badge=latest
      :alt: Documentation Status

   .. image:: https://www.mypy-lang.org/static/mypy_badge.svg
      :target: http://mypy-lang.org/
      :alt: mypy

   .. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
      :target: https://github.com/pre-commit/pre-commit
      :alt: pre-commit

   .. image:: https://img.shields.io/badge/pydocstyle-enabled-AD4CD3
      :target: http://www.pydocstyle.org/en/stable/
      :alt: pydocstyle

   .. image:: https://img.shields.io/badge/pytest-zz?logo=Pytest&labelColor=black&color=black
      :target: https://docs.pytest.org/en/stable/
      :alt: pytest

   .. image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
      :target: https://github.com/astral-sh/ruff
      :alt: Ruff

   .. image:: https://static.pepy.tech/badge/instagram-archiver/month
      :target: https://pepy.tech/project/instagram-archiver
      :alt: Downloads

   .. image:: https://img.shields.io/github/stars/Tatsh/instagram-archiver?logo=github&style=flat
      :target: https://github.com/Tatsh/instagram-archiver/stargazers
      :alt: Stargazers

   .. image:: https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fpublic.api.bsky.app%2Fxrpc%2Fapp.bsky.actor.getProfile%2F%3Factor%3Ddid%3Aplc%3Auq42idtvuccnmtl57nsucz72%26query%3D%24.followersCount%26style%3Dsocial%26logo%3Dbluesky%26label%3DFollow%2520%40Tatsh&query=%24.followersCount&style=social&logo=bluesky&label=Follow%20%40Tatsh
      :target: https://bsky.app/profile/Tatsh.bsky.social
      :alt: Follow @Tatsh

   .. image:: https://img.shields.io/mastodon/follow/109370961877277568?domain=hostux.social&style=social
      :target: https://hostux.social/@Tatsh
      :alt: Mastodon Follow

Commands
--------

.. click:: instagram_archiver.main:main
  :prog: instagram-archiver
  :nested: full

.. code-block:: shell

   instagram-archiver -o ~/instagram-backups username

The default output path is the username under the current working directory.

Videos are saved using yt-dlp and its respective configuration.

.. click:: instagram_archiver.main:save_saved_main
   :prog: instagram-save-saved
   :nested: full

.. only:: html

   Library
   -------
   .. automodule:: instagram_archiver.client
      :members:

   .. automodule:: instagram_archiver.profile_scraper
      :members:

   .. automodule:: instagram_archiver.saved_scraper
      :members:

   Constants
   ---------
   .. automodule:: instagram_archiver.constants
      :members:

   Typing
   ------
   .. automodule:: instagram_archiver.typing
      :members:

   Utilities
   ---------
   .. automodule:: instagram_archiver.utils
      :members:
      :exclude-members: setup_logging

   .. toctree::
      :maxdepth: 2
      :caption: Contents:

Indices and tables
------------------
* :ref:`genindex`
* :ref:`modindex`
