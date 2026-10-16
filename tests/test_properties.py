"""Property-style round-trip tests: every marking has an exact inverse, for any text.

Hypothesis generates the inputs, including Unicode whitespace, line separators, CRLF,
fenced code and lone surrogates, which hand-picked samples miss.
"""

from __future__ import annotations

import json

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from spotlighting import (
    MarkerCollision,
    Pipeline,
    SpotlightError,
    datamark,
    decode,
    delimit,
    encode,
    reverse,
    spotlight,
    undelimit,
    unmark,
)

# Text with the characters that matter to the markers: ASCII and Unicode whitespace, line
# breaks of every kind, the default markers, fences, plus anything else Hypothesis likes.
SPECIAL = " \t\n\r\x0b\x0c\x85\u00a0\u2003\u2028\u2029\u3000^\u02c6\ue000<>`~"
texts = st.text(
    alphabet=st.one_of(st.sampled_from(SPECIAL), st.characters(exclude_categories=("Cs",))),
    max_size=200,
)
fenced = st.builds(
    lambda before, code, after, fence: f"{before}\n{fence}py\n{code}\n{fence}\n{after}",
    texts,
    texts,
    texts,
    st.sampled_from(["```", "~~~", "````"]),
)
markers = st.sampled_from(["^", "\u02c6", "\ue000", "@@", "|"])
COMMON = settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])


@COMMON
@given(texts)
def test_delimit_round_trips(text):
    try:
        result = delimit(text)
    except MarkerCollision:
        assert "<<" in text or ">>" in text
        return
    assert undelimit(result.text) == text
    assert unmark(result) == text


@COMMON
@given(texts)
def test_delimit_with_tag_round_trips(text):
    result = delimit(text, on_collision="tag")
    assert unmark(result) == text
    assert result.marker not in text and result.end not in text


@COMMON
@given(st.one_of(texts, fenced), markers, st.booleans())
def test_datamark_round_trips_or_refuses(text, marker, skip_code):
    try:
        result = datamark(text, marker=marker, skip_code=skip_code)
    except MarkerCollision:
        return
    assert reverse(result.text, marker=marker, skip_code=skip_code) == text
    assert unmark(result) == text


@COMMON
@given(st.one_of(texts, fenced), st.booleans())
def test_datamark_auto_marker_always_round_trips(text, skip_code):
    result = datamark(text, marker="auto", skip_code=skip_code)
    assert unmark(result) == text


@COMMON
@given(texts)
def test_datamark_leaves_no_plain_space(text):
    result = datamark(text, marker="auto")
    assert " " not in result.text


@COMMON
@given(texts, st.sampled_from(["base64", "rot13", "hex"]))
def test_encode_round_trips(text, scheme):
    result = encode(text, scheme)
    assert decode(result.text, scheme) == text
    assert unmark(result) == text


@COMMON
@given(texts, st.sampled_from(["delimit", "datamark", "encode"]))
def test_spotlight_round_trips_through_its_own_metadata(text, mode):
    try:
        result = spotlight(text, mode, marker="auto" if mode == "datamark" else "^")
    except MarkerCollision:
        assert mode == "delimit"
        return
    assert unmark(result) == text
    assert result.original_length == len(text)


@COMMON
@given(st.text(alphabet=st.characters(categories=("Cs",)), min_size=1, max_size=5))
def test_encode_lone_surrogates_round_trip(text):
    # Lone surrogates turn up in text decoded with errors="surrogateescape" or from JSON.
    for scheme in ("base64", "hex"):
        assert decode(encode(text, scheme).text, scheme) == text


json_values = st.recursive(
    st.one_of(st.none(), st.booleans(), st.integers(), texts),
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(
            st.sampled_from(["id", "title", "body", "status", "items"]), children, max_size=4
        ),
    ),
    max_leaves=12,
)


@COMMON
@given(json_values, st.sampled_from(["datamark", "encode", "delimit"]))
def test_pipeline_restore_round_trips(value, mode):
    pipeline = Pipeline(mode, trusted_keys={"id", "status"}, start="\ue010", end="\ue011")
    try:
        result = pipeline.apply(value)
    except MarkerCollision:
        return
    assert result.restore() == value
    json.dumps(result.value)  # the marked structure stays JSON-serialisable


def test_decode_rejects_garbage():
    with pytest.raises(SpotlightError):
        decode("not base64!", "base64")
    with pytest.raises(SpotlightError):
        decode("zz", "hex")
