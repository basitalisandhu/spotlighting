# Security policy

## Supported versions

The latest release on the `main` branch receives fixes.

## Reporting a vulnerability

Please use GitHub private vulnerability reporting on this repository (Security tab, "Report a vulnerability") rather than a public issue. Include the version, the input text and options that reproduce the problem, and what you expected to happen.

You will get an acknowledgement within 7 days and a fix or a mitigation plan within 30 days for confirmed issues. Credit is given in the release notes unless you prefer otherwise.

## Scope

spotlighting is a pure string transformation library. It makes no network calls, runs no other programs and has no dependencies outside the Python standard library.

Issues of interest:

- input for which `mark` followed by `unmark` does not return the original text;
- input that makes marked text ambiguous, for example a marker or delimiter that occurs in the untrusted text without `MarkerCollision` being raised (outside `on_collision="allow"`);
- an instruction that does not describe the marking actually applied;
- a provenance header that can be made to span more than one line or to carry control characters;
- visible-text extraction in `html_to_text` that keeps the content of `script`, `style`, comments or elements marked `hidden`.

Out of scope: a model following text inside spotlighted content. Spotlighting reduces that risk and does not remove it; the README says so and recommends a policy layer and least privilege alongside it. Reports about a specific model's behaviour are still welcome as issues, with neutral reproduction text, so the documentation can reflect them.

Please do not include working attack text in public issues; describe the shape of the input instead.
