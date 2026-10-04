from __future__ import annotations

from spotlighting import for_email, for_fetched_page, for_tool_result, header_value, html_to_text

PAGE = """<!doctype html>
<html><head><title>Garden club</title><style>p { color: green; }</style>
<script>var visits = 1;</script></head>
<body>
<h1>Garden club</h1>
<p>Meetings are on the first Saturday of the month.</p>
<!-- a comment that is not shown -->
<div hidden>Hidden paragraph about seed prices.</div>
<p style="display:none">Another hidden line.</p>
<span aria-hidden="true">Decorative text.</span>
<ul><li>Bring gloves</li><li>Bring water &amp; a hat</li></ul>
<p>Tomatoes<br>Beans<img src="x.png" alt="photo"></p>
</body></html>"""


def test_html_to_text_visible_only() -> None:
    text = html_to_text(PAGE)
    assert text.startswith("Garden club")
    assert "Meetings are on the first Saturday of the month." in text
    assert "Bring water & a hat" in text
    assert "Tomatoes\nBeans" in text
    for gone in (
        "visits",
        "color: green",
        "comment",
        "seed prices",
        "Another hidden",
        "Decorative",
    ):
        assert gone not in text


def test_html_to_text_keep_hidden() -> None:
    text = html_to_text(PAGE, drop_hidden=False)
    assert "seed prices" in text and "Another hidden line." in text
    assert "visits" not in text


def test_html_to_text_nested_hidden_and_unclosed() -> None:
    html = "<div hidden><div><p>inner</p></div>still hidden</div><p>shown<p>also shown"
    assert html_to_text(html) == "shown\nalso shown"


def test_for_fetched_page() -> None:
    result = for_fetched_page("https://example.com/garden", PAGE)
    assert result.provenance == "source: web page https://example.com/garden"
    assert "Meetings^are^on" in result.text
    assert result.block().startswith("source: web page https://example.com/garden\nGarden^club")
    assert result.unmark() == html_to_text(PAGE)


def test_for_tool_result() -> None:
    result = for_tool_result("search", "Two results found for the query.")
    assert result.provenance == "source: tool search"
    assert result.text == "Two^results^found^for^the^query."
    assert result.mode == "datamark"


def test_for_tool_result_other_modes() -> None:
    enc = for_tool_result("files", "a b", mode="encode", scheme="hex")
    assert enc.text == "612062" and enc.provenance == "source: tool files"
    deli = for_tool_result("files", "a b", mode="delimit")
    assert deli.text == "<<a b>>"


def test_for_tool_result_auto_marker() -> None:
    result = for_tool_result("calc", "2 ^ 3 = 8")
    assert result.marker != "^"
    assert result.unmark() == "2 ^ 3 = 8"


def test_for_email() -> None:
    result = for_email("Lunch on Friday", "Shall we meet at noon?\nThanks.", "sam@example.com")
    assert result.provenance == "source: email from sam@example.com"
    assert result.text.startswith("Subject:^Lunch^on^Friday^\n^\nShall^we")
    assert result.unmark() == "Subject: Lunch on Friday\n\nShall we meet at noon?\nThanks."


def test_header_values_are_one_line_and_capped() -> None:
    assert header_value("name\nwith\r\nbreaks\x00and\u2028more") == "name with breaks and more"
    assert len(header_value("x" * 500)) == 200
    assert header_value("x" * 500).endswith("...")
    result = for_email("s", "b", "Sam\nsource: tool other")
    assert "\n" not in (result.provenance or "")
    assert for_tool_result("a\nb", "c").provenance == "source: tool a b"
