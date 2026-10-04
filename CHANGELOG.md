# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-04

### Added

- `delimit`, `datamark` and `encode` (base64, hex, ROT13), the three spotlighting techniques from Hines et al. 2024 (arXiv 2403.14720), each with an exact inverse (`undelimit`, `reverse`, `decode`) and the matching system-prompt instruction.
- Datamarking that handles Unicode whitespace, CRLF and tabs, optional skipping of fenced code blocks, automatic marker choice (`marker="auto"`) and a round-trip check that refuses ambiguous markers.
- Delimiter collision handling: raise by default, `allow`, or `tag` with a content-derived tag.
- `spotlight()` entry point returning a frozen `Spotlighted` dataclass with `prompt(system, user_prefix)`, `block()` and `unmark()`.
- `Pipeline` for nested dicts, lists and tuples with `trusted_keys` and `trusted_paths` allowlists, one shared marker and instruction, and `restore()`.
- `for_tool_result`, `for_fetched_page` (standard library `html.parser`, drops scripts, styles, comments and hidden elements, no network) and `for_email`, each with a sanitised one-line provenance header.
- `spotlighting` command: `mark`, `unmark`, `instruction` and `demo`, text and JSON output.
- Container image `ghcr.io/basitalisandhu/spotlighting` for linux/amd64 and linux/arm64, published on version tags with an SPDX SBOM, a build provenance attestation and a keyless cosign signature; runs as uid 1000.
- CI on Python 3.11 and 3.12 with SHA-pinned actions, PyPI trusted publishing on tags (off until the repository variable `PYPI_PUBLISH` is set), `docs/demo.svg` rendered from `spotlighting demo`.

[Unreleased]: https://github.com/basitalisandhu/spotlighting/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/basitalisandhu/spotlighting/releases/tag/v0.1.0
