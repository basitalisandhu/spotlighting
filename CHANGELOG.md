# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.4.0] - 2026-10-28

### Added

- `spotlighting mark-json` marks every untrusted string in a JSON document from the shell, with `--trusted-key` and `--trusted-path` allowlists, one instruction for the whole document and the marked paths; `spotlighting unmark-json` reverses it.
- Troubleshooting section in the README with the real error messages and their fixes.
- Seeded, time-bounded fuzz tests over every command's input reader, scaling tests (ten times the input, held near linear) and an end-to-end test that installs the built wheel in a fresh venv and runs the README quick start, in CI.

### Fixed

- `unmark --format json` crashed with a traceback on JSON with the wrong types (a number for `text`, a list for `marker`), on `NaN`, and on very deeply nested input. It now exits 2 with a message that names the file or `stdin`.
- `Pipeline.apply` and `PipelineResult.restore` hit `RecursionError` on structures nested thousands of levels deep and on a list that contains itself; they now raise `SpotlightError`. Shared, non-cyclic sub-structures still work.
- `spotlighting instruction --mode datamark --marker ""` printed an instruction for an empty marker; it now exits 1 like `mark`.
- A lone surrogate in `unmark` output ended in a `UnicodeEncodeError` traceback; it is now a one-line error with exit 1.
- Non-UTF-8 input errors now name the file.

## [0.3.0] - 2026-10-16

### Added

- `spotlighting mark --with-instruction` prints the instruction, one blank line, then the marked text, so one command gives both (#1).
- Property-based round-trip tests (Hypothesis) for every mode, the automatic marker, fenced code, `Pipeline.restore()` and lone surrogates.

### Fixed

- `encode` with base64 or hex raised `UnicodeEncodeError` on text containing a lone surrogate (for example text decoded with `errors="surrogateescape"` or JSON with an unpaired `\ud800` escape). Encoding and decoding now use `surrogatepass`, so the round trip is exact.

## [0.2.0] - 2026-10-09

### Added

- `task` option on `instruction`, `delimit`, `datamark`, `encode` and `spotlight` to name the application's task in the instruction; default output unchanged.

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

[Unreleased]: https://github.com/basitalisandhu/spotlighting/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/basitalisandhu/spotlighting/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/basitalisandhu/spotlighting/releases/tag/v0.1.0
