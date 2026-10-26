from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
LATEX_DIR = ROOT / "paper" / "latex"


def test_figures_conversion_failure_cannot_fall_back_to_stale_pdf(tmp_path: Path) -> None:
    if shutil.which("make") is None:
        pytest.skip("make is not installed")

    workspace = tmp_path / "project" / "paper" / "latex"
    workspace.mkdir(parents=True)
    shutil.copy2(LATEX_DIR / "Makefile", workspace / "Makefile")
    scripts = workspace.parents[1] / "scripts"
    scripts.mkdir()
    (scripts / "generate_paper_figures.py").write_text("pass\n", encoding="utf-8")
    (scripts / "run_kg_ontology_simulation.py").write_text("pass\n", encoding="utf-8")
    figures = workspace / "figures"
    figures.mkdir()
    (figures / "sample.svg").write_text(
        "<svg xmlns='http://www.w3.org/2000/svg' />\n", encoding="utf-8"
    )
    stale_pdf = figures / "sample.pdf"
    stale_pdf.write_bytes(b"stale-pdf-from-previous-success")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    converter = fake_bin / "rsvg-convert"
    converter.write_text(
        "#!/bin/sh\nprintf '%s\\n' 'conversion failed' >&2\nexit 17\n", encoding="utf-8"
    )
    converter.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        ["make", "-o", "generated", "figures"],
        cwd=workspace,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert "conversion failed" in result.stderr
    assert stale_pdf.read_bytes() == b"stale-pdf-from-previous-success"
    assert not (figures / "sample.pdf.tmp").exists()


def _write_stub(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


@pytest.mark.parametrize(
    ("case", "expected_marker"),
    (
        ("pdfinfo_nonzero", None),
        ("missing_pages", "page count"),
        ("eleven_pages", "ceiling"),
        ("pdffonts_nonzero", None),
        ("type3_first_figure", "Type 3"),
    ),
)
def test_check_fails_closed_for_pdf_inspection_errors(
    tmp_path: Path,
    case: str,
    expected_marker: str | None,
) -> None:
    if shutil.which("make") is None:
        pytest.skip("make is not installed")

    workspace = tmp_path / "project" / "paper" / "latex"
    workspace.mkdir(parents=True)
    shutil.copy2(LATEX_DIR / "Makefile", workspace / "Makefile")
    figures = workspace / "figures"
    figures.mkdir()
    (figures / "sample.svg").write_text(
        "<svg xmlns='http://www.w3.org/2000/svg' />\n", encoding="utf-8"
    )
    (workspace / "en").mkdir()
    (workspace / "ko").mkdir()

    (workspace / "figures" / "sample.pdf").write_bytes(b"stub-pdf")
    for language in ("en", "ko"):
        (workspace / language / "main.pdf").write_bytes(b"stub-pdf")
        (workspace / language / "main.log").write_text("", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_stub(fake_bin / "uv", "#!/bin/sh\nexit 0\n")
    _write_stub(
        fake_bin / "rsvg-convert",
        "#!/usr/bin/env python3\n"
        "import pathlib, sys\n"
        "pathlib.Path(sys.argv[sys.argv.index('-o') + 1]).touch()\n",
    )
    _write_stub(
        fake_bin / "ps2pdf",
        "#!/usr/bin/env python3\nimport pathlib, sys\npathlib.Path(sys.argv[-1]).touch()\n",
    )
    _write_stub(
        fake_bin / "latexmk",
        "#!/bin/sh\n: > main.pdf\n: > main.log\n",
    )
    _write_stub(
        fake_bin / "pdfinfo",
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "mode = os.environ['CHECK_CASE']\n"
        "if mode == 'pdfinfo_nonzero': sys.exit(23)\n"
        "if mode == 'missing_pages': print('Producer: stub'); sys.exit(0)\n"
        "print('Pages: 11' if mode == 'eleven_pages' else 'Pages: 9')\n",
    )
    _write_stub(
        fake_bin / "pdffonts",
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "mode = os.environ['CHECK_CASE']\n"
        "if mode == 'pdffonts_nonzero': sys.exit(29)\n"
        "print('name type emb sub uni object ID')\n"
        "print('---')\n"
        "if mode == 'type3_first_figure' and sys.argv[-1].endswith('figures/sample.pdf'):\n"
        "    print('bad Type 3 no no no 1 0')\n"
        "else:\n"
        "    print('good TrueType yes yes yes 1 0')\n",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
    env["CHECK_CASE"] = case
    result = subprocess.run(
        ["make", "-o", "english", "-o", "korean", "check"],
        cwd=workspace,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    if expected_marker is not None:
        assert expected_marker.lower() in combined_output.lower()


LOG_PATHS = (
    "en/main.log",
    "ko/main.log",
    "en/traceability-supplement.log",
    "ko/traceability-supplement.log",
)


def _prepare_log_check_workspace(
    tmp_path: Path,
    log_contents: dict[str, str | None],
    *,
    scanner_status: int | None = None,
) -> tuple[Path, Path]:
    workspace = tmp_path / "project" / "paper" / "latex"
    workspace.mkdir(parents=True)
    shutil.copy2(LATEX_DIR / "Makefile", workspace / "Makefile")

    for directory in (workspace / "figures", workspace / "en", workspace / "ko"):
        directory.mkdir()
    for pdf in (
        workspace / "figures" / "sample.pdf",
        workspace / "en" / "main.pdf",
        workspace / "ko" / "main.pdf",
        workspace / "en" / "traceability-supplement.pdf",
        workspace / "ko" / "traceability-supplement.pdf",
    ):
        pdf.write_bytes(b"bounded pdf fixture\n")

    for relative_path, contents in log_contents.items():
        if contents is not None:
            (workspace / relative_path).write_text(contents, encoding="utf-8")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_stub(fake_bin / "pdfinfo", "#!/bin/sh\nprintf '%s\\n' 'Pages: 9'\n")
    _write_stub(
        fake_bin / "pdffonts",
        "#!/bin/sh\n"
        "printf '%s\\n' 'name type emb sub uni object ID'\n"
        "printf '%s\\n' '---'\n"
        "printf '%s\\n' 'fixture TrueType yes yes yes 1 0'\n",
    )
    if scanner_status is not None:
        _write_stub(fake_bin / "grep", f"#!/bin/sh\nexit {scanner_status}\n")

    return workspace, fake_bin


def _run_log_check(workspace: Path, fake_bin: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
    return subprocess.run(
        [
            "make",
            "-o",
            "generated",
            "-o",
            "figures",
            "-o",
            "english",
            "-o",
            "korean",
            "-o",
            "supplements",
            "check",
        ],
        cwd=workspace,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _clean_logs(contents: str) -> dict[str, str | None]:
    return {relative_path: contents for relative_path in LOG_PATHS}


def test_check_accepts_four_clean_logs(tmp_path: Path) -> None:
    workspace, fake_bin = _prepare_log_check_workspace(
        tmp_path,
        _clean_logs("Compilation completed without diagnostics.\n"),
    )

    result = _run_log_check(workspace, fake_bin)

    assert result.returncode == 0


def test_check_rejects_forbidden_log_diagnostic(tmp_path: Path) -> None:
    logs = _clean_logs("Compilation completed without diagnostics.\n")
    logs["en/main.log"] = "LaTeX Error: fixture failure\n"
    workspace, fake_bin = _prepare_log_check_workspace(tmp_path, logs)

    result = _run_log_check(workspace, fake_bin)

    assert result.returncode != 0
    assert "Paper logs contain forbidden diagnostics" in result.stdout + result.stderr


def test_check_rejects_missing_log_with_scanner_diagnostic(tmp_path: Path) -> None:
    logs = _clean_logs("Compilation completed without diagnostics.\n")
    logs["ko/traceability-supplement.log"] = None
    workspace, fake_bin = _prepare_log_check_workspace(tmp_path, logs)

    result = _run_log_check(workspace, fake_bin)

    assert result.returncode != 0
    assert "Paper log scan could not complete (status 2)" in result.stdout + result.stderr


@pytest.mark.parametrize(
    "scanner_status",
    (2, 127),
    ids=("scanner-error", "scanner-unavailable"),
)
def test_check_rejects_scanner_error_status(
    tmp_path: Path,
    scanner_status: int,
) -> None:
    workspace, fake_bin = _prepare_log_check_workspace(
        tmp_path,
        _clean_logs("Compilation completed without diagnostics.\n"),
        scanner_status=scanner_status,
    )

    result = _run_log_check(workspace, fake_bin)

    assert result.returncode != 0
    assert (
        f"Paper log scan could not complete (status {scanner_status})"
        in result.stdout + result.stderr
    )
