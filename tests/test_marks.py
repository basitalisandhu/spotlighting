from __future__ import annotations

import pytest

from spotlighting import (
    MODES,
    SCHEMES,
    MarkerCollision,
    SpotlightError,
    datamark,
    decode,
    delimit,
    encode,
    instruction,
    reverse,
    spotlight,
    undelimit,
    unmark,
    unmark_text,
)

from .conftest import SAMPLES

SAMPLE_IDS = sorted(SAMPLES)


@pytest.mark.parametrize("name", SAMPLE_IDS)
def test_delimit_round_trip(name: str) -> None:
    text = SAMPLES[name]
    result = delimit(text)
    assert result.text == f"<<{text}>>"
    assert undelimit(result.text) == text
    assert unmark(result) == text


@pytest.mark.parametrize("name", SAMPLE_IDS)
def test_datamark_round_trip(name: str) -> None:
    text = SAMPLES[name]
    result = datamark(text)
    assert " " not in result.text
    assert reverse(result.text) == text
    assert unmark(result) == text


@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("name", SAMPLE_IDS)
def test_encode_round_trip(name: str, scheme: str) -> None:
    text = SAMPLES[name]
    result = encode(text, scheme)  # type: ignore[arg-type]
    assert decode(result.text, scheme) == text  # type: ignore[arg-type]
    assert unmark(result) == text


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("name", ["empty", "emoji", "crlf", "long"])
def test_spotlight_round_trip_every_mode(mode: str, name: str) -> None:
    result = spotlight(SAMPLES[name], mode)  # type: ignore[arg-type]
    assert result.mode == mode
    assert result.unmark() == SAMPLES[name]


def test_datamark_matches_the_paper_example() -> None:
    assert datamark("In this manner Cosette traversed").text == "In^this^manner^Cosette^traversed"


def test_datamark_keeps_line_breaks_with_a_marker_in_front() -> None:
    assert datamark("one two\nthree").text == "one^two^\nthree"
    assert datamark("a\r\nb").text == "a^\r^\nb"
    assert datamark("a\tb").text == "a^\tb"


def test_datamark_unicode_spaces_are_marked() -> None:
    assert datamark("a\u3000b\u00a0c").text == "a^\u3000b^\u00a0c"


def test_datamark_custom_and_multichar_marker() -> None:
    result = datamark("alpha beta gamma", marker="\ue000")
    assert result.text == "alpha\ue000beta\ue000gamma"
    assert result.marker == "\ue000"
    assert "U+E000" in result.instruction
    multi = datamark("alpha beta", marker="||")
    assert multi.text == "alpha||beta"
    assert reverse(multi.text, marker="||") == "alpha beta"


def test_datamark_collision_raises_by_default() -> None:
    with pytest.raises(MarkerCollision):
        datamark("x ^ y")


def test_datamark_auto_marker_avoids_collision() -> None:
    result = datamark("x ^ y", marker="auto")
    assert result.marker == "\u02c6"
    assert result.unmark() == "x ^ y"
    assert datamark("x ^ y", on_collision="auto").marker == "\u02c6"


def test_datamark_rejects_ambiguous_multichar_marker() -> None:
    with pytest.raises(MarkerCollision):
        datamark("a b", marker="aa")


@pytest.mark.parametrize("bad", ["", " ", "a b", "\n"])
def test_datamark_rejects_bad_markers(bad: str) -> None:
    with pytest.raises(SpotlightError):
        datamark("text here", marker=bad)


@pytest.mark.parametrize("name", SAMPLE_IDS)
def test_datamark_never_changes_the_non_whitespace_characters(name: str) -> None:
    text = SAMPLES[name]
    result = datamark(text, marker="auto")
    before = [ch for ch in text if not ch.isspace()]
    after = [ch for ch in result.text.replace(result.marker, "") if not ch.isspace()]
    assert after == before
    assert {ch for ch in after} == {ch for ch in before}


def _pseudo_random_texts(count: int) -> list[str]:
    alphabet = ["a", "b", "Z", "\u00e9", "\u4e2d", "\U0001f600", " ", "  ", "\n", "\r\n", "\t"]
    alphabet += [".", "`"]
    state = 20261004
    texts = []
    for _ in range(count):
        parts = []
        for _ in range(state % 40):
            state = (state * 1103515245 + 12345) % (2**31)
            parts.append(alphabet[state % len(alphabet)])
        state = (state * 1103515245 + 12345) % (2**31)
        texts.append("".join(parts))
    return texts


@pytest.mark.parametrize("text", _pseudo_random_texts(60))
def test_property_datamark_preserves_characters_and_round_trips(text: str) -> None:
    for skip_code in (False, True):
        result = datamark(text, skip_code=skip_code)
        stripped = result.text.replace("^", "")
        assert sorted(ch for ch in stripped if not ch.isspace()) == sorted(
            ch for ch in text if not ch.isspace()
        )
        assert reverse(result.text, skip_code=skip_code) == text


CODE_DOC = (
    "Run the tool like this:\n"
    "```bash\n"
    "tool --flag value  # two spaces kept\n"
    "```\n"
    "Then read the output.\n"
)


def test_skip_code_leaves_fenced_blocks_untouched() -> None:
    result = datamark(CODE_DOC, skip_code=True)
    assert "```bash\ntool --flag value  # two spaces kept\n```\n" in result.text
    assert result.text.startswith("Run^the^tool^like^this:^\n")
    assert result.text.endswith("Then^read^the^output.^\n")
    assert reverse(result.text, skip_code=True) == CODE_DOC
    assert result.unmark() == CODE_DOC


def test_without_skip_code_code_is_marked() -> None:
    result = datamark(CODE_DOC)
    assert "tool^--flag^value^^#" in result.text
    assert result.unmark() == CODE_DOC


def test_skip_code_tilde_fence_and_unclosed_fence() -> None:
    tilde = "intro text\n~~~\nraw  code\n~~~\noutro text"
    assert datamark(tilde, skip_code=True).text == "intro^text^\n~~~\nraw  code\n~~~\noutro^text"
    unclosed = "intro text\n```\nraw  code to the end\n"
    marked = datamark(unclosed, skip_code=True)
    assert marked.text == "intro^text^\n```\nraw  code to the end\n"
    assert marked.unmark() == unclosed


def test_skip_code_marker_inside_code_is_allowed() -> None:
    doc = "see below\n```\nx = a ^ b\n```\n"
    result = datamark(doc, skip_code=True)
    assert result.marker == "^"
    assert result.unmark() == doc


def test_skip_code_longer_closing_fence_and_crlf() -> None:
    doc = "intro\r\n````\r\ncode  here\r\n`````\r\nafter words\r\n"
    result = datamark(doc, skip_code=True)
    assert "code  here" in result.text
    assert "after^words" in result.text
    assert result.unmark() == doc


def test_skip_code_note_in_instruction() -> None:
    assert "Fenced code blocks" in datamark("a b", skip_code=True).instruction
    assert "Fenced code blocks" not in datamark("a b").instruction


def test_delimit_custom_delimiters() -> None:
    result = delimit("plain text", start="[[DATA]]", end="[[/DATA]]")
    assert result.text == "[[DATA]]plain text[[/DATA]]"
    assert result.marker == "[[DATA]]" and result.end == "[[/DATA]]"
    assert undelimit(result.text, start="[[DATA]]", end="[[/DATA]]") == "plain text"


def test_delimit_collision_modes() -> None:
    text = "shell output: echo hi >> log.txt"
    with pytest.raises(MarkerCollision):
        delimit(text)
    allowed = delimit(text, on_collision="allow")
    assert allowed.unmark() == text
    tagged = delimit(text, on_collision="tag")
    assert tagged.marker.startswith("<<") and len(tagged.marker) == 14
    assert tagged.end is not None and tagged.end.endswith(">>")
    assert tagged.marker not in text and tagged.end not in text
    assert tagged.marker in tagged.instruction
    assert tagged.unmark() == text


def test_delimit_tag_is_deterministic() -> None:
    a = delimit("same text", on_collision="tag")
    b = delimit("same text", on_collision="tag")
    c = delimit("other text", on_collision="tag")
    assert a == b
    assert a.marker != c.marker


@pytest.mark.parametrize("kwargs", [{"start": ""}, {"end": ""}, {"on_collision": "maybe"}])
def test_delimit_rejects_bad_options(kwargs: dict[str, str]) -> None:
    with pytest.raises(SpotlightError):
        delimit("text", **kwargs)  # type: ignore[arg-type]


def test_undelimit_rejects_unwrapped_text() -> None:
    with pytest.raises(SpotlightError):
        undelimit("no delimiters")
    with pytest.raises(SpotlightError):
        undelimit("<>")


def test_encode_values() -> None:
    assert encode("hello").text == "aGVsbG8="
    assert encode("hello", "hex").text == "68656c6c6f"
    assert encode("Hello, World", "rot13").text == "Uryyb, Jbeyq"


def test_decode_ignores_whitespace_and_rejects_garbage() -> None:
    assert decode("aGVs\nbG8=") == "hello"
    assert decode("68 65", "hex") == "he"
    with pytest.raises(SpotlightError):
        decode("not base64!!")
    with pytest.raises(SpotlightError):
        decode("zz", "hex")
    with pytest.raises(SpotlightError):
        decode("//4=")  # valid base64, not UTF-8


def test_unknown_scheme_and_mode() -> None:
    with pytest.raises(SpotlightError):
        encode("x", "rot47")  # type: ignore[arg-type]
    with pytest.raises(SpotlightError):
        spotlight("x", "invisible")  # type: ignore[arg-type]
    with pytest.raises(SpotlightError):
        instruction("invisible")  # type: ignore[arg-type]
    with pytest.raises(SpotlightError):
        unmark_text("x", "invisible")  # type: ignore[arg-type]


def test_spotlight_defaults_to_datamark() -> None:
    assert spotlight("a b").mode == "datamark"
