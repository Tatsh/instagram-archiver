# instagram-archiver

<!-- WISWA-GENERATED-README:START -->

[![Python versions](https://img.shields.io/pypi/pyversions/instagram-archiver.svg?color=blue&logo=python&logoColor=white)](https://www.python.org/)
[![PyPI - Version](https://img.shields.io/pypi/v/instagram-archiver)](https://pypi.org/project/instagram-archiver/)
[![GitHub tag (with filter)](https://img.shields.io/github/v/tag/Tatsh/instagram-archiver)](https://github.com/Tatsh/instagram-archiver/tags)
[![License](https://img.shields.io/github/license/Tatsh/instagram-archiver)](https://github.com/Tatsh/instagram-archiver/blob/master/LICENSE.txt)
[![GitHub commits since latest release (by SemVer including pre-releases)](https://img.shields.io/github/commits-since/Tatsh/instagram-archiver/v0.4.0/master)](https://github.com/Tatsh/instagram-archiver/compare/v0.4.0...master)
[![CodeQL](https://github.com/Tatsh/instagram-archiver/actions/workflows/codeql.yml/badge.svg)](https://github.com/Tatsh/instagram-archiver/actions/workflows/codeql.yml)
[![QA](https://github.com/Tatsh/instagram-archiver/actions/workflows/qa.yml/badge.svg)](https://github.com/Tatsh/instagram-archiver/actions/workflows/qa.yml)
[![Tests](https://github.com/Tatsh/instagram-archiver/actions/workflows/tests.yml/badge.svg)](https://github.com/Tatsh/instagram-archiver/actions/workflows/tests.yml)
[![Coverage Status](https://coveralls.io/repos/github/Tatsh/instagram-archiver/badge.svg?branch=master)](https://coveralls.io/github/Tatsh/instagram-archiver?branch=master)
[![Dependabot](https://img.shields.io/badge/Dependabot-enabled-blue?logo=dependabot)](https://github.com/dependabot)
[![Documentation Status](https://readthedocs.org/projects/instagram-archiver/badge/?version=latest)](https://instagram-archiver.readthedocs.org/?badge=latest)
[![mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![uv](https://img.shields.io/badge/uv-261230?logo=astral)](https://docs.astral.sh/uv/)
[![pytest](https://img.shields.io/badge/pytest-zz?logo=Pytest&labelColor=black&color=black)](https://docs.pytest.org/en/stable/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Downloads](https://static.pepy.tech/badge/instagram-archiver/month)](https://pepy.tech/project/instagram-archiver)
[![Stargazers](https://img.shields.io/github/stars/Tatsh/instagram-archiver?logo=github&style=flat)](https://github.com/Tatsh/instagram-archiver/stargazers)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Prettier](https://img.shields.io/badge/Prettier-black?logo=prettier)](https://prettier.io/)

[![@Tatsh](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fpublic.api.bsky.app%2Fxrpc%2Fapp.bsky.actor.getProfile%2F%3Factor=did%3Aplc%3Auq42idtvuccnmtl57nsucz72&query=%24.followersCount&label=Follow+%40Tatsh&logo=bluesky&style=social)](https://bsky.app/profile/Tatsh.bsky.social)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Tatsh-black?logo=buymeacoffee)](https://buymeacoffee.com/Tatsh)
[![Libera.Chat](https://img.shields.io/badge/Libera.Chat-Tatsh-black?logo=liberadotchat)](irc://irc.libera.chat/Tatsh)
[![Mastodon Follow](https://img.shields.io/mastodon/follow/109370961877277568?domain=hostux.social&style=social)](https://hostux.social/@Tatsh)
[![Patreon](https://img.shields.io/badge/Patreon-Tatsh2-F96854?logo=patreon)](https://www.patreon.com/Tatsh2)

<!-- WISWA-GENERATED-README:STOP -->

Save Instagram content you have access to.

## Installation

```shell
pip install instagram-archiver
```

## Usage

```plain
Usage: instagram-archiver [OPTIONS] [USERNAME]

  Archive a profile (USERNAME) or your saved posts (--saved).

  Pass exactly one of: a USERNAME positional argument, or --saved/-s.

Options:
  -o, --output-dir DIRECTORY      Output directory. Defaults to the username
                                  (profile mode) or `.` (saved mode).
  -b, --browser [brave|chrome|chromium|edge|opera|vivaldi|firefox|safari]
                                  Browser to read cookies from.
  -p, --profile TEXT              Browser profile.
  -d, --debug                     Enable debug output.
  -q, --quiet                     Disable progress display updates.
  -S, --sleep-time INTEGER        Number of seconds yt-dlp waits between
                                  requests.
  --no-log                        Ignore log (re-fetch everything).
  -C, --include-comments          Also download all comments (extends download
                                  time significantly).
  -R, --include-child-comments    Also recursively download child (reply)
                                  comments. Implies --include-comments.
  -s, --saved                     Archive your saved posts instead of a
                                  profile (mutually exclusive with USERNAME).
  -u, --unsave                    Unsave posts after successful archive (only
                                  with --saved).
  -h, --help                      Show this message and exit.
```

Typical use:

```shell
instagram-archiver -o ~/instagram-backups/username username
instagram-archiver --saved -o ~/instagram-backups/saved
```

When neither `--debug` nor `--quiet` is passed, a Rich-based live progress
display (provided by the `archiver-stats` library) is shown on stderr. Pass
`--quiet` to disable it for non-interactive use, or `--debug` to see verbose
log output instead.

Downloads run concurrently using `niquests.AsyncSession` and
producer/consumer queues: one worker for media posts, one for comments
(when `-C` is passed), and one for yt-dlp video downloads. Each worker
handles at most one in-flight HTTP request at a time, which keeps Instagram
rate-limiting at bay while still overlapping image downloads with yt-dlp.

The dedup log lives at `<output_dir>/.log.db` and is honoured across runs in
both profile and `--saved` modes. Pass `--no-log` to bypass it and re-fetch
everything.

## Notes

The default output path is the username under the current working directory.

Videos are saved using yt-dlp and its respective configuration.

In profile mode, both image and video items in the user's highlights and currently-active stories
are archived. Image story items go through the same media pipeline as posts, while video items
are handed to yt-dlp.
