# instagram-archiver

[![Python versions](https://img.shields.io/pypi/pyversions/instagram-archiver.svg?color=blue&logo=python&logoColor=white)](https://www.python.org/)
[![PyPI - Version](https://img.shields.io/pypi/v/instagram-archiver)](https://pypi.org/project/instagram-archiver/)
[![GitHub tag (with filter)](https://img.shields.io/github/v/tag/Tatsh/instagram-archiver)](https://github.com/Tatsh/instagram-archiver/tags)
[![License](https://img.shields.io/github/license/Tatsh/instagram-archiver)](https://github.com/Tatsh/instagram-archiver/blob/master/LICENSE.txt)
[![GitHub commits since latest release (by SemVer including pre-releases)](https://img.shields.io/github/commits-since/Tatsh/instagram-archiver/v0.3.3/master)](https://github.com/Tatsh/instagram-archiver/compare/v0.3.3...master)
[![CodeQL](https://github.com/Tatsh/instagram-archiver/actions/workflows/codeql.yml/badge.svg)](https://github.com/Tatsh/instagram-archiver/actions/workflows/codeql.yml)
[![QA](https://github.com/Tatsh/instagram-archiver/actions/workflows/qa.yml/badge.svg)](https://github.com/Tatsh/instagram-archiver/actions/workflows/qa.yml)
[![Tests](https://github.com/Tatsh/instagram-archiver/actions/workflows/tests.yml/badge.svg)](https://github.com/Tatsh/instagram-archiver/actions/workflows/tests.yml)
[![Coverage Status](https://coveralls.io/repos/github/Tatsh/instagram-archiver/badge.svg?branch=master)](https://coveralls.io/github/Tatsh/instagram-archiver?branch=master)
[![Dependabot](https://img.shields.io/badge/Dependabot-enabled-blue?logo=dependabot)](https://github.com/dependabot)
[![Documentation Status](https://readthedocs.org/projects/instagram-archiver/badge/?version=latest)](https://instagram-archiver.readthedocs.org/?badge=latest)
[![mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://pre-commit.com/)
[![Poetry](https://img.shields.io/badge/Poetry-242d3e?logo=poetry)](https://python-poetry.org)
[![pydocstyle](https://img.shields.io/badge/pydocstyle-enabled-AD4CD3?logo=pydocstyle)](https://www.pydocstyle.org/)
[![pytest](https://img.shields.io/badge/pytest-enabled-CFB97D?logo=pytest)](https://docs.pytest.org)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Downloads](https://static.pepy.tech/badge/instagram-archiver/month)](https://pepy.tech/project/instagram-archiver)
[![Stargazers](https://img.shields.io/github/stars/Tatsh/instagram-archiver?logo=github&style=flat)](https://github.com/Tatsh/instagram-archiver/stargazers)
[![Prettier](https://img.shields.io/badge/Prettier-enabled-black?logo=prettier)](https://prettier.io/)

[![@Tatsh](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fpublic.api.bsky.app%2Fxrpc%2Fapp.bsky.actor.getProfile%2F%3Factor=did%3Aplc%3Auq42idtvuccnmtl57nsucz72&query=%24.followersCount&style=social&logo=bluesky&label=Follow+%40Tatsh)](https://bsky.app/profile/Tatsh.bsky.social)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Tatsh-black?logo=buymeacoffee)](https://buymeacoffee.com/Tatsh)
[![Libera.Chat](https://img.shields.io/badge/Libera.Chat-Tatsh-black?logo=liberadotchat)](irc://irc.libera.chat/Tatsh)
[![Mastodon Follow](https://img.shields.io/mastodon/follow/109370961877277568?domain=hostux.social&style=social)](https://hostux.social/@Tatsh)
[![Patreon](https://img.shields.io/badge/Patreon-Tatsh2-F96854?logo=patreon)](https://www.patreon.com/Tatsh2)

Save Instagram content you have access to.

## Installation

### Poetry

```shell
poetry add instagram-archiver
```

### Pip

```shell
pip install instagram-archiver
```

## Usage

```plain
Usage: instagram-archiver [OPTIONS] USERNAME

  Archive a profile's posts.

Options:
  -o, --output-dir DIRECTORY      Output directory.
  -b, --browser [brave|chrome|chromium|edge|opera|vivaldi|firefox|safari]
                                  Browser to read cookies from.
  -p, --profile TEXT              Browser profile.
  -d, --debug                     Enable debug output.
  --no-log                        Ignore log (re-fetch everything).
  -C, --include-comments          Also download all comments (extends download
                                  time significantly).
  -h, --help                      Show this message and exit.
```

Typical use:

```shell
instagram-archiver -o ~/instagram-backups/username username
```

### `instagram-save-saved`

This tool saves your saved posts (at `www.instagram.com/username/saved/all-posts`).

```plain
Usage: instagram-save-saved [OPTIONS]

  Archive your saved posts.

Options:
  -o, --output-dir DIRECTORY      Output directory.
  -b, --browser [brave|chrome|chromium|edge|opera|vivaldi|firefox|safari]
                                  Browser to read cookies from.
  -p, --profile TEXT              Browser profile.
  -d, --debug                     Enable debug output.
  -C, --include-comments          Also download all comments (extends download
                                  time significantly).
  -u, --unsave                    Unsave posts after successful archive.
  -h, --help                      Show this message and exit.
```

## Notes

The default output path is the username under the current working directory.

Videos are saved using yt-dlp and its respective configuration.
