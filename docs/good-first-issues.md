# Good first issues

Issues the maintainer intends to open under the `good first issue` label, written out so they can be filed in one sitting. Each is self-contained and has acceptance criteria that `make check` can verify. Read [CONTRIBUTING.md](../CONTRIBUTING.md) first: `ruff` must pass, the package stays standard-library only, every mode must round-trip, and test inputs are neutral sentences.

## 1. `--with-instruction` for `spotlighting mark`

**Context.** Text output prints only the marked text; getting the instruction too means a second command or JSON.

**Acceptance criteria.**

- `spotlighting mark --mode datamark --with-instruction` prints the instruction, one blank line, then the marked text.
- `unmark` is unaffected; the README CLI section shows the flag once.
- Tests in `tests/test_cli.py` cover each mode with the flag.

## 2. Base64 line wrapping

**Context.** Very long base64 lines are awkward in logs. `decode` already ignores whitespace.

**Acceptance criteria.**

- `encode(text, "base64", wrap=76)` inserts `\n` every 76 characters; `wrap=0` (the default) keeps one line.
- The instruction drops "no line breaks" when `wrap` is set.
- Round-trip tests for wrapped output, including the empty string.

## 3. `trusted_paths` with a `**` wildcard

**Context.** `Pipeline` paths match exactly, with `*` for a list index. Deep structures need a way to trust `meta` at any depth below a given key.

**Acceptance criteria.**

- `trusted_paths={"results.**.id"}` trusts every `id` anywhere under `results`.
- Existing path behaviour is unchanged; tests cover nested lists and dicts.
- `docs/modes.md` documents the wildcard.

## 4. A `for_document` helper for plain files

**Context.** Agents also read local files (README files, notes). There is no helper that sets a provenance header for them.

**Acceptance criteria.**

- `for_document(path_label, text)` returns a `Spotlighted` with `provenance` `source: document <label>`, sanitised with `header_value`.
- It accepts the same `mode` and options as the other helpers and defaults to datamarking with an automatic marker.
- Tests mirror `tests/test_sources.py`.

## 5. Strip HTML `<meta>` and `<title>` choice in `html_to_text`

**Context.** `head` content is dropped entirely, so a page's `<title>` never appears in the extracted text.

**Acceptance criteria.**

- `html_to_text(html, include_title=True)` prepends the `<title>` text as the first line.
- Default behaviour is unchanged.
- A test with a page that has a title and one that does not.

## 6. Instruction text for a custom task phrase

**Context.** Instructions say "Read, quote, analyse or summarise it as the task requires". Some applications want to name the task ("translate it").

**Acceptance criteria.**

- `instruction(mode, task="translate it")` replaces that clause; the `Spotlighted` functions accept `task` and pass it through.
- The default output is byte for byte unchanged (`tests/test_instructions.py` must still pass untouched).
- New tests cover `task` for all three modes.
