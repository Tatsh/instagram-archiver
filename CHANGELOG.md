<!-- markdownlint-configure-file {"MD024": { "siblings_only": true } } -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.1/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Rich-based live progress display (via the `archiver-stats` library) shown on stderr by default.
  Use `--quiet` to suppress it for non-interactive runs, or `--debug` to fall back to verbose logs.
- `--quiet` / `-q` flag on both `instagram-archiver` and `instagram-save-saved`.
- `--sleep-time` / `-S` flag (forwarded to yt-dlp) on both commands.
- Parallel downloads. Internally the scrapers now act as producers feeding a media worker, a
  comments worker (active only with `-C`), and a yt-dlp worker. Each worker performs at most one
  in-flight HTTP request, so concurrency is bounded but image, comment, and video work can overlap.
- SQLite dedup log for `instagram-save-saved`. The `.log.db` file is shared between both
  scrapers, so re-running `instagram-save-saved` against the same output directory now skips
  posts whose media URLs (and the per-post info call) have already been recorded. New
  `--no-log` flag on `instagram-save-saved` bypasses the log.

### Changed

- The whole HTTP layer is now asynchronous. The `requests` runtime dependency was replaced with
  `niquests` (`niquests.AsyncSession`); `yt-dlp-utils` is now consumed via its `[asyncio]` extra
  and `yt_dlp_utils.aio.AsyncYoutubeDL`.
- `InstagramClient`, `ProfileScraper`, and `SavedScraper` are now async context managers
  (`async with`). Their HTTP helpers and `process(...)` are coroutines.
- `setup_logging` now manages `niquests`, `urllib3`, `urllib3.util.retry`, and `yt_dlp_utils`
  loggers in addition to the package logger.
- yt-dlp output is silenced (`quiet`, `noprogress`, `no_warnings`) when the live display is
  active, so its `[download]` lines no longer interleave with the Rich panel.

## [0.3.5] - 2026-01-31

### Changed

- Use standard library `mimetypes` module to determine file extensions for media. Fixes issue
  #445.

## [0.3.4] - 2025-12-11

### Added

- Attestation.

## [0.3.3] - 2025-11-10

Release for testing the publishing process.

### Changed

- Increased upper bound of Python version requirement.

## [0.3.2] - 2025-05-14

### Fixed

- Handle when profile data lacks a `data` key. In this case, processing is likely to fail
  entirely.

## [0.3.1] - 2025-05-12

### Changed

- Use proper endpoint for fetching media information.
- Stop processing on first indication of being blocked (including when fetching videos).

## [0.3.0] - 2025-05-12

### Added

- Save saved posts (and unsave them too).

### Changed

- Main program is now named `instagram-archiver`.

### Fixed

- Back to working state.

## [0.2.1] - 2023-07-14

### Added

- `--print-query-hashes` debug option.
- Path support for `output_dir` argument.
- Python `-m` entry point (e.g. `python -m instagram_archiver`).
- Query hash discovery utilities.

### Changed

- Documentation and build configuration updates.
- Various dependency updates.

## [0.2.0] - 2023-06-23

### Changed

- Client logging improvements.

[unreleased]: https://github.com/Tatsh/instagram-archiver/compare/v0.3.5...HEAD
[0.3.5]: https://github.com/Tatsh/instagram-archiver/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/Tatsh/instagram-archiver/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/Tatsh/instagram-archiver/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/Tatsh/instagram-archiver/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/Tatsh/instagram-archiver/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Tatsh/instagram-archiver/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/Tatsh/instagram-archiver/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Tatsh/instagram-archiver/releases/tag/v0.2.0
