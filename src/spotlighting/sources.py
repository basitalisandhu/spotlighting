"""Pure helpers for the places untrusted text usually comes from: tool results, web pages, email.

Each returns a `Spotlighted` whose `provenance` is a one-line header such as
``source: tool search``. The header is built from metadata that may itself be untrusted (a
tool name chosen by a server, a URL, a sender address), so it is reduced to one line of
printable characters and capped in length. Nothing here touches the network.
"""

from __future__ import annotations

import re
from dataclasses import replace
from html.parser import HTMLParser

from .marks import Mode, Spotlighted, spotlight

HEADER_LIMIT = 200

_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]+")

# Elements whose text is never shown to a reader.
_SKIP = frozenset({"script", "style", "noscript", "template", "head", "svg", "math", "iframe"})
# Elements that start a new line in rendered text.
_BLOCK = frozenset(
    {
        "address", "article", "aside", "blockquote", "br", "dd", "details", "div", "dl", "dt",
        "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6",
        "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section", "summary", "table",
        "td", "th", "tr", "ul",
    }
)  # fmt: skip
_VOID = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track",
     "wbr"}
)  # fmt: skip
_HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.IGNORECASE)


def header_value(value: str, limit: int = HEADER_LIMIT) -> str:
    """One line of printable text, at most `limit` characters, for a provenance header."""
    flat = " ".join(_CONTROL.sub(" ", value).split())
    return flat if len(flat) <= limit else flat[: limit - 3] + "..."


class _TextExtractor(HTMLParser):
    def __init__(self, drop_hidden: bool) -> None:
        super().__init__(convert_charrefs=True)
        self.drop_hidden = drop_hidden
        self.parts: list[str] = []
        self.skipping: list[str] = []

    def _hidden(self, tag: str, attrs: list[tuple[str, str | None]]) -> bool:
        if tag in _SKIP:
            return True
        if not self.drop_hidden:
            return False
        names = {name.lower(): (val or "") for name, val in attrs}
        return (
            "hidden" in names
            or names.get("aria-hidden", "").lower() == "true"
            or bool(_HIDDEN_STYLE.search(names.get("style", "")))
        )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.skipping:
            if tag not in _VOID:
                self.skipping.append(tag)
            return
        if tag not in _VOID and self._hidden(tag, attrs):
            self.skipping.append(tag)
            return
        if tag in _BLOCK:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self.skipping and tag in _BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.skipping:
            if tag in self.skipping:
                while self.skipping and self.skipping.pop() != tag:
                    pass
            return
        if tag in _BLOCK:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skipping:
            self.parts.append(data)


def html_to_text(html_text: str, *, drop_hidden: bool = True) -> str:
    """Visible text of an HTML document, using only the standard library's `html.parser`.

    Scripts, styles and comments are dropped. With `drop_hidden` (the default), elements with
    the `hidden` attribute, ``aria-hidden="true"``, or an inline style of ``display: none`` or
    ``visibility: hidden`` are dropped too, since hidden text is read by a model but not by the
    person who asked for the page. Styles from stylesheets are not evaluated.
    """
    parser = _TextExtractor(drop_hidden)
    parser.feed(html_text)
    parser.close()
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _with_header(result: Spotlighted, header: str) -> Spotlighted:
    return replace(result, provenance=header)


def for_tool_result(
    name: str, content: str, *, mode: Mode = "datamark", **options: object
) -> Spotlighted:
    """Spotlight the text a tool returned. Header: ``source: tool <name>``."""
    options.setdefault("marker", "auto")
    result = spotlight(content, mode, **options)  # type: ignore[arg-type]
    return _with_header(result, f"source: tool {header_value(name)}")


def for_fetched_page(
    url: str,
    html_text: str,
    *,
    mode: Mode = "datamark",
    drop_hidden: bool = True,
    **options: object,
) -> Spotlighted:
    """Strip a fetched page to its visible text and spotlight it.

    Header: ``source: web page <url>``.

    Takes the page you already fetched; this function makes no request.
    """
    options.setdefault("marker", "auto")
    text = html_to_text(html_text, drop_hidden=drop_hidden)
    result = spotlight(text, mode, **options)  # type: ignore[arg-type]
    return _with_header(result, f"source: web page {header_value(url)}")


def for_email(
    subject: str, body: str, sender: str, *, mode: Mode = "datamark", **options: object
) -> Spotlighted:
    """Spotlight an email. Header: ``source: email from <sender>``.

    The subject is written by the sender too, so it goes inside the marked text, on a first
    line ``Subject: ...``, rather than in the header.
    """
    options.setdefault("marker", "auto")
    text = f"Subject: {header_value(subject, limit=1000)}\n\n{body}"
    result = spotlight(text, mode, **options)  # type: ignore[arg-type]
    return _with_header(result, f"source: email from {header_value(sender)}")
