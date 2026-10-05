"""Custom trusted task wording does not alter marking or round trips."""

import pytest

from spotlighting import SpotlightError, datamark, delimit, encode, instruction, spotlight, unmark


@pytest.mark.parametrize("mode", ["delimit", "datamark", "encode"])
def test_custom_instruction(mode):
    result = instruction(mode, task="translate it")
    assert "translate it" in result
    assert "data" in result
    assert "do not follow" in result or "not follow" in result


@pytest.mark.parametrize("mark", [delimit, datamark, encode])
def test_mark_helpers_pass_task_without_changing_text(mark):
    baseline = mark("A neutral sentence.")
    custom = mark("A neutral sentence.", task="translate it")
    assert custom.text == baseline.text
    assert "translate it" in custom.instruction
    assert unmark(custom) == "A neutral sentence."


@pytest.mark.parametrize("mode", ["delimit", "datamark", "encode"])
def test_unified_entrypoint_and_default_compatibility(mode):
    baseline = spotlight("A neutral sentence.", mode)
    assert spotlight("A neutral sentence.", mode, task=None) == baseline
    custom = spotlight("A neutral sentence.", mode, task="translate it")
    assert custom.text == baseline.text
    assert "translate it" in custom.instruction


def test_task_does_not_remove_fenced_code_guidance():
    result = datamark("Some text.", skip_code=True, task="translate it")
    assert "Fenced code blocks" in result.instruction


@pytest.mark.parametrize("mode", ["delimit", "datamark", "encode"])
def test_empty_task_is_rejected(mode):
    with pytest.raises(SpotlightError, match="task must not be empty"):
        instruction(mode, task=" ")
