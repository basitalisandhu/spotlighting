"""End-to-end: build the wheel, install it in a fresh venv and run the README quick start.

The console block at the top of README.md and the Python Quickstart block are run exactly as
written (with `pipx install` replaced by installing the freshly built wheel) and the console
output must match the README byte for byte. Building needs the network for the build backend,
so the test runs only when SPOTLIGHTING_E2E=1; CI sets it in the `quickstart` job.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import venv
from pathlib import Path

import pytest

from .conftest import ROOT

pytestmark = pytest.mark.skipif(
    os.environ.get("SPOTLIGHTING_E2E") != "1", reason="set SPOTLIGHTING_E2E=1 to run"
)

README = (ROOT / "README.md").read_text(encoding="utf-8")


def _block(lang: str, after: str) -> str:
    start = README.index(after)
    match = re.search(rf"```{lang}\n(.*?)```", README[start:], re.S)
    assert match, f"no ```{lang} block after {after!r}"
    return match.group(1)


@pytest.fixture(scope="module")
def fresh_env(tmp_path_factory: pytest.TempPathFactory) -> Path:
    base = tmp_path_factory.mktemp("e2e")
    dist = base / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist), str(ROOT)],
        check=True,
        capture_output=True,
    )
    env_dir = base / "venv"
    venv.create(env_dir, with_pip=True)
    bin_dir = env_dir / ("Scripts" if os.name == "nt" else "bin")
    wheel = next(dist.glob("spotlighting-*.whl"))
    subprocess.run(
        [str(bin_dir / "python"), "-m", "pip", "install", "-q", str(wheel)],
        check=True,
        capture_output=True,
    )
    return bin_dir


def test_readme_console_quick_start(fresh_env: Path, tmp_path: Path) -> None:
    lines = _block("console", "# Spotlighting").splitlines()
    commands = [i for i, line in enumerate(lines) if line.startswith("$ ")]
    assert lines[commands[0]].startswith("$ pipx install ")
    run, expected = lines[commands[1]][2:], "\n".join(lines[commands[1] + 1 :]) + "\n"
    env = {"PATH": f"{fresh_env}{os.pathsep}/usr/bin:/bin", "LC_ALL": "C.UTF-8"}
    out = subprocess.run(
        ["bash", "-c", run], cwd=tmp_path, env=env, capture_output=True, check=True
    )
    assert out.stdout.decode("utf-8") == expected


def test_readme_python_quickstart(fresh_env: Path, tmp_path: Path) -> None:
    code = _block("python", "## Quickstart")
    script = tmp_path / "quickstart.py"
    script.write_text(
        'tool_output_text = "Meeting moved to 3pm.\\nBring the draft agenda.\\n"\n'
        + code
        + "assert original == tool_output_text\n"
        + "assert result.instruction in messages[0]['content']\n"
        + "print(result.text)\n",
        encoding="utf-8",
    )
    out = subprocess.run(
        [str(fresh_env / "python"), "-I", str(script)],
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    assert "Meeting^moved^to^3pm." in out.stdout.decode("utf-8")


def test_installed_command_marks_json(fresh_env: Path, tmp_path: Path) -> None:
    src = tmp_path / "hits.json"
    src.write_text('{"id": "a1", "body": "Bring the draft agenda."}', encoding="utf-8")
    exe = fresh_env / "spotlighting"
    marked = subprocess.run(
        [str(exe), "mark-json", "--trusted-key", "id", str(src)], capture_output=True, check=True
    ).stdout
    restored = subprocess.run(
        [str(exe), "unmark-json"], input=marked, capture_output=True, check=True
    ).stdout
    assert b'"body": "Bring^the^draft^agenda."' in marked
    assert b'"body": "Bring the draft agenda."' in restored
