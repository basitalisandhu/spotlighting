"""Seeded fuzz tests for every input reader of the command.

Bad input (non-UTF-8 bytes, wrong JSON types, deep nesting, empty or huge input) must end
with exit code 1 or 2 and a one-line `spotlighting:` message, never a traceback or a hang.
Each case runs under a wall-clock alarm so a hang fails the test instead of stalling CI.
"""

from __future__ import annotations

import io
import json
import random
import signal
import sys
from collections.abc import Iterator

import pytest

from spotlighting import Pipeline, SpotlightError
from spotlighting.cli import main

SEED = 20261028
CASES = 300
SECONDS = 10


class _Stdin:
    def __init__(self, data: bytes) -> None:
        self.buffer = io.BytesIO(data)


@pytest.fixture(autouse=True)
def _alarm() -> Iterator[None]:
    if not hasattr(signal, "SIGALRM"):  # pragma: no cover - Windows
        yield
        return

    def fail(signum, frame):
        raise TimeoutError(f"case ran longer than {SECONDS}s")

    old = signal.signal(signal.SIGALRM, fail)
    signal.alarm(SECONDS)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def _run(monkeypatch, capsys, argv: list[str], data: bytes) -> tuple[int, str]:
    monkeypatch.setattr(sys, "stdin", _Stdin(data))
    code = main(argv)
    return code, capsys.readouterr().err


def _junk(rng: random.Random) -> bytes:
    kind = rng.randrange(6)
    if kind == 0:
        return bytes(rng.randrange(256) for _ in range(rng.randrange(64)))
    if kind == 1:
        return b"\xff\xfe" + "notes".encode("utf-16-le")
    if kind == 2:
        return b""
    if kind == 3:
        return json.dumps(_random_json(rng, 4)).encode()
    if kind == 4:
        depth = rng.choice([50, 1000, 100_000])
        return (rng.choice("[{") * depth).encode()
    return ("word " * rng.randrange(1, 2000)).encode()


def _random_json(rng: random.Random, depth: int):
    pick = rng.randrange(8 if depth else 5)
    if pick == 0:
        return None
    if pick == 1:
        return rng.randrange(-5, 5)
    if pick == 2:
        return rng.random()
    if pick == 3:
        return rng.choice([True, False])
    if pick == 4:
        return rng.choice(["", "a b", "^", "<<x>>", "YQ==", "\ud800", "```\ncode\n```"])
    if pick == 5:
        return [_random_json(rng, depth - 1) for _ in range(rng.randrange(3))]
    keys = ["mode", "text", "marker", "end", "skip_code", "value", "trusted_keys"]
    return {rng.choice(keys): _random_json(rng, depth - 1) for _ in range(rng.randrange(4))}


COMMANDS = [
    ["mark", "--mode", "datamark"],
    ["mark", "--mode", "delimit", "--on-collision", "tag"],
    ["mark", "--mode", "encode", "--format", "json"],
    ["unmark", "--mode", "datamark"],
    ["unmark", "--mode", "encode", "--scheme", "hex"],
    ["unmark", "--mode", "delimit"],
    ["unmark", "--format", "json"],
    ["mark-json"],
    ["mark-json", "--mode", "delimit"],
    ["unmark-json"],
]


@pytest.mark.parametrize("argv", COMMANDS, ids=" ".join)
def test_random_input_never_crashes(argv: list[str], monkeypatch, capsys) -> None:
    rng = random.Random(f"{SEED}-{' '.join(argv)}")
    for _ in range(CASES // len(COMMANDS) * 3):
        data = _junk(rng)
        code, err = _run(monkeypatch, capsys, argv, data)
        assert code in (0, 1, 2), (argv, data[:80])
        if code:
            assert err.startswith("spotlighting: ") and "Traceback" not in err, (argv, err)


@pytest.mark.parametrize(
    "doc",
    [
        {"mode": "datamark", "text": 5},
        {"mode": 5, "text": "a"},
        {"mode": "datamark", "text": "a^b", "marker": [1]},
        {"mode": "delimit", "text": "<<a>>", "marker": "<<", "end": 3},
        {"mode": "encode", "text": None},
        [1, 2],
        "text",
    ],
)
def test_unmark_json_wrong_types_exit_2(doc, monkeypatch, capsys) -> None:
    code, err = _run(monkeypatch, capsys, ["unmark", "--format", "json"], json.dumps(doc).encode())
    assert code == 2 and "expected the JSON" in err and "stdin" in err


def test_deep_json_names_the_file(tmp_path, monkeypatch, capsys) -> None:
    src = tmp_path / "deep.json"
    src.write_text("[" * 100_000)
    code, err = _run(monkeypatch, capsys, ["mark-json", str(src)], b"")
    assert code == 2 and str(src) in err and "nested too deeply" in err


def test_non_utf8_names_the_file(tmp_path, monkeypatch, capsys) -> None:
    src = tmp_path / "latin1.txt"
    src.write_bytes("caf\xe9".encode("latin-1"))
    code, err = _run(monkeypatch, capsys, ["mark", "--mode", "datamark", str(src)], b"")
    assert code == 2 and str(src) in err and "not valid UTF-8" in err


def test_lone_surrogate_in_output_is_a_clear_error(monkeypatch, capsys) -> None:
    doc = '{"mode": "datamark", "marker": "^", "text": "a^\\ud800"}'
    code, err = _run(monkeypatch, capsys, ["unmark", "--format", "json"], doc.encode())
    assert code == 1 and "lone surrogate" in err


def test_instruction_rejects_an_empty_marker(monkeypatch, capsys) -> None:
    code, err = _run(
        monkeypatch, capsys, ["instruction", "--mode", "datamark", "--marker", ""], b""
    )
    assert code == 1 and "must not be empty" in err


def test_pipeline_refuses_deep_and_cyclic_structures() -> None:
    deep: object = "x"
    for _ in range(5000):
        deep = [deep]
    with pytest.raises(SpotlightError, match="levels deep"):
        Pipeline().apply(deep)
    loop: list[object] = []
    loop.append(loop)
    with pytest.raises(SpotlightError, match="contains itself"):
        Pipeline().apply({"k": loop})
    shared = ["same text"]
    assert Pipeline().apply({"a": shared, "b": shared}).value == {
        "a": ["same^text"],
        "b": ["same^text"],
    }
