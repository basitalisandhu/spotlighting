"""Scaling checks: ten times the input must take roughly ten times as long, not a hundred.

Each pair is timed at 1x and 10x and the ratio is held under 30, which a linear
implementation meets with room for noisy CI machines and a quadratic one does not.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import pytest

from spotlighting import Pipeline, datamark, delimit, encode, reverse
from spotlighting.sources import html_to_text

BASE = "The build passed on all platforms.\n```py\nx = 1\n```\n" * 400
HTML = "<div><p>Meeting moved <b>to</b> 3pm.</p><script>x()</script></div>" * 1000
LIMIT = 30


def _best(fn: Callable[[], object]) -> float:
    times = []
    for _ in range(3):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return max(min(times), 1e-4)


def _doc(n: int) -> dict[str, object]:
    return {
        "hits": [{"id": i, "body": "Bring the draft agenda.", "tags": ["a b"]} for i in range(n)]
    }


CASES: dict[str, Callable[[int], Callable[[], object]]] = {
    "datamark": lambda k: lambda: datamark(BASE * k),
    "datamark-skip-code": lambda k: lambda: datamark(BASE * k, skip_code=True),
    "datamark-auto": lambda k: lambda: datamark(BASE * k + "^", marker="auto"),
    "reverse": lambda k: (lambda t: lambda: reverse(t, marker="^"))(datamark(BASE * k).text),
    "delimit-tag": lambda k: lambda: delimit(BASE * k + "<<", on_collision="tag"),
    "encode": lambda k: lambda: encode(BASE * k),
    "html_to_text": lambda k: lambda: html_to_text(HTML * k),
    "pipeline": lambda k: lambda: Pipeline(trusted_keys={"id"}).apply(_doc(200 * k)),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_ten_times_the_input_stays_near_linear(name: str) -> None:
    small, large = _best(CASES[name](1)), _best(CASES[name](10))
    assert large / small < LIMIT, f"{name}: 1x {small:.4f}s, 10x {large:.4f}s"
