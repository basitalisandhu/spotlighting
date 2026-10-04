"""Repository hygiene: no attack text, no model names, no em dashes, docs agree with code."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import spotlighting

from .conftest import ROOT

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
}
FORBIDDEN_FILE = ROOT / "tests" / "forbidden.txt"


def repo_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        if path.is_file() and not (set(path.relative_to(ROOT).parts) & SKIP_DIRS):
            if ".egg-info" in str(path):
                continue
            files.append(path)
    return files


def forbidden_phrases() -> list[str]:
    lines = FORBIDDEN_FILE.read_text(encoding="utf-8").splitlines()
    return [line.strip().lower() for line in lines if line.strip() and not line.startswith("#")]


def test_forbidden_list_is_not_empty() -> None:
    assert len(forbidden_phrases()) >= 10


def test_no_file_contains_a_forbidden_phrase() -> None:
    phrases = forbidden_phrases()
    hits = []
    for path in repo_files():
        if path == FORBIDDEN_FILE:
            continue
        text = path.read_bytes().decode("utf-8", "ignore").lower()
        text = " ".join(text.split())
        hits += [f"{path.relative_to(ROOT)}: {p}" for p in phrases if p in text]
    assert hits == []


def test_no_em_dashes() -> None:
    hits = [
        str(p.relative_to(ROOT))
        for p in repo_files()
        if chr(0x2014) in p.read_bytes().decode("utf-8", "ignore")
    ]
    assert hits == []


def test_version_matches_pyproject() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == spotlighting.__version__
    assert data["project"]["dependencies"] == []


def test_changelog_has_current_version() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{spotlighting.__version__}] - 2026-10-04" in changelog


def test_py_typed_present() -> None:
    assert (ROOT / "src" / "spotlighting" / "py.typed").exists()


def test_readme_cites_the_paper() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "https://arxiv.org/abs/2403.14720" in readme
    assert re.search(r"^# Spotlighting for prompt injection defence in Python", readme, re.M)


def test_public_api_exported() -> None:
    for name in ("delimit", "datamark", "encode", "decode", "reverse", "spotlight", "Pipeline",
                 "Spotlighted", "for_tool_result", "for_fetched_page", "for_email"):  # fmt: skip
        assert name in spotlighting.__all__
