from __future__ import annotations

import pytest

from spotlighting import MarkerCollision, Pipeline, SpotlightError

TOOL_RESULT = {
    "id": "res-42",
    "status": "ok",
    "count": 2,
    "cached": False,
    "meta": {"source_url": "https://example.com/a", "fetched": "2026-10-04"},
    "results": [
        {"id": "r1", "title": "Weekly update", "snippet": "The build passed on all platforms."},
        {"id": "r2", "title": "Lunch menu", "snippet": "Soup and bread on Tuesday.", "score": 0.5},
    ],
    "notes": ("first note", "second note"),
    "nothing": None,
}


def test_marks_untrusted_strings_and_keeps_trusted_keys() -> None:
    result = Pipeline(trusted_keys={"id", "status"}).apply(TOOL_RESULT)
    value = result.value
    assert value["id"] == "res-42" and value["status"] == "ok"
    assert value["results"][0]["id"] == "r1"
    assert value["results"][0]["snippet"] == "The^build^passed^on^all^platforms."
    assert value["results"][1]["title"] == "Lunch^menu"
    assert value["notes"] == ("first^note", "second^note")
    assert value["count"] == 2 and value["cached"] is False and value["nothing"] is None
    assert value["results"][1]["score"] == 0.5


def test_paths_listed() -> None:
    result = Pipeline(trusted_keys={"id", "status"}).apply(TOOL_RESULT)
    assert "results.*.snippet" in result.paths
    assert "meta.fetched" in result.paths
    assert not any(p.endswith(".id") or p == "id" for p in result.paths)


def test_trusted_paths_exact() -> None:
    result = Pipeline(trusted_paths={"meta", "results.*.title"}).apply(TOOL_RESULT)
    assert result.value["meta"] == TOOL_RESULT["meta"]
    assert result.value["results"][0]["title"] == "Weekly update"
    assert result.value["results"][0]["snippet"] != "The build passed on all platforms."
    assert result.value["id"] == "res-42"  # one word, nothing to mark, but still marked


def test_trusted_list_path() -> None:
    result = Pipeline(trusted_paths={"notes.*"}).apply(TOOL_RESULT)
    assert result.value["notes"] == ("first note", "second note")


@pytest.mark.parametrize("mode", ["delimit", "datamark", "encode"])
def test_restore_round_trip(mode: str) -> None:
    result = Pipeline(mode, trusted_keys={"id"}).apply(TOOL_RESULT)  # type: ignore[arg-type]
    assert result.restore() == TOOL_RESULT


def test_does_not_mutate_input() -> None:
    import copy

    before = copy.deepcopy(TOOL_RESULT)
    Pipeline().apply(TOOL_RESULT)
    assert before == TOOL_RESULT


def test_auto_marker_is_shared_and_collision_free() -> None:
    data = {"a": "x ^ y", "b": "plain words"}
    result = Pipeline().apply(data)
    assert result.marker == "\u02c6"
    assert result.value["b"] == "plain\u02c6words"
    assert "U+02C6" in result.instruction
    assert result.restore() == data


def test_explicit_marker_collision_raises() -> None:
    with pytest.raises(MarkerCollision):
        Pipeline(marker="^").apply({"a": "x ^ y"})


def test_delimit_collision_raises() -> None:
    with pytest.raises(MarkerCollision):
        Pipeline("delimit").apply(["fine", "has >> inside"])


def test_top_level_string_and_list() -> None:
    assert Pipeline().apply("a b").value == "a^b"
    result = Pipeline("encode").apply(["hi", 3])
    assert result.value == ["aGk=", 3]
    assert result.paths == ("*",)


def test_one_instruction_for_whole_structure() -> None:
    result = Pipeline("encode", scheme="hex").apply(TOOL_RESULT)
    assert "hexadecimal" in result.instruction
    assert result.mode == "encode" and result.marker == "hex"


def test_unknown_mode() -> None:
    with pytest.raises(SpotlightError):
        Pipeline("other")  # type: ignore[arg-type]
