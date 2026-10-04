"""Shared sample texts. Every sample is a neutral sentence; none is attack text."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SAMPLES: dict[str, str] = {
    "empty": "",
    "one_word": "hello",
    "sentence": "The meeting moved to Thursday at ten.",
    "multiline": "First line of the note.\nSecond line.\n\nA new paragraph.\n",
    "crlf": "Line one\r\nLine two\r\n",
    "tabs": "name\tvalue\tunit\n",
    "unicode": "Caf\u00e9 au lait co\u00fbte 3\u00a0\u20ac, na\u00efve r\u00e9sum\u00e9.",
    "cjk": "\u4eca\u65e5\u306f\u6674\u308c\u3067\u3059\u3002\u3000\u660e\u65e5\u3082\u3002",
    "emoji": "Shipped \U0001f680 on time \U0001f389 with the team \U0001f469\u200d\U0001f4bb.",
    "rtl": "\u0645\u0631\u062d\u0628\u0627 \u0628\u0627\u0644\u0639\u0627\u0644\u0645 hello",
    "leading_trailing": "   padded text   ",
    "only_spaces": "     ",
    "only_newlines": "\n\n\n",
    "mixed_ws": "a \u2003b\u2028c\u0085d\x0be\x0cf",
    "long": ("The weather report for the coast is mild and dry. " * 4000).strip(),
}
