<!-- markdownlint-configure-file {"MD024": { "siblings_only": true } } -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Use standard library `mimetypes` module to determine file extensions for media.

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

[unreleased]: https://github.com/Tatsh/instagram-archiver/compare/v0.3.4...HEAD
[0.3.4]: https://github.com/Tatsh/instagram-archiver/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/Tatsh/instagram-archiver/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/Tatsh/instagram-archiver/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/Tatsh/instagram-archiver/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/Tatsh/instagram-archiver/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/Tatsh/instagram-archiver/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Tatsh/instagram-archiver/releases/tag/v0.2.0
