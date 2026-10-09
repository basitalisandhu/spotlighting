# Spotlighting for prompt injection defence in Python

**spotlighting marks untrusted text before it reaches a model, with delimiting, datamarking and encoding as described in the Microsoft Research paper, plus the system-prompt instructions that go with each mode, so an agent can tell data from instructions.**

[![CI](https://github.com/basitalisandhu/spotlighting/actions/workflows/ci.yml/badge.svg)](https://github.com/basitalisandhu/spotlighting/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

![spotlighting demo: one neutral paragraph shown delimited, datamarked and base64 encoded, each with its instruction](docs/demo.svg)

## What it is, who it is for, and why

**What.** A small Python library and command that transform untrusted text (a tool result, a fetched web page, an email) so a model can see where it starts and ends, and that give you the matching sentence for the system prompt. It implements the three spotlighting techniques from Hines et al., [Defending Against Indirect Prompt Injection Attacks With Spotlighting](https://arxiv.org/abs/2403.14720) (Microsoft, 2024): delimiting, datamarking and encoding. Every transformation has an exact inverse, so you can always show or log the original. Standard library only, Python 3.11 or newer, typed.

**For whom.** People building agents and retrieval pipelines in Python who put text they did not write into a prompt, and who want the paper's technique without writing the string handling, the edge cases (Unicode whitespace, CRLF, code blocks, markers that already occur in the text) and the instruction text themselves.

**Why.** Indirect prompt injection works because a model receives trusted instructions and untrusted content as one stream of tokens. Spotlighting gives the untrusted part a continuous, visible signal of where it came from. The paper reports that datamarking and encoding cut attack success substantially in its experiments, while delimiting alone is easy to get around. The technique is simple, but the details decide whether it round-trips and whether the instruction matches the marking; this library gets those details right once and tests them.

## Install

Requires Python 3.11 or newer. Until the package is on PyPI, install from the repository:

```bash
pipx install git+https://github.com/basitalisandhu/spotlighting            # the spotlighting command
python3 -m pip install git+https://github.com/basitalisandhu/spotlighting  # the library
```

pip, once published to PyPI:

```bash
pip install spotlighting
```

Container image for the CLI: each release tag publishes `ghcr.io/basitalisandhu/spotlighting` for linux/amd64 and linux/arm64 (runs as uid 1000, working directory `/work`):

```bash
echo "The build passed on all platforms." | docker run --rm -i ghcr.io/basitalisandhu/spotlighting:0.1.0 mark --mode datamark
docker run --rm -v "$PWD:/work:ro" ghcr.io/basitalisandhu/spotlighting:0.1.0 mark --mode encode page.txt
```

The image is signed with a keyless cosign signature and carries a build provenance attestation and an SPDX SBOM (attached to the GitHub Release):

```bash
cosign verify ghcr.io/basitalisandhu/spotlighting:0.1.0 \
  --certificate-identity-regexp '^https://github.com/basitalisandhu/spotlighting/\.github/workflows/publish-github-packages\.yml@refs/tags/v' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
gh attestation verify oci://ghcr.io/basitalisandhu/spotlighting:0.1.0 --repo basitalisandhu/spotlighting
```

## Quickstart

```python
from spotlighting import for_tool_result

result = for_tool_result("search", tool_output_text)  # datamarking by default
prompt = result.prompt("You answer questions about the user's files.", "Tool output:")
messages = prompt.as_messages()  # the system message carries the instruction
original = result.unmark()  # the exact original text, for display or logs
```

`result.text` is the marked text, `result.instruction` the sentence for the system prompt, and `result.provenance` a one-line header (`source: tool search`).

For a specific application task, pass trusted wording such as
`spotlight(text, task="translate it")` or `instruction("encode", task="translate it")`.
The same keyword is available on `delimit`, `datamark` and `encode`.
It changes the task clause, not the transformed text or its untrusted-data restrictions.
Keep this option in trusted application configuration, not in retrieved content.
Omitting it (or passing `None`) preserves the default output exactly.

From the shell:

```bash
spotlighting mark --mode datamark notes.txt          # marked text on stdout
spotlighting mark --mode encode --format json < page.txt   # marked text plus instruction as JSON
spotlighting instruction --mode datamark             # just the system-prompt sentence
spotlighting demo                                    # the three modes on a neutral paragraph
```

## When to use this

- **How do I apply spotlighting or datamarking to tool output in Python?** `for_tool_result(name, content)` or `spotlight(text, mode="datamark")`; put `result.instruction` in the system prompt and `result.text` where the content goes.
- **I put a whole JSON tool result into the prompt. How do I mark only the untrusted fields?** `Pipeline(trusted_keys={"id", "status"}).apply(result_dict)` marks every other string, picks one marker for the whole structure and returns one instruction.
- **My agent reads web pages.** `for_fetched_page(url, html)` strips the page to its visible text with the standard library parser (scripts, styles, comments and elements hidden with `hidden`, `aria-hidden` or an inline `display: none` are dropped) and marks it. It makes no request; pass the HTML you already fetched.
- **My agent reads email.** `for_email(subject, body, sender)` marks the subject together with the body, since both are written by the sender, and keeps the sender in a sanitised one-line header.
- **Fenced code in documentation should stay readable.** `datamark(text, skip_code=True)` leaves ```` ``` ```` and `~~~` blocks unmarked and says so in the instruction.
- **I want to see what the model sees.** `spotlighting demo`, or `spotlighting mark --format json`, prints the marked text with its instruction.

## The three modes and their trade-offs

All quotations are from Hines et al. 2024, <https://arxiv.org/abs/2403.14720>. Model names are left out here; the paper names the models it tested. [docs/modes.md](docs/modes.md) has the exact output format of each mode.

| Mode | What it does | What the paper says | When to pick it |
|---|---|---|---|
| `delimit` | Wraps the text in a start and end marker, `<<` and `>>` by default. | Easy to bypass: text that contains the delimiters can close the block early, and the authors write that they "do not recommend using delimiting in practice". | Only with delimiters the text cannot contain. `on_collision="tag"` adds a tag derived from the text's own SHA-256 to both delimiters; the default raises an error when the text contains a delimiter. |
| `datamark` | Replaces every space with a marker (`^` by default) and puts the marker before every other whitespace character, so the marking runs through the whole text. | On the benchmarks the authors ran, "the presence of the datamarking transformation does not have any detrimental impact on task performance". They suggest a private-use character such as U+E000 as a marker that ordinary text does not contain. They also note a limitation: a stretch of text with no spaces gets no markers inside it. | The default. Use `marker="auto"` to pick a marker the text does not contain, or a private-use character. |
| `encode` | Encodes the text with base64 (default), hex or ROT13 and tells the model to decode it. | Encoding works well with the most capable model tested, but on a less capable one "the decoding process occasionally is accompanied by mistakes or hallucinations that impair task performance". The authors recommend encoding only with the highest-capacity models and validating task performance for your use case. They also point out that a simple cipher such as ROT13 can be worked around by text written so that its ROT13 form is what the writer wants the model to read. | Large, capable models where you have measured task quality. Prefer base64; ROT13 is offered for experiments only. |

**Encoding degrades model comprehension for smaller models.** That is the paper's finding, stated above in its own words; measure your own task before you ship `encode`.

The authors are also candid about mechanism: "we lack a clear understanding of why spotlighting actually helps". Treat it as a measured mitigation, not a proof.

### Spotlighting in a hosted service

Microsoft offers spotlighting as a preview option of Prompt Shields for document attacks in Azure AI Content Safety and Foundry ([Prompt Shields documentation](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/jailbreak-detection), as read on 2026-10-04). The page says the service transforms document content with base64 encoding, that the option is off by default, that it is available only for models used through the Chat Completions API, that base64 increases the number of document tokens (which can raise cost or push a long document past the input limit), and that the model may mention that the content is base64 encoded. This library does the same kind of transformation locally, for any model and any API, and lets you choose datamarking instead of encoding.

## API

| Function | Returns | Notes |
|---|---|---|
| `delimit(text, *, start="<<", end=">>", on_collision="error")` | `Spotlighted` | `on_collision`: `error`, `allow`, `tag` |
| `datamark(text, *, marker="^", skip_code=False, on_collision="error")` | `Spotlighted` | `marker="auto"` or `on_collision="auto"` picks a free marker |
| `encode(text, scheme="base64")` | `Spotlighted` | schemes `base64`, `hex`, `rot13` |
| `spotlight(text, mode="datamark", **options)` | `Spotlighted` | one entry point for the three modes |
| `undelimit`, `reverse`, `decode`, `unmark`, `unmark_text` | `str` | exact inverses |
| `instruction(mode, **options)` | `str` | the instruction alone |
| `Pipeline(mode, trusted_keys=..., trusted_paths=...).apply(obj)` | `PipelineResult` | `.value`, `.instruction`, `.paths`, `.restore()` |
| `for_tool_result(name, content)`, `for_fetched_page(url, html_text)`, `for_email(subject, body, sender)` | `Spotlighted` | with `provenance` set; datamarking with an automatic marker by default |
| `html_to_text(html, drop_hidden=True)` | `str` | visible text, standard library parser |

`Spotlighted` is a frozen dataclass with `text`, `instruction`, `mode`, `marker`, `end`, `skip_code` and `provenance`, and the methods `block()` (header plus text), `prompt(system, user_prefix)` (returns a `Prompt` with `system`, `user` and `as_messages()`) and `unmark()`.

Every function is deterministic: the same input and options give the same output, including the automatic marker and the delimiter tag.

## CLI

```text
spotlighting mark --mode delimit|datamark|encode [--marker X] [--start S --end E]
                  [--scheme base64|hex|rot13] [--skip-code] [--on-collision ...]
                  [--format text|json] [FILE]
spotlighting unmark --mode ... [same options] [FILE]     # or --format json with mark's JSON
spotlighting instruction --mode ... [options] [--format text|json]
spotlighting demo [--format text|json]
```

Input is FILE or stdin, read as UTF-8 bytes so CRLF line endings survive. Text output is the marked text only; for `delimit` and `encode` a final newline is added, and `unmark` removes it again. Exit codes: 0 success, 1 the text could not be marked or unmarked (a marker collision, invalid base64), 2 usage errors and unreadable or non-UTF-8 input. `--help` works on every command.

## What this is not

- **Not a complete defence.** Spotlighting lowers the chance that a model follows text inside untrusted content. It does not make that chance zero, the paper does not claim it does, and no amount of prompt text is a security boundary.
- **Not a detector.** It does not look for attacks and does not block anything. Pair it with a classifier or a hosted shield if you want detection.
- **Not a replacement for a policy layer and least privilege.** The controls that hold when the model is fooled are outside the model: tools that can only do what the task needs, approval for actions with side effects, egress limits, and credentials scoped to the user. Spotlighting is one layer in front of those.
- **Not an HTML sanitiser.** `html_to_text` drops what the markup itself hides; it does not evaluate stylesheets, scripts or off-screen positioning.

## FAQ

**Which mode should I use?**
Datamarking, unless you have measured that encoding keeps your task quality on your model. The paper found no task-quality cost for datamarking on its benchmarks and recommends against delimiting alone.

**What if the text already contains `^`?**
`datamark` raises `MarkerCollision` by default, because a marker that already occurs would make the text ambiguous to the model and to `reverse`. Pass `marker="auto"` to use the first of `^`, `ˆ` (U+02C6), U+E000, U+E001, U+E002 and U+2063 that the text does not contain, or choose your own. The integration helpers and `Pipeline` use `auto` by default.

**Does the instruction change with the options?**
Yes. It names the actual delimiters, marker (with its code point) or encoding, and mentions code blocks when `skip_code` is on. Always use the `instruction` that came back with the text.

**Can I mark text in several places of one prompt?**
Yes. Use `Pipeline` for one structure, or mark each piece with the same mode and marker and include the instruction once.

**Is the delimiter tag a secret?**
No. It is the start of the SHA-256 of the text, so anyone can compute it, but text cannot contain its own hash except by an extremely unlikely accident, which `delimit` checks for. It removes the simplest bypass of delimiting; it does not make delimiting as strong as datamarking.

**Does this call a model or the network?**
No. Everything is a pure string transformation on your machine.

## Contributing

Issues and pull requests are welcome. Run `make check` (ruff and pytest) before opening a pull request; [CONTRIBUTING.md](CONTRIBUTING.md) has the details and [docs/good-first-issues.md](docs/good-first-issues.md) lists six scoped starting points. Test inputs are neutral sentences: `tests/forbidden.txt` lists phrases that must not appear anywhere in the repository. Security problems: see [SECURITY.md](SECURITY.md).

## Related projects

- [basitalisandhu on GitHub](https://github.com/basitalisandhu): the maintainer's other projects.
- [agent-security-skills](https://github.com/basitalisandhu/agent-security-skills): a Claude Code plugin and skill pack for agent security: threat modelling, prompt injection review, MCP server review, guard hooks.
- [agentic-semgrep-rules](https://github.com/basitalisandhu/agentic-semgrep-rules): Semgrep rules for agent code: model output reaching shells, SQL and files, user input in system prompts, over-broad tools.
- [cc-hooks](https://github.com/basitalisandhu/cc-hooks): typed Python SDK and offline test runner for Claude Code hooks.

## Licence

MIT, see [LICENSE](LICENSE). Copyright 2026 Muhammad Basit Ali.
