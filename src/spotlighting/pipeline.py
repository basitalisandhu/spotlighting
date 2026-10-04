"""Spotlight every untrusted string in a nested structure, leaving trusted fields alone.

Use it on a tool result, a list of search hits or a parsed email before the structure is
serialised into a prompt. Fields are trusted only by an explicit allowlist: by key name
anywhere in the structure (`trusted_keys`) or by exact path (`trusted_paths`, dotted, with
``*`` matching any list index). Everything else that is a string is marked; numbers, booleans
and ``None`` are left as they are. Dictionary keys are not marked.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from .marks import (
    DEFAULT_END,
    DEFAULT_MARKER,
    DEFAULT_START,
    MarkerCollision,
    Mode,
    Scheme,
    SpotlightError,
    choose_marker,
    instruction,
    spotlight,
    unmark_text,
)


def _path(parent: str, part: str | int) -> str:
    if isinstance(part, int):
        return f"{parent}.*" if parent else "*"
    return f"{parent}.{part}" if parent else part


@dataclass(frozen=True)
class PipelineResult:
    """The marked structure, the one instruction that covers it, and the paths that were marked."""

    value: Any
    instruction: str
    mode: Mode
    marker: str
    end: str | None
    skip_code: bool
    paths: tuple[str, ...]
    trusted_keys: frozenset[str] = field(repr=False, default=frozenset())
    trusted_paths: frozenset[str] = field(repr=False, default=frozenset())

    def restore(self) -> Any:
        """The original structure, with every marked string unmarked."""

        def undo(text: str) -> str:
            return unmark_text(
                text, self.mode, marker=self.marker, end=self.end, skip_code=self.skip_code
            )

        return _map(self.value, undo, self.trusted_keys, self.trusted_paths, "", [])


def _map(
    value: Any,
    fn: Callable[[str], str],
    trusted_keys: frozenset[str],
    trusted_paths: frozenset[str],
    path: str,
    seen: list[str],
) -> Any:
    if isinstance(value, str):
        seen.append(path or "$")
        return fn(value)
    if isinstance(value, dict):
        out: dict[Any, Any] = {}
        for key, item in value.items():
            child = _path(path, str(key))
            if str(key) in trusted_keys or child in trusted_paths:
                out[key] = item
            else:
                out[key] = _map(item, fn, trusted_keys, trusted_paths, child, seen)
        return out
    if isinstance(value, list | tuple):
        child = _path(path, 0)
        if child in trusted_paths:
            return value
        items = [_map(item, fn, trusted_keys, trusted_paths, child, seen) for item in value]
        return items if isinstance(value, list) else tuple(items)
    return value


def _strings(value: Any, trusted_keys: frozenset[str], trusted_paths: frozenset[str]) -> list[str]:
    found: list[str] = []

    def keep(text: str) -> str:
        found.append(text)
        return text

    _map(value, keep, trusted_keys, trusted_paths, "", [])
    return found


class Pipeline:
    """Apply one spotlighting mode to every untrusted string in a dict or list.

    One marker is chosen for the whole structure so that one instruction covers it. With
    ``marker="auto"`` (the default for datamarking here) the first marker that occurs in none
    of the untrusted strings is used. Delimiters must not occur in any untrusted string.
    """

    def __init__(
        self,
        mode: Mode = "datamark",
        *,
        trusted_keys: Iterable[str] = (),
        trusted_paths: Iterable[str] = (),
        marker: str = "auto",
        start: str = DEFAULT_START,
        end: str = DEFAULT_END,
        scheme: Scheme = "base64",
        skip_code: bool = False,
    ) -> None:
        if mode not in ("delimit", "datamark", "encode"):
            raise SpotlightError(f"unknown mode {mode!r}")
        self.mode: Mode = mode
        self.trusted_keys = frozenset(trusted_keys)
        self.trusted_paths = frozenset(trusted_paths)
        self.marker = marker
        self.start = start
        self.end = end
        self.scheme: Scheme = scheme
        self.skip_code = skip_code

    def apply(self, value: Any) -> PipelineResult:
        """Return the structure with every untrusted string spotlighted."""
        strings = _strings(value, self.trusted_keys, self.trusted_paths)
        marker = self.marker
        end: str | None = None
        if self.mode == "datamark":
            marker = choose_marker(strings) if marker == "auto" else marker
            text = instruction("datamark", marker=marker, skip_code=self.skip_code)
        elif self.mode == "delimit":
            marker, end = self.start, self.end
            if any(marker in s or end in s for s in strings):
                raise MarkerCollision(
                    f"an untrusted field contains {marker!r} or {end!r}; choose other delimiters"
                )
            text = instruction("delimit", start=marker, end=end)
        else:
            marker = self.scheme
            text = instruction("encode", scheme=self.scheme)

        def mark(item: str) -> str:
            return spotlight(
                item,
                self.mode,
                marker=marker if self.mode == "datamark" else DEFAULT_MARKER,
                start=self.start,
                end=self.end,
                scheme=self.scheme,
                skip_code=self.skip_code,
            ).text

        paths: list[str] = []
        marked = _map(value, mark, self.trusted_keys, self.trusted_paths, "", paths)
        return PipelineResult(
            value=marked,
            instruction=text,
            mode=self.mode,
            marker=marker,
            end=end,
            skip_code=self.skip_code,
            paths=tuple(paths),
            trusted_keys=self.trusted_keys,
            trusted_paths=self.trusted_paths,
        )
