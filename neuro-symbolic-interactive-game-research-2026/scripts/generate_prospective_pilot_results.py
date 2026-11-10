#!/usr/bin/env python3
"""Reconcile a prospective-pilot collection manifest and write its summary and text fragments.

The summary is derived only from the retained raw rows (never from a count a row list merely
claims), and the generated TeX is text-only: no table, equation or figure and no outcome value
that was not observed. A null stays null. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from nesy_game import prospective_pilot as pilot

DEFAULT_STUDY = ROOT / "research" / pilot.STUDY_ID
DEFAULT_TEX = ROOT / "paper/latex/generated/prospective-pilot"
_COUNT_KEYS = ("planned", "blocked", "assigned", "attempted", "executed")


def _tt(text: str) -> str:
    return "\\texttt{\\detokenize{" + text + "}}"


def _show(value: Any, null_text: str) -> str:
    if value is None:
        return null_text
    return f"{value:.4g}" if isinstance(value, float) else str(value)


def _fragment(summary: dict[str, Any], collection: dict[str, Any], language: str) -> str:
    counts, tracks = summary["counts"], summary["tracks"]
    starts = sum(row["native_process_starts"] for row in collection["rows"])
    reasons = Counter(reason for row in collection["rows"] for reason in row["blocked_reasons"])
    listed = ", ".join(f"{_tt(code)} ({count})" for code, count in sorted(reasons.items()))
    study, status, conclusion = (
        _tt(summary["study_id"]),
        _tt(summary["status"]),
        _tt(summary["conclusion"]),
    )
    null = "null"
    rate = _show(summary["success_rate"], null)
    cost = _show(summary["observed_cost"], null)
    subtotal = _show(summary["known_cost_subtotal"], null)
    effect = _show(summary["effect_estimate"], null)
    if language == "en":
        paragraphs = [
            (
                "\\textbf{Prospective pilot status: not a model comparison.} The frozen study "
                f"{study} plans {counts['planned']} units ({tracks['runtime']['planned']} runtime and "
                f"{tracks['development']['planned']} development) over three requested targets. "
                f"{counts['blocked']} are blocked, {counts['assigned']} assigned, {counts['attempted']} "
                f"attempted and {counts['executed']} executed, with {starts} native process starts. "
                f"Status {status}; scientific conclusion {conclusion}."
            ),
            (
                f"Success rate: {rate}. Observed cost: {cost} (known subtotal {subtotal}; "
                f"{summary['unknown_cost_units']} admitted units with unknown cost). Effect estimate: "
                f"{effect}. A null is an absent measurement, never zero."
            ),
            f"Blocked prerequisites, counted per unit: {listed}.",
            (
                "The earlier eight-row 5/8 pilot, the stopped identity extension, the Ollama lane, the "
                "deterministic fixtures and the n=1 results are separate lanes. They are neither pooled "
                "nor re-reported here."
            ),
        ]
    else:
        paragraphs = [
            (
                "\\textbf{전향 파일럿 상태: 모델 비교가 아님.} 고정된 연구 "
                f"{study}는 요청된 세 target에 걸쳐 {counts['planned']}개 단위(런타임 "
                f"{tracks['runtime']['planned']}개, 개발 {tracks['development']['planned']}개)를 계획한다. "
                f"{counts['blocked']}개 차단, {counts['assigned']}개 배정, {counts['attempted']}개 시도, "
                f"{counts['executed']}개 실행이며 native 프로세스 시작은 {starts}회이다. "
                f"상태 {status}; 과학적 결론 {conclusion}."
            ),
            (
                f"성공률: {rate}. 관측 비용: {cost} (알려진 부분합 {subtotal}; 비용을 알 수 없는 "
                f"배정 단위 {summary['unknown_cost_units']}개). 효과 추정: {effect}. null은 측정이 "
                "없다는 뜻이며 0이 아니다."
            ),
            f"차단된 선결 조건(단위별 집계): {listed}.",
            (
                "이전 8행 5/8 파일럿, 중단된 신원 확장, Ollama 레인, 결정적 fixture, n=1 결과는 별도 "
                "레인이다. 여기서 합산하거나 다시 보고하지 않는다."
            ),
        ]
    return "\n\n".join(paragraphs) + "\n"


def _validate_destinations(paths: tuple[Path, ...]) -> None:
    """Preflight the entire output set before creating directories or writing any file."""
    protected = tuple(
        (ROOT / name).resolve()
        for name in (
            "research",
            "runs",
            "data",
            "knowledge",
            "_workspace",
            "game-track",
            "paper",
            "docs",
        )
    )
    protected += (
        (ROOT.parent / "_workspace").resolve(),
        (Path.home() / ".local/share/nesy-prospective-trust").resolve(),
    )
    summary = (DEFAULT_STUDY / "results-v1/summary.json").resolve()
    fragments = {(DEFAULT_TEX / f"status_{language}.tex").resolve() for language in ("en", "ko")}
    for path in paths:
        absolute = path.absolute()
        for entry in (absolute, *absolute.parents):
            if entry.is_symlink():
                raise ValueError(f"output destination contains a symlink: {entry}")
            if entry != absolute and entry.exists() and not entry.is_dir():
                raise ValueError(f"output ancestor is not a directory: {entry}")
        resolved = absolute.resolve()
        # Only this study's summary and two generated fragments are mutable in these roots.
        for root in protected:
            if (resolved == root or resolved.is_relative_to(root)) and not (
                (root == (ROOT / "research").resolve() and resolved == summary)
                or (root == (ROOT / "paper").resolve() and resolved in fragments)
            ):
                raise ValueError(f"output destination is protected evidence: {path}")
        if absolute.exists() and not absolute.is_file():
            raise ValueError(f"output destination is not a regular file: {path}")


def generate_results(protocol: dict, collection: dict, output_dir: Path, tex_dir: Path) -> dict:
    if not isinstance(collection, dict) or not isinstance(collection.get("rows"), list):
        raise TypeError("collection must carry a rows list")
    summary = pilot.reconcile_results(protocol, collection["rows"])
    declared = collection.get("counts")
    if (
        not isinstance(declared, dict)
        or set(declared) != set(_COUNT_KEYS)
        or any(declared[key] != summary["counts"][key] for key in _COUNT_KEYS)
    ):
        raise ValueError("collection counts do not match its raw rows")
    if collection.get("native_process_starts") != sum(
        row["native_process_starts"] for row in collection["rows"]
    ):
        raise ValueError("collection native_process_starts does not match its raw rows")
    if collection.get("protocol_sha256") not in (None, pilot.protocol_sha256(protocol)):
        raise ValueError("collection was produced for a different protocol")
    out, tex = Path(output_dir), Path(tex_dir)
    text = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    target = out / "summary.json"
    destinations = (target, *(tex / f"status_{language}.tex" for language in ("en", "ko")))
    _validate_destinations(destinations)
    if target.exists() and target.read_text(encoding="utf-8") != text:
        raise ValueError(f"{target} exists with different content; results are never overwritten")
    out.mkdir(parents=True, exist_ok=True)
    tex.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    for language in ("en", "ko"):
        (tex / f"status_{language}.tex").write_text(
            _fragment(summary, collection, language), encoding="utf-8"
        )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_STUDY / "protocol-v1.json")
    parser.add_argument(
        "--collection", type=Path, default=DEFAULT_STUDY / "results-v1/collection-status.json"
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_STUDY / "results-v1")
    parser.add_argument("--tex-dir", type=Path, default=DEFAULT_TEX)
    args = parser.parse_args(argv)
    try:
        summary = generate_results(
            pilot.load_json_file(args.protocol),
            pilot.load_json_file(args.collection),
            args.output_dir,
            args.tex_dir,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(
            f"generate_prospective_pilot_results: {type(error).__name__}: {error}", file=sys.stderr
        )
        return 1
    print(
        json.dumps(
            {
                "status": summary["status"],
                "conclusion": summary["conclusion"],
                "summary": str(args.output_dir / "summary.json"),
                "tex_dir": str(args.tex_dir),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
