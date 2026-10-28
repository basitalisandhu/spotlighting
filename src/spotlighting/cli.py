"""The `spotlighting` command: mark, unmark, mark JSON, print instructions, and a demo.

Exit codes: 0 success, 1 the text could not be marked or unmarked (for example a marker
collision or invalid base64), 2 usage errors and unreadable or malformed input.
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path
from typing import Any

from . import __version__
from .marks import (
    DEFAULT_END,
    DEFAULT_MARKER,
    DEFAULT_START,
    MODES,
    SCHEMES,
    Spotlighted,
    SpotlightError,
    instruction,
    spotlight,
    unmark_text,
)
from .pipeline import Pipeline, PipelineResult

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2

DEMO_TEXT = (
    "The quarterly report is attached. Revenue grew in the second half, and the team plans "
    "to hire two engineers in March.\nPlease send comments by Friday."
)


class _InputError(Exception):
    pass


def _name(path: str | None) -> str:
    return "stdin" if path in (None, "-") else str(path)


def _read(path: str | None) -> str:
    try:
        data = sys.stdin.buffer.read() if path in (None, "-") else Path(path).read_bytes()  # type: ignore[arg-type]
    except OSError as exc:
        raise _InputError(f"cannot read {path}: {exc.strerror or exc}") from exc
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise _InputError(f"{_name(path)}: input is not valid UTF-8: {exc}") from exc


def _load_json(raw: str, path: str | None, expected: str) -> Any:
    try:
        return json.loads(raw)
    except ValueError as exc:  # JSONDecodeError, and integers longer than Python reads
        raise _InputError(f"{_name(path)}: expected {expected}; not valid JSON: {exc}") from exc
    except RecursionError as exc:
        raise _InputError(f"{_name(path)}: expected {expected}; nested too deeply to read") from exc


def _field(
    doc: dict[str, Any],
    key: str,
    path: str | None,
    *,
    optional: bool = False,
    printer: str = "mark --format json",
) -> Any:
    value = doc.get(key)
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise _InputError(
            f"{_name(path)}: expected the JSON printed by `{printer}`: {key!r} must be a string"
        )
    return value


def _write(text: str) -> None:
    sys.stdout.write(text)
    sys.stdout.flush()


def _dump(obj: Any) -> None:
    _write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def _as_json(result: Spotlighted) -> dict[str, Any]:
    return {
        "mode": result.mode,
        "marker": result.marker,
        "end": result.end,
        "skip_code": result.skip_code,
        "instruction": result.instruction,
        "text": result.text,
    }


def _add_mode_options(parser: argparse.ArgumentParser, *, required: bool = True) -> None:
    parser.add_argument(
        "--mode", choices=MODES, required=required, default=None if required else "datamark",
        help="delimit, datamark or encode",
    )  # fmt: skip
    parser.add_argument(
        "--marker", default=DEFAULT_MARKER,
        help=f"datamark marker (default {DEFAULT_MARKER!r}; 'auto' picks one the text lacks)",
    )  # fmt: skip
    parser.add_argument("--start", default=DEFAULT_START, help="delimit start delimiter")
    parser.add_argument("--end", default=DEFAULT_END, help="delimit end delimiter")
    parser.add_argument("--scheme", choices=SCHEMES, default="base64", help="encode scheme")
    parser.add_argument(
        "--skip-code", action="store_true", help="datamark: leave fenced code blocks unmarked"
    )
    parser.add_argument("--format", choices=("text", "json"), default="text", help="output format")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spotlighting",
        description=(
            "Mark untrusted text before it reaches a model (delimiting, datamarking, encoding) "
            "and print the system-prompt instruction that goes with each mode."
        ),
        epilog="Exit codes: 0 success, 1 cannot mark or unmark, 2 usage or input error.",
    )
    parser.add_argument("--version", action="version", version=f"spotlighting {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    mark = sub.add_parser(
        "mark",
        help="spotlight text from a file or stdin",
        description="Spotlight text read from FILE or stdin. Text output is the marked text "
        "only (delimit and encode add a final newline); json adds the instruction and settings.",
    )
    _add_mode_options(mark)
    mark.add_argument(
        "--on-collision", choices=("error", "allow", "tag", "auto"), default="error",
        help="when the text contains the marker or a delimiter (delimit: error, allow, tag; "
        "datamark: error, auto)",
    )  # fmt: skip
    mark.add_argument(
        "--with-instruction", action="store_true",
        help="text output: print the instruction, one blank line, then the marked text "
        "(json output always includes the instruction)",
    )  # fmt: skip
    mark.add_argument("file", nargs="?", help="input file (default: stdin)")

    unmark = sub.add_parser(
        "unmark",
        help="recover the original text",
        description="Reverse `mark`. With --format json, the input is the JSON that "
        "`mark --format json` printed and its settings are used.",
    )
    _add_mode_options(unmark, required=False)
    unmark.add_argument("file", nargs="?", help="input file (default: stdin)")

    instr = sub.add_parser(
        "instruction",
        help="print the system-prompt instruction for a mode",
        description="Print the instruction that tells a model how the text is marked.",
    )
    _add_mode_options(instr)

    mjson = sub.add_parser(
        "mark-json",
        help="spotlight every untrusted string in a JSON document",
        description="Read a JSON document (a tool result, search hits) from FILE or stdin and "
        "spotlight every string value except trusted ones. Prints JSON with the marked value, "
        "one instruction for the whole document and the settings `unmark-json` needs.",
    )
    mjson.add_argument(
        "--mode", choices=MODES, default="datamark", help="delimit, datamark (default) or encode"
    )
    mjson.add_argument(
        "--trusted-key", action="append", default=[], metavar="KEY",
        help="leave values under this key unmarked, anywhere in the document (repeatable)",
    )  # fmt: skip
    mjson.add_argument(
        "--trusted-path", action="append", default=[], metavar="PATH",
        help="leave the value at this dotted path unmarked; * matches any list index (repeatable)",
    )  # fmt: skip
    mjson.add_argument(
        "--marker", default="auto",
        help="datamark marker (default 'auto': one that no untrusted string contains)",
    )  # fmt: skip
    mjson.add_argument("--start", default=DEFAULT_START, help="delimit start delimiter")
    mjson.add_argument("--end", default=DEFAULT_END, help="delimit end delimiter")
    mjson.add_argument("--scheme", choices=SCHEMES, default="base64", help="encode scheme")
    mjson.add_argument(
        "--skip-code", action="store_true", help="datamark: leave fenced code blocks unmarked"
    )
    mjson.add_argument("file", nargs="?", help="input JSON file (default: stdin)")

    ujson = sub.add_parser(
        "unmark-json",
        help="recover the original JSON document from mark-json output",
        description="Reverse `mark-json`: read its JSON output and print the original document.",
    )
    ujson.add_argument("file", nargs="?", help="mark-json output (default: stdin)")

    demo = sub.add_parser(
        "demo",
        help="show the three modes on a neutral sample paragraph",
        description="Show delimit, datamark and encode on a neutral sample paragraph.",
    )
    demo.add_argument("--format", choices=("text", "json"), default="text", help="output format")
    return parser


def _cmd_mark(args: argparse.Namespace) -> int:
    text = _read(args.file)
    collision = args.on_collision
    if args.mode == "delimit" and collision == "auto":
        raise SpotlightError("--on-collision auto applies to datamark; use tag for delimit")
    if args.mode == "datamark" and collision in ("allow", "tag"):
        raise SpotlightError("--on-collision for datamark is error or auto")
    result = spotlight(
        text,
        args.mode,
        marker=args.marker,
        start=args.start,
        end=args.end,
        scheme=args.scheme,
        skip_code=args.skip_code,
        on_collision=collision,
    )
    if args.format == "json":
        _dump(_as_json(result))
    else:
        prefix = result.instruction + "\n\n" if args.with_instruction else ""
        _write(prefix + (result.text if args.mode == "datamark" else result.text + "\n"))
    return EXIT_OK


def _cmd_unmark(args: argparse.Namespace) -> int:
    raw = _read(args.file)
    if args.format == "json":
        doc = _load_json(raw, args.file, "the JSON printed by `mark --format json`")
        if not isinstance(doc, dict):
            raise _InputError(
                f"{_name(args.file)}: expected the JSON object printed by `mark --format json`"
            )
        mode, text = _field(doc, "mode", args.file), _field(doc, "text", args.file)
        original = unmark_text(
            text, mode, marker=_field(doc, "marker", args.file, optional=True),
            end=_field(doc, "end", args.file, optional=True),
            skip_code=bool(doc.get("skip_code")),
        )  # fmt: skip
        _write(original)
        return EXIT_OK
    mode = args.mode
    text = raw
    if mode in ("delimit", "encode") and text.endswith("\n"):
        stripped = text[:-1]
        if mode == "encode" or stripped.endswith(args.end):
            text = stripped
    marker = {"delimit": args.start, "datamark": args.marker, "encode": args.scheme}[mode]
    _write(unmark_text(text, mode, marker=marker, end=args.end, skip_code=args.skip_code))
    return EXIT_OK


def _cmd_instruction(args: argparse.Namespace) -> int:
    marker = DEFAULT_MARKER if args.marker == "auto" else args.marker
    if args.mode == "datamark":
        if not marker:
            raise SpotlightError("the marker must not be empty")
        if any(ch.isspace() for ch in marker):
            raise SpotlightError("the marker must not contain whitespace")
    text = instruction(
        args.mode, start=args.start, end=args.end, marker=marker, scheme=args.scheme,
        skip_code=args.skip_code,
    )  # fmt: skip
    if args.format == "json":
        _dump({"mode": args.mode, "instruction": text})
    else:
        _write(text + "\n")
    return EXIT_OK


def _cmd_mark_json(args: argparse.Namespace) -> int:
    value = _load_json(_read(args.file), args.file, "a JSON document")
    result = Pipeline(
        args.mode,
        trusted_keys=args.trusted_key,
        trusted_paths=args.trusted_path,
        marker=args.marker,
        start=args.start,
        end=args.end,
        scheme=args.scheme,
        skip_code=args.skip_code,
    ).apply(value)
    _dump(
        {
            "mode": result.mode,
            "marker": result.marker,
            "end": result.end,
            "skip_code": result.skip_code,
            "trusted_keys": sorted(result.trusted_keys),
            "trusted_paths": sorted(result.trusted_paths),
            "instruction": result.instruction,
            "paths": list(result.paths),
            "value": result.value,
        }
    )
    return EXIT_OK


def _cmd_unmark_json(args: argparse.Namespace) -> int:
    doc = _load_json(_read(args.file), args.file, "the JSON printed by `mark-json`")
    bad = f"{_name(args.file)}: expected the JSON printed by `mark-json`"
    if not isinstance(doc, dict) or "value" not in doc:
        raise _InputError(bad)
    keys, paths = doc.get("trusted_keys", []), doc.get("trusted_paths", [])
    if not all(isinstance(v, list) and all(isinstance(x, str) for x in v) for v in (keys, paths)):
        raise _InputError(f"{bad}: trusted_keys and trusted_paths must be lists of strings")
    mode = _field(doc, "mode", args.file, printer="mark-json")
    if mode not in MODES:
        raise SpotlightError(f"unknown mode {mode!r}; expected one of {', '.join(MODES)}")
    result = PipelineResult(
        value=doc["value"],
        instruction="",
        mode=mode,  # type: ignore[arg-type]
        marker=_field(doc, "marker", args.file, printer="mark-json"),
        end=_field(doc, "end", args.file, optional=True, printer="mark-json"),
        skip_code=bool(doc.get("skip_code")),
        paths=(),
        trusted_keys=frozenset(keys),
        trusted_paths=frozenset(paths),
    )
    _dump(result.restore())
    return EXIT_OK


def demo_results() -> list[Spotlighted]:
    """The three spotlighted versions of `DEMO_TEXT` the demo shows."""
    return [
        spotlight(DEMO_TEXT, "delimit"),
        spotlight(DEMO_TEXT, "datamark"),
        spotlight(DEMO_TEXT, "encode", scheme="base64"),
    ]


def _cmd_demo(args: argparse.Namespace) -> int:
    results = demo_results()
    if args.format == "json":
        _dump({"input": DEMO_TEXT, "results": [_as_json(r) for r in results]})
        return EXIT_OK
    lines = ["spotlighting demo: one neutral paragraph, three modes", "", "input:"]
    lines += ["  " + line for line in DEMO_TEXT.splitlines()]
    for r in results:
        label = {
            "delimit": f"delimiters {r.marker} and {r.end}",
            "datamark": f"marker {r.marker}",
            "encode": f"scheme {r.marker}",
        }[r.mode]
        lines += ["", f"[{r.mode}] {label}", "instruction:"]
        lines += textwrap.wrap(r.instruction, width=88, initial_indent="  ", subsequent_indent="  ")
        lines += ["text:"] + ["  " + line for line in r.text.splitlines()]
    _write("\n".join(lines) + "\n")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "mark": _cmd_mark,
        "unmark": _cmd_unmark,
        "instruction": _cmd_instruction,
        "mark-json": _cmd_mark_json,
        "unmark-json": _cmd_unmark_json,
        "demo": _cmd_demo,
    }
    if args.command is None:
        parser.print_help()
        return EXIT_USAGE
    try:
        return handlers[args.command](args)
    except _InputError as exc:
        print(f"spotlighting: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except SpotlightError as exc:
        print(f"spotlighting: {exc}", file=sys.stderr)
        return EXIT_FAILED
    except UnicodeEncodeError as exc:
        print(
            f"spotlighting: the output contains a character that cannot be written as UTF-8 "
            f"(a lone surrogate, position {exc.start})",
            file=sys.stderr,
        )
        return EXIT_FAILED


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
