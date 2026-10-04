from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from spotlighting import __version__
from spotlighting.cli import DEMO_TEXT, main


class _Stdin:
    def __init__(self, data: bytes) -> None:
        self.buffer = io.BytesIO(data)


def run(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], argv: list[str],
        stdin: str = "") -> tuple[int, str, str]:  # fmt: skip
    monkeypatch.setattr(sys, "stdin", _Stdin(stdin.encode("utf-8")))
    code = main(argv)
    out = capsys.readouterr()
    return code, out.out, out.err


def test_mark_datamark_stdin(monkeypatch, capsys) -> None:
    code, out, _ = run(monkeypatch, capsys, ["mark", "--mode", "datamark"], "one two\n")
    assert code == 0 and out == "one^two^\n"


def test_mark_file(tmp_path: Path, monkeypatch, capsys) -> None:
    src = tmp_path / "in.txt"
    src.write_bytes(b"Line one\r\nLine two\r\n")
    code, out, _ = run(monkeypatch, capsys, ["mark", "--mode", "datamark", str(src)])
    assert code == 0 and out == "Line^one^\r^\nLine^two^\r^\n"


TEXTS = ["Plain words here.\n", "No newline", "Caf\u00e9 \U0001f680\r\n", ""]


@pytest.mark.parametrize(
    "opts",
    [
        ["--mode", "delimit"],
        ["--mode", "datamark"],
        ["--mode", "datamark", "--marker", "\ue000"],
        ["--mode", "datamark", "--skip-code"],
        ["--mode", "encode"],
        ["--mode", "encode", "--scheme", "hex"],
        ["--mode", "encode", "--scheme", "rot13"],
        ["--mode", "delimit", "--start", "[[", "--end", "]]"],
    ],
)
@pytest.mark.parametrize("text", TEXTS)
def test_mark_then_unmark_text(monkeypatch, capsys, opts: list[str], text: str) -> None:
    code, marked, _ = run(monkeypatch, capsys, ["mark", *opts], text)
    assert code == 0
    code, restored, _ = run(monkeypatch, capsys, ["unmark", *opts], marked)
    assert code == 0 and restored == text


def test_mark_then_unmark_json(monkeypatch, capsys) -> None:
    text = "x ^ y and more\n"
    code, out, _ = run(
        monkeypatch,
        capsys,
        ["mark", "--mode", "datamark", "--marker", "auto", "--format", "json"],
        text,
    )
    doc = json.loads(out)
    assert code == 0 and doc["marker"] == "\u02c6" and "instruction" in doc
    code, restored, _ = run(monkeypatch, capsys, ["unmark", "--format", "json"], out)
    assert code == 0 and restored == text


def test_unmark_json_bad_input(monkeypatch, capsys) -> None:
    code, _, err = run(monkeypatch, capsys, ["unmark", "--format", "json"], "not json")
    assert code == 2 and "expected the JSON" in err


def test_collision_exit_1(monkeypatch, capsys) -> None:
    code, out, err = run(monkeypatch, capsys, ["mark", "--mode", "datamark"], "a ^ b")
    assert code == 1 and out == "" and "marker" in err


def test_delimit_tag_option(monkeypatch, capsys) -> None:
    code, out, _ = run(
        monkeypatch,
        capsys,
        ["mark", "--mode", "delimit", "--on-collision", "tag", "--format", "json"],
        "a >> b",
    )  # fmt: skip
    doc = json.loads(out)
    assert code == 0 and len(doc["marker"]) == 14


@pytest.mark.parametrize(
    "argv",
    [
        ["mark", "--mode", "delimit", "--on-collision", "auto"],
        ["mark", "--mode", "datamark", "--on-collision", "tag"],
    ],
)
def test_mismatched_collision_option(monkeypatch, capsys, argv: list[str]) -> None:
    code, _, _ = run(monkeypatch, capsys, argv, "text")
    assert code == 1


def test_invalid_encoded_input_exit_1(monkeypatch, capsys) -> None:
    code, _, err = run(monkeypatch, capsys, ["unmark", "--mode", "encode"], "@@@")
    assert code == 1 and "base64" in err


def test_missing_file_exit_2(tmp_path: Path, monkeypatch, capsys) -> None:
    code, _, err = run(monkeypatch, capsys, ["mark", "--mode", "datamark", str(tmp_path / "nope")])
    assert code == 2 and "cannot read" in err


def test_non_utf8_input_exit_2(tmp_path: Path, monkeypatch, capsys) -> None:
    bad = tmp_path / "bad.bin"
    bad.write_bytes(b"\xff\xfe\x00")
    code, _, err = run(monkeypatch, capsys, ["mark", "--mode", "datamark", str(bad)])
    assert code == 2 and "UTF-8" in err


def test_usage_errors_exit_2(monkeypatch, capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["mark"])
    assert exc.value.code == 2
    with pytest.raises(SystemExit) as exc:
        main(["mark", "--mode", "rot"])
    assert exc.value.code == 2
    assert main([]) == 2


@pytest.mark.parametrize("mode", ["delimit", "datamark", "encode"])
def test_instruction_command(monkeypatch, capsys, mode: str) -> None:
    code, out, _ = run(monkeypatch, capsys, ["instruction", "--mode", mode])
    assert code == 0 and "data, never instructions" in out and out.endswith("\n")
    code, out, _ = run(monkeypatch, capsys, ["instruction", "--mode", mode, "--format", "json"])
    assert json.loads(out)["mode"] == mode


def test_demo_text(monkeypatch, capsys) -> None:
    code, out, _ = run(monkeypatch, capsys, ["demo"])
    assert code == 0
    assert "[delimit] delimiters << and >>" in out
    assert "[datamark] marker ^" in out
    assert "[encode] scheme base64" in out
    assert "The^quarterly^report" in out


def test_demo_json_round_trips(monkeypatch, capsys) -> None:
    from spotlighting import unmark_text

    code, out, _ = run(monkeypatch, capsys, ["demo", "--format", "json"])
    doc = json.loads(out)
    assert code == 0 and doc["input"] == DEMO_TEXT
    for r in doc["results"]:
        assert unmark_text(r["text"], r["mode"], marker=r["marker"], end=r["end"]) == DEMO_TEXT


def test_demo_is_deterministic(monkeypatch, capsys) -> None:
    first = run(monkeypatch, capsys, ["demo"])[1]
    assert run(monkeypatch, capsys, ["demo"])[1] == first


@pytest.mark.parametrize("sub", [[], ["mark"], ["unmark"], ["instruction"], ["demo"]])
def test_help_everywhere(capsys, sub: list[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main([*sub, "--help"])
    assert exc.value.code == 0
    assert "usage: spotlighting" in capsys.readouterr().out


def test_version(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["--version"])
    assert capsys.readouterr().out.strip() == f"spotlighting {__version__}"


def test_module_entry_point_subprocess() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "spotlighting", "mark", "--mode", "datamark"],
        input=b"alpha beta\n",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0 and proc.stdout == b"alpha^beta^\n"
