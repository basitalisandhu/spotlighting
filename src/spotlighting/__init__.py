"""spotlighting: mark untrusted text before it reaches a model, with the matching instruction.

Delimiting, datamarking and encoding as described in Hines et al., "Defending Against Indirect
Prompt Injection Attacks With Spotlighting" (2024), https://arxiv.org/abs/2403.14720, plus the
system-prompt instruction for each mode. Standard library only.
"""

from __future__ import annotations

from .marks import (
    AUTO_MARKERS,
    DEFAULT_END,
    DEFAULT_MARKER,
    DEFAULT_START,
    MODES,
    SCHEMES,
    MarkerCollision,
    Mode,
    Prompt,
    Scheme,
    Spotlighted,
    SpotlightError,
    choose_marker,
    content_tag,
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
from .pipeline import Pipeline, PipelineResult
from .sources import for_email, for_fetched_page, for_tool_result, header_value, html_to_text

__version__ = "0.1.0"

__all__ = [
    "AUTO_MARKERS",
    "DEFAULT_END",
    "DEFAULT_MARKER",
    "DEFAULT_START",
    "MODES",
    "SCHEMES",
    "MarkerCollision",
    "Mode",
    "Pipeline",
    "PipelineResult",
    "Prompt",
    "Scheme",
    "SpotlightError",
    "Spotlighted",
    "__version__",
    "choose_marker",
    "content_tag",
    "datamark",
    "decode",
    "delimit",
    "encode",
    "for_email",
    "for_fetched_page",
    "for_tool_result",
    "header_value",
    "html_to_text",
    "instruction",
    "reverse",
    "spotlight",
    "undelimit",
    "unmark",
    "unmark_text",
]
