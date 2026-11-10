#!/usr/bin/env python3
"""Thin fail-closed CLI over ``nesy_game.prospective_pilot``.

Every subcommand prints one JSON receipt (also written to ``--receipt`` when given, and never
over an existing file). Exit codes: 0 PASS, 1 FAIL, 3 BLOCKED or UNRESOLVED, 2 usage.
No subcommand calls a model, an SDK, an account/credential probe or a native inference host;
``preflight --metadata-only`` runs only the four frozen version/help argv. The live runtime
runner and the development broker loop are NOT implemented, so ``collect`` can only produce a
blocked manifest with zero native processes.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nesy_game import prospective_pilot as pilot

EXIT = {"PASS": 0, "FAIL": 1, "BLOCKED": 3, "UNRESOLVED": 3}
DEFAULT_STUDY = ROOT / "research" / pilot.STUDY_ID
DEFAULT_PREFIX = "neuro-symbolic-interactive-game-research-2026/"
PROTOCOL, UNITS, TASKS, SOURCES, BROKER, PUBLIC, LEDGER = (
    "protocol-v1.json",
    "planned-units-v1.json",
    "task-manifest-v1.json",
    "source-manifest-v1.json",
    "broker-v1.json",
    "public-input-manifest-v1.json",
    "derivation-ledger-v1.json",
)


class Blocked(Exception):
    def __init__(self, reasons: list[str]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = reasons


def _read(path: Path | str, ctx: dict[str, Any]) -> Any:
    data = Path(path).read_bytes()
    ctx["inputs"][str(path)] = pilot.sha256_hex(data)
    return pilot.strict_json_loads(data.decode("utf-8"), allow_whitespace=True)


def _write_new(path: Path, value: Any, ctx: dict[str, Any], mode: int = 0o644) -> str:
    """Exclusive create: an evidentiary file is never overwritten."""
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)
    ctx["outputs"][str(path)] = digest = pilot.sha256_hex(text)
    return digest


def _git(git_root: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
    env = {"PATH": os.environ.get("PATH", ""), "LC_ALL": "C", "GIT_OPTIONAL_LOCKS": "0"}
    return subprocess.run(
        ["git", "-C", str(git_root), *argv],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        env=env,
        timeout=30,
        check=False,
    )


def _safe_relative(path: Any) -> str:
    if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/"):
        raise ValueError(f"unsafe relative path {path!r}")
    return path


# ---------------------------------------------------------------- prepare
def cmd_prepare(args: argparse.Namespace, ctx: dict[str, Any]) -> tuple[str, dict]:
    study = args.study_root
    if study.exists() and any(study.iterdir()):
        raise ValueError("study root must be fresh: prepared files are never overwritten")
    reasons = [
        f"--{name} missing or not a directory"
        for name, path in (
            ("task-root", args.task_root),
            ("source-root", args.source_root),
            ("git-root", args.git_root),
        )
        if path is None or not path.is_dir()
    ]
    if reasons:
        raise Blocked(reasons)
    prefix = args.tree_prefix
    commit = _git(args.git_root, "rev-parse", "--verify", f"{pilot.SOURCE_COMMIT}^{{commit}}")
    if commit.returncode != 0 or commit.stdout.decode().strip() != pilot.SOURCE_COMMIT:
        raise Blocked(["BLOCKED_SOURCE_COMMIT_UNAVAILABLE: pinned commit object absent locally"])

    def blob(path: str) -> str | None:
        found = _git(
            args.git_root, "rev-parse", "--verify", f"{pilot.SOURCE_COMMIT}:{prefix}{path}"
        )
        return found.stdout.decode().strip() if found.returncode == 0 else None

    bundle = args.task_root
    if any(path.is_symlink() for path in (bundle, *bundle.parents)):
        raise ValueError(f"task bundle contains a symlink: {bundle}")
    manifest_path = bundle / "task-manifest.json"
    if not manifest_path.is_file():
        raise Blocked(
            ["BLOCKED_TASK_FREEZE_INCOMPLETE: the external task bundle has no task-manifest.json"]
        )
    manifest = _read(manifest_path, ctx)
    entries = {e["task_id"]: e for e in manifest["tasks"]}
    specs, task_rows, source_rows = [], [], []
    for task_id in pilot.TASK_IDS:
        entry = entries.get(task_id)
        if entry is None:
            raise Blocked([f"BLOCKED_TASK_FREEZE_INCOMPLETE: task-manifest lacks {task_id}"])
        spec_path = bundle / task_id / "task-spec.json"
        if not spec_path.is_file():
            raise Blocked([f"BLOCKED_TASK_FREEZE_INCOMPLETE: {task_id}/task-spec.json absent"])
        spec = _read(spec_path, ctx)
        if (
            spec.get("task_id") != task_id
            or spec.get("source_commit") != pilot.SOURCE_COMMIT
            or entry.get("source_commit") != pilot.SOURCE_COMMIT
        ):
            raise ValueError(f"{task_id}: not bound to the pinned source commit")
        target = _safe_relative(spec.get("target_file"))
        try:
            source_bytes = (args.source_root / target).read_bytes()
        except OSError as error:
            raise Blocked(
                [f"BLOCKED_SOURCE_COMMIT_UNAVAILABLE: {target}: {error.__class__.__name__}"]
            ) from error
        source_sha = pilot.sha256_hex(source_bytes)
        pinned = blob(target)
        if pinned is None:
            raise Blocked(
                [f"BLOCKED_SOURCE_COMMIT_UNAVAILABLE: {target} absent from the pinned tree"]
            )
        if pinned != pilot.git_blob_id(source_bytes) or entry.get("source_sha256") != source_sha:
            raise ValueError(f"{task_id}: source bytes are not the pinned commit's blob")
        pilot.validate_task_source_binding(
            bundle / task_id / "baseline" / target,
            bundle / task_id / "corpus-overlay" / target,
            {
                "source_commit": pilot.SOURCE_COMMIT,
                "baseline_sha256": spec.get("baseline_sha256"),
                "source_sha256": source_sha,
            },
        )
        if entry.get("baseline_sha256") != spec.get("baseline_sha256"):
            raise ValueError(f"{task_id}: manifest and spec baseline hashes differ")
        interfaces = []
        for relative in pilot.interface_paths(spec):
            relative = _safe_relative(relative)
            if relative == target:
                interfaces.append(
                    {
                        "path": relative,
                        "sha256": source_sha,
                        "matches_pinned_blob": True,
                        "model_input": "baseline",
                        "baseline_sha256": spec["baseline_sha256"],
                    }
                )
                continue
            data = (bundle / task_id / "interfaces" / relative).read_bytes()
            if blob(relative) != pilot.git_blob_id(data):
                raise ValueError(f"{task_id}: interface is not the pinned source blob: {relative}")
            interfaces.append(
                {"path": relative, "sha256": pilot.sha256_hex(data), "matches_pinned_blob": True}
            )
        specs.append(spec)
        source_rows.append(
            {
                "task_id": task_id,
                "target_file": target,
                "source_sha256": source_sha,
                "git_blob": pinned,
                "baseline_sha256": spec["baseline_sha256"],
                "interfaces": interfaces,
            }
        )
        task_rows.append(
            {
                "task_id": task_id,
                "spec_sha256": ctx["inputs"][str(spec_path)],
                "baseline_sha256": spec["baseline_sha256"],
                "source_sha256": source_sha,
                "determinacy_sha256": entry.get("determinacy_sha256"),
                "logic_auditor": None,
                "bundle_reported_freeze_status": entry.get("freeze_status"),
                # The public record never attests a freeze; verify-task-oracles does.
                "freeze_status": "BLOCKED_TASK_FREEZE_INCOMPLETE",
            }
        )
    files, classified = [], {}
    for directory, dirs, names in os.walk(bundle):
        dirs.sort()
        for name in dirs:
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError(f"task bundle contains a symlink: {path}")
        for name in sorted(names):
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError(f"task bundle contains a symlink: {path}")
            relative = path.relative_to(bundle).as_posix()
            parts = relative.split("/")
            if len(parts) > 2 and parts[1] in ("baseline", "corpus-overlay"):
                kind = "PUBLIC_DERIVED"
            elif len(parts) > 2 and parts[1] == "interfaces":
                interface = next(
                    (i for i in source_rows if i["task_id"] == parts[0]), {"interfaces": []}
                )["interfaces"]
                match = next((i for i in interface if i["path"] == "/".join(parts[2:])), None)
                kind = "PUBLIC_BLOB" if match and match["matches_pinned_blob"] else "NEW_AUTHORED"
            else:
                kind = "NEW_AUTHORED"
            digest = pilot.sha256_hex(path.read_bytes())
            files.append({"path": f"tasks/{relative}", "classification": kind, "sha256": digest})
            classified[relative] = digest
    protocol = pilot.build_protocol(specs)
    report = pilot.validate_protocol(protocol)
    for task in protocol["tasks"]:
        task_rows[pilot.TASK_IDS.index(task["task_id"])].update(
            semantic_sha256=pilot.sha256_hex(pilot.canonical_json(task["semantic"])),
            context_hashes=task["context_hashes"],
        )
    shutil.copytree(bundle, study / "tasks", symlinks=False)
    for relative, digest in classified.items():
        if pilot.sha256_hex((study / "tasks" / relative).read_bytes()) != digest:
            raise ValueError(f"copied bundle file changed in transit: {relative}")
    _write_new(study / PROTOCOL, protocol, ctx)
    _write_new(
        study / UNITS,
        {
            "schema": "prospective-pilot-planned-units/v1",
            "study_id": pilot.STUDY_ID,
            "protocol_sha256": report["protocol_sha256"],
            "units": protocol["units"],
        },
        ctx,
    )
    _write_new(
        study / TASKS,
        {
            "schema": "prospective-pilot-task-manifest/v1",
            "study_id": pilot.STUDY_ID,
            "source_commit": pilot.SOURCE_COMMIT,
            "tasks": task_rows,
        },
        ctx,
    )
    _write_new(
        study / SOURCES,
        {
            "schema": "prospective-pilot-source-manifest/v1",
            "source_commit": pilot.SOURCE_COMMIT,
            "git_root_verified": True,
            "tree_prefix": prefix,
            "tasks": source_rows,
        },
        ctx,
    )
    _write_new(
        study / PUBLIC,
        {"schema": "prospective-pilot-public-input-manifest/v1", "files": files},
        ctx,
    )
    _write_new(
        study / LEDGER,
        {
            "schema": "prospective-pilot-derivation-ledger/v1",
            "approved": False,
            "programs": {},
            "blocked_reason": "BLOCKED_PUBLIC_DERIVED_UNAPPROVED",
        },
        ctx,
    )
    _write_new(study / BROKER, pilot.BROKER, ctx)
    return "PASS", {
        "protocol_sha256": report["protocol_sha256"],
        "units": report["units"],
        "tasks": report["tasks"],
        "bundle_files": len(files),
        "note": "public derivation/new-authored approval and activation remain absent",
    }


# ---------------------------------------------------------------- validate-protocol
def cmd_validate_protocol(args: argparse.Namespace, ctx: dict[str, Any]) -> tuple[str, dict]:
    study = args.study_root
    protocol = _read(study / PROTOCOL, ctx)
    units, tasks, broker = (_read(study / name, ctx) for name in (UNITS, TASKS, BROKER))
    report = pilot.validate_protocol(protocol)
    problems = []
    if (
        units.get("units") != protocol["units"]
        or units.get("protocol_sha256") != report["protocol_sha256"]
    ):
        problems.append("planned units differ from the protocol")
    if pilot.canonical_json(broker) != pilot.canonical_json(pilot.BROKER):
        problems.append("broker contract differs from the frozen broker")
    rows = {row.get("task_id"): row for row in tasks.get("tasks", [])}
    for task in protocol["tasks"]:
        row = rows.get(task["task_id"], {})
        if (
            row.get("semantic_sha256") != pilot.sha256_hex(pilot.canonical_json(task["semantic"]))
            or row.get("context_hashes") != task["context_hashes"]
        ):
            problems.append(f"{task['task_id']}: task manifest does not bind this semantic mapping")
    inventory: Any = "NOT_CHECKED"
    if args.pre_inventory is not None:
        raw = _read(args.pre_inventory, ctx)
        recorded = raw.get("files", raw) if isinstance(raw, dict) else None
        if not isinstance(recorded, dict):
            raise ValueError("pre-inventory must map relative paths to sha256")
        drift = []
        for relative, digest in sorted(recorded.items()):
            path = ROOT / _safe_relative(relative)
            if not path.is_file() or pilot.sha256_hex(path.read_bytes()) != digest:
                drift.append(relative)
        if drift:
            problems.append(
                f"{len(drift)} historical file(s) differ from the pre-inventory: {drift[:5]}"
            )
        inventory = {"files_checked": len(recorded), "drift": drift}
    if problems:
        raise ValueError("; ".join(problems))
    return "PASS", {**report, "historical_inventory": inventory}


# ---------------------------------------------------------------- preflight (metadata only)
def cmd_preflight(args: argparse.Namespace, ctx: dict[str, Any]) -> tuple[str, dict]:
    if not args.metadata_only:
        raise ValueError(
            "preflight exists only as --metadata-only; no inference or probe is implemented"
        )
    protocol = _read(args.study_root / PROTOCOL, ctx)
    pilot.validate_protocol(protocol)
    observations = [
        pilot.metadata_preflight(list(argv), process_factory=subprocess.run)
        for argv in pilot.METADATA_ARGV
    ]
    raw = [{"argv": obs["argv"], **obs.pop("raw")} for obs in observations]
    retained = None
    if args.trust_root is not None:
        if not args.trust_root.is_dir():
            raise ValueError(
                "--trust-root must be an existing evaluator-only directory (mode 0700)"
            )
        name = f"metadata-raw-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{os.getpid()}.json"
        retained = {
            "path": str(args.trust_root / name),
            "sha256": _write_new(args.trust_root / name, raw, ctx, mode=0o600),
        }
    evidence: dict[str, Any] = {"metadata": pilot.summarize_metadata(observations)}
    if args.checkpoint_receipt is not None:
        receipt = _read(args.checkpoint_receipt, ctx)
        present = (
            args.git_root is not None
            and _git(
                args.git_root, "cat-file", "-e", f"{pilot.SOURCE_COMMIT}^{{commit}}"
            ).returncode
            == 0
        )
        evidence["source"] = {
            "source_commit": receipt.get("source_commit"),
            "checkpoint_status": receipt.get("status"),
            "checkpoint_receipt_sha256": ctx["inputs"][str(args.checkpoint_receipt)],
            "commit_object_present": present,
        }
    admission = pilot.evaluate_admission(protocol, evidence)
    if admission["admitted"]:
        raise RuntimeError(
            f"{admission['admitted']} unit(s) unexpectedly admitted while the live path "
            "is not implemented; escalate, do not collect"
        )
    return "BLOCKED", {
        "protocol_sha256": admission["protocol_sha256"],
        "observations": observations,
        "raw_retained": retained,
        "evidence": evidence,
        "admission": admission,
        "inferred": {"served_identity": None, "no_additional_charge": None, "isolation": None},
    }


# ---------------------------------------------------------------- collect (fail closed)
def _no_process(*_args: Any, **_kwargs: Any) -> Any:
    raise AssertionError("collect must never start a process: the live path is not implemented")


def cmd_collect(args: argparse.Namespace, ctx: dict[str, Any]) -> tuple[str, dict]:
    protocol = _read(args.study_root / PROTOCOL, ctx)
    previous = _read(args.preflight, ctx)
    result = previous.get("result") if isinstance(previous, dict) else None
    if (
        not isinstance(previous, dict)
        or previous.get("command") != "preflight"
        or not isinstance(result, dict)
        or not isinstance(result.get("evidence"), dict)
    ):
        raise ValueError("--preflight is not a preflight receipt")
    # A receipt cannot attest itself: admission is recomputed from its evidence, never trusted.
    admission = pilot.evaluate_admission(protocol, result["evidence"])
    if pilot.canonical_json(result.get("admission")) != pilot.canonical_json(admission):
        raise ValueError("the preflight receipt's admission differs from the recomputed admission")
    out = args.output_root
    if out.exists() and any(out.iterdir()):
        raise ValueError("collection output root must be fresh")
    collection = pilot.collect(protocol, admission, process_factory=_no_process)
    digest = _write_new(out / "collection-status.json", collection, ctx)
    if collection["unexpected_admissions"]:
        raise RuntimeError(
            f"{len(collection['unexpected_admissions'])} unexpected admission(s) while "
            "the live runner is not implemented; the blocked manifest was still written"
        )
    return "BLOCKED", {
        "collection_status_sha256": digest,
        "counts": collection["counts"],
        "native_process_starts": collection["native_process_starts"],
        "trust_root_read": False,
        "note": "live runtime runner and development broker loop are NOT_IMPLEMENTED",
    }


# ---------------------------------------------------------------- verify-task-oracles
def cmd_verify_task_oracles(args: argparse.Namespace, ctx: dict[str, Any]) -> tuple[str, dict]:
    if not args.trust_root.is_dir():
        raise Blocked([f"BLOCKED_TASK_FREEZE_INCOMPLETE: trust root {args.trust_root} is absent"])
    report = pilot.verify_task_oracles(
        args.study_root / "tasks", args.trust_root, corpus_roots=tuple(args.corpus_root)
    )
    return {"PASS": "PASS", "FAIL": "FAIL"}.get(report["status"], "BLOCKED"), report


# ---------------------------------------------------------------- replay
def cmd_replay(args: argparse.Namespace, ctx: dict[str, Any]) -> tuple[str, dict]:
    protocol = _read(args.study_root / PROTOCOL, ctx)
    collection = _read(args.collection_root / "collection-status.json", ctx)
    pilot.reconcile_results(protocol, collection["rows"])
    admitted = [row["unit_id"] for row in collection["rows"] if row["admitted"]]
    reason = (
        "no admitted artifacts exist to replay"
        if not admitted
        else "independent artifact replay is not implemented; admitted units stay unreplayed"
    )
    return "UNRESOLVED", {
        "admitted_artifacts": len(admitted),
        "replayed": 0,
        "added_model_calls": 0,
        "reason": reason,
        "trust_root_read": False,
    }


# ---------------------------------------------------------------- verify-analysis
def _recount(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Independent of the library's reconciliation: plain loops over the retained raw rows."""
    total = dict.fromkeys(
        (
            "planned",
            "blocked",
            "assigned",
            "attempted",
            "executed",
            "failed",
            "missing",
            "successful",
            "identity_qualified",
            "replayed",
        ),
        0,
    )
    tracks = {"runtime": 0, "development": 0}
    costs: list[Any] = []
    starts, reasons = 0, {}
    for row in rows:
        total["planned"] += 1
        tracks[row["track"]] += 1
        starts += row["native_process_starts"]
        for reason in row["blocked_reasons"]:
            reasons[reason] = reasons.get(reason, 0) + 1
        total["attempted"] += 1 if row["dispatch_attempts"] > 0 else 0
        total["executed"] += 1 if row["executed"] is True else 0
        total["successful"] += 1 if row["successful"] is True else 0
        total["identity_qualified"] += 1 if row["identity_qualified"] is True else 0
        total["replayed"] += 1 if row["replayed"] is True else 0
        if row["admitted"] is True:
            total["assigned"] += 1
            costs.append(row["cost"])
            if row["terminal_outcome"] is None:
                total["missing"] += 1
            elif row["successful"] is not True:
                total["failed"] += 1
        else:
            total["blocked"] += 1
    known = [cost for cost in costs if cost is not None]
    unknown = len(costs) - len(known)
    status = (
        "NOT_RUN/BLOCKED"
        if not total["assigned"]
        else "PARTIAL"
        if total["assigned"] < total["planned"] or total["missing"]
        else "COMPLETE_ANALYSIS_NOT_IMPLEMENTED"
    )
    claims = {
        key: total[key] for key in ("planned", "blocked", "assigned", "attempted", "executed")
    }
    claims.update(
        runtime=tracks["runtime"],
        development=tracks["development"],
        native_starts=starts,
        study=pilot.STUDY_ID,
        status=status,
        conclusion="NOT_MET",
        rate=total["successful"] / total["assigned"] if total["assigned"] else None,
        cost=math.fsum(known) if costs and not unknown else None,
        subtotal=math.fsum(known) if known else None,
        unknown=unknown,
        effect=None,
    )
    return {
        "counts": total,
        "tracks": tracks,
        "costs": costs,
        "claims": claims,
        "blocker_counts": reasons,
    }


def _publication_text(path: Path, ctx: dict[str, Any]) -> str:
    data = path.read_bytes()
    ctx["inputs"][str(path)] = pilot.sha256_hex(data)
    return data.decode("utf-8")


def _check_tex(directory: Path, recount: dict[str, Any], ctx: dict[str, Any]) -> list[str]:
    """Parse the deliberately narrow visible publication grammar, not the producer's output."""
    identifiers = r"[A-Za-z0-9_/-]+"
    number = r"(?:null|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)"
    grammars = {
        "en": (
            r"Prospective pilot status: not a model comparison\. The frozen study "
            rf"(?P<study>{identifiers}) plans (?P<planned>\d+) units "
            r"\((?P<runtime>\d+) runtime and (?P<development>\d+) development\) "
            r"over three requested targets\. (?P<blocked>\d+) are blocked, "
            r"(?P<assigned>\d+) assigned, (?P<attempted>\d+) attempted and "
            r"(?P<executed>\d+) executed, with (?P<native_starts>\d+) native process starts\. "
            rf"Status (?P<status>{identifiers}); scientific conclusion (?P<conclusion>{identifiers})\. "
            rf"Success rate: (?P<rate>{number})\. Observed cost: (?P<cost>{number}) "
            rf"\(known subtotal (?P<subtotal>{number}); (?P<unknown>\d+) admitted units "
            rf"with unknown cost\)\. Effect estimate: (?P<effect>{number})\. "
            r"A null is an absent measurement, never zero\. "
            r"Blocked prerequisites, counted per unit: (?P<blockers>.*?)\. "
            r"The earlier eight-row 5/8 pilot, the stopped identity extension, the Ollama lane, "
            r"the deterministic fixtures and the n=1 results are separate lanes\. "
            r"They are neither pooled nor re-reported here\."
        ),
        "ko": (
            r"전향 파일럿 상태: 모델 비교가 아님\. 고정된 연구 "
            rf"(?P<study>{identifiers})는 요청된 세 target에 걸쳐 (?P<planned>\d+)개 단위"
            r"\(런타임 (?P<runtime>\d+)개, 개발 (?P<development>\d+)개\)를 계획한다\. "
            r"(?P<blocked>\d+)개 차단, (?P<assigned>\d+)개 배정, (?P<attempted>\d+)개 시도, "
            r"(?P<executed>\d+)개 실행이며 native 프로세스 시작은 (?P<native_starts>\d+)회이다\. "
            rf"상태 (?P<status>{identifiers}); 과학적 결론 (?P<conclusion>{identifiers})\. "
            rf"성공률: (?P<rate>{number})\. 관측 비용: (?P<cost>{number}) "
            rf"\(알려진 부분합 (?P<subtotal>{number}); 비용을 알 수 없는 배정 단위 (?P<unknown>\d+)개\)\. "
            rf"효과 추정: (?P<effect>{number})\. null은 측정이 없다는 뜻이며 0이 아니다\. "
            r"차단된 선결 조건\(단위별 집계\): (?P<blockers>.*?)\. "
            r"이전 8행 5/8 파일럿, 중단된 신원 확장, Ollama 레인, 결정적 fixture, n=1 결과는 "
            r"별도 레인이다\. 여기서 합산하거나 다시 보고하지 않는다\."
        ),
    }
    expected = {
        key: (
            "null"
            if value is None
            else format(value, ".4g")
            if isinstance(value, float)
            else str(value)
        )
        for key, value in recount["claims"].items()
    }
    problems = []
    for language in ("en", "ko"):
        path = directory / f"status_{language}.tex"
        text = re.sub(r"(?<!\\)%[^\n]*", "", _publication_text(path, ctx))
        # Only these two non-hiding wrappers are supported. Any other TeX command,
        # grouping, math, or condition is rejected rather than guessed to be visible.
        text = re.sub(r"\\texttt\{\\detokenize\{(" + identifiers + r")\}\}", r"\1", text)
        text = re.sub(r"\A\\textbf\{([^{}\\]*)\}", r"\1", text)
        if any(char in text for char in "\\{}$%"):
            problems.append(f"{path.name}: unsupported or hidden TeX publication surface")
            continue
        match = re.fullmatch(grammars[language], " ".join(text.split()))
        if match is None:
            problems.append(f"{path.name}: missing, duplicate or invalid visible labeled claims")
            continue
        claims = match.groupdict()
        blockers = claims.pop("blockers")
        items = blockers.split(", ") if blockers else []
        parsed = [re.fullmatch(r"(" + identifiers + r") \((\d+)\)", item) for item in items]
        if (
            any(item is None for item in parsed)
            or len({item[1] for item in parsed if item is not None}) != len(items)
            or {item[1]: int(item[2]) for item in parsed if item is not None}
            != recount["blocker_counts"]
        ):
            problems.append(
                f"{path.name}: visible blocker counts differ from the retained-row recount"
            )
        for key, value in expected.items():
            if claims[key] != value:
                problems.append(
                    f"{path.name}: visible {key} claim differs from the retained-row recount"
                )
    return problems


def _check_manuscripts(ctx: dict[str, Any]) -> list[str]:
    problems = []
    for language in ("en", "ko"):
        path = ROOT / "paper/latex" / language / "main.tex"
        text = re.sub(r"(?<!\\)%[^\n]*", "", _publication_text(path, ctx))
        inputs = re.findall(r"\\input\{([^{}]+)\}", text)
        own = f"../generated/prospective-pilot/status_{language}.tex"
        other = f"../generated/prospective-pilot/status_{'ko' if language == 'en' else 'en'}.tex"
        if inputs.count(own) != 1 or other in inputs:
            problems.append(
                f"{language}: expected exactly one active own-language prospective input"
            )
    return problems


def _check_readmes(summary: dict[str, Any], ctx: dict[str, Any]) -> list[str]:
    problems = []
    start, end = "<!-- prospective-pilot:start -->", "<!-- prospective-pilot:end -->"
    header = ["Track", "Planned", "Blocked", "Assigned", "Attempted", "Executed"]
    for name in ("README.md", "README.ko.md"):
        text = _publication_text(ROOT.parent / name, ctx)
        if text.count(start) != 1 or text.count(end) != 1 or text.index(start) >= text.index(end):
            problems.append(f"{name}: expected one ordered prospective section marker pair")
            continue
        visible = re.sub(
            r"<!--.*?-->", "", text.split(start, 1)[1].split(end, 1)[0], flags=re.DOTALL
        )
        if not all(
            value in visible
            for value in (summary["study_id"], summary["status"], summary["conclusion"])
        ):
            problems.append(
                f"{name}: visible study identity, blocked status or unmet conclusion absent"
            )
        if re.search(r"\b(?:PASS|MET|COMPLETE|COMPLETED)\b", visible):
            problems.append(f"{name}: contradictory prospective publication status")
        table = []
        for line in visible.splitlines():
            if line.strip().startswith("|"):
                cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                    table.append(cells)
        expected = [header]
        for label, track in (("Runtime", "runtime"), ("Development", "development")):
            expected.append(
                [label, *(str(summary["tracks"][track][key.lower()]) for key in header[1:])]
            )
        if table != expected:
            problems.append(f"{name}: visible track table differs from retained-unit counts")
    return problems


def cmd_verify_analysis(args: argparse.Namespace, ctx: dict[str, Any]) -> tuple[str, dict]:
    study = args.study_root
    protocol = _read(study / PROTOCOL, ctx)
    collection = _read(args.collection or study / "results-v1/collection-status.json", ctx)
    summary = _read(args.summary or study / "results-v1/summary.json", ctx)
    pilot.validate_analysis(protocol, collection["rows"], summary)
    recount, problems = _recount(collection["rows"]), []
    counts = recount["counts"]
    if {key: summary["counts"][key] for key in counts} != counts:
        problems.append("summary counts differ from the independent recount")
    if {name: summary["tracks"][name]["planned"] for name in recount["tracks"]} != recount[
        "tracks"
    ]:
        problems.append("per-track planned counts differ from the independent recount")
    if {key: collection["counts"][key] for key in collection["counts"]} != {
        key: counts[key] for key in ("planned", "blocked", "assigned", "attempted", "executed")
    }:
        problems.append("collection counts differ from the independent recount")
    if collection["native_process_starts"] != sum(
        row["native_process_starts"] for row in collection["rows"]
    ):
        problems.append("native_process_starts differs from the raw rows")
    admitted_costs = recount["costs"]
    expected_rate = counts["successful"] / counts["assigned"] if counts["assigned"] else None
    expected_cost = (
        math.fsum(admitted_costs) if counts["assigned"] and None not in admitted_costs else None
    )
    if summary["success_rate"] != expected_rate or (summary["success_rate"] is None) != (
        expected_rate is None
    ):
        problems.append(
            "success_rate is not the admitted-denominator rate (null when nothing admitted)"
        )
    if summary["observed_cost"] != expected_cost or (summary["observed_cost"] is None) != (
        expected_cost is None
    ):
        problems.append("observed_cost invents or drops a measurement")
    if summary["effect_estimate"] is not None or summary["conclusion"] != "NOT_MET":
        problems.append(
            "an effect estimate or a non-NOT_MET conclusion has no implemented analysis"
        )
    tex_dir = args.tex_dir
    if tex_dir is None and args.scope != "results":
        tex_dir = ROOT / "paper/latex/generated/prospective-pilot"
    if tex_dir is not None:
        problems += _check_tex(tex_dir, recount, ctx)
    if args.scope == "manuscript":
        problems += _check_manuscripts(ctx)
    elif args.scope == "readme":
        problems += _check_readmes(summary, ctx)
    if problems:
        raise ValueError("; ".join(problems))
    return "PASS", {
        "scope": args.scope,
        "rows": len(collection["rows"]),
        "counts": counts,
        "tex_checked": tex_dir is not None,
    }


# ---------------------------------------------------------------- receipt and entry point
COMMANDS = {
    "prepare": cmd_prepare,
    "validate-protocol": cmd_validate_protocol,
    "preflight": cmd_preflight,
    "collect": cmd_collect,
    "verify-task-oracles": cmd_verify_task_oracles,
    "replay": cmd_replay,
    "verify-analysis": cmd_verify_analysis,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str) -> argparse.ArgumentParser:
        child = sub.add_parser(name)
        child.add_argument(
            "--receipt", type=Path, help="new receipt file; an existing one is refused"
        )
        child.add_argument("--study-root", type=Path, default=DEFAULT_STUDY)
        return child

    prepare = add("prepare")
    prepare.add_argument("--task-root", type=Path, help="external pre-prepared public task bundle")
    prepare.add_argument("--source-root", type=Path, help="tree extracted from the pinned commit")
    prepare.add_argument(
        "--git-root", type=Path, help="repository holding the pinned commit object"
    )
    prepare.add_argument("--tree-prefix", default=DEFAULT_PREFIX)
    add("validate-protocol").add_argument("--pre-inventory", type=Path)
    pre = add("preflight")
    pre.add_argument("--metadata-only", action="store_true")
    pre.add_argument("--trust-root", type=Path)
    pre.add_argument("--checkpoint-receipt", type=Path)
    pre.add_argument("--git-root", type=Path)
    col = add("collect")
    col.add_argument("--preflight", type=Path, required=True)
    col.add_argument("--trust-root", type=Path)
    col.add_argument("--output-root", type=Path, required=True)
    ver = add("verify-task-oracles")
    ver.add_argument("--trust-root", type=Path, required=True)
    ver.add_argument("--corpus-root", type=Path, action="append", default=[])
    rep = add("replay")
    rep.add_argument("--collection-root", type=Path, required=True)
    rep.add_argument("--trust-root", type=Path)
    ana = add("verify-analysis")
    ana.add_argument("--scope", choices=("results", "manuscript", "readme"), default="results")
    ana.add_argument("--collection", type=Path)
    ana.add_argument("--summary", type=Path)
    ana.add_argument("--tex-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.receipt is not None and args.receipt.exists():
        print(f"refusing to overwrite existing receipt {args.receipt}", file=sys.stderr)
        return 1
    ctx: dict[str, Any] = {"inputs": {}, "outputs": {}}
    started = time.time()
    status, result, errors = "FAIL", None, []
    try:
        status, result = COMMANDS[args.command](args, ctx)
    except Blocked as blocked:
        status, errors = "BLOCKED", blocked.reasons
    except Exception as error:  # noqa: BLE001 - every failure must become an exact receipt
        status, errors = "FAIL", [f"{type(error).__name__}: {error}"]
    receipt = {
        "schema": "prospective-pilot-receipt/v1",
        "study_id": pilot.STUDY_ID,
        "command": args.command,
        "status": status,
        "argv": sys.argv if argv is None else ["run_prospective_pilot.py", *argv],
        "cwd": os.getcwd(),
        "started_utc": pilot._utc(started),
        "ended_utc": pilot._utc(),
        "inputs": ctx["inputs"],
        "outputs": ctx["outputs"],
        "errors": errors,
        "result": result,
    }
    if args.receipt is not None:
        try:
            _write_new(args.receipt, receipt, {"outputs": {}})
        except OSError as error:
            receipt.update(status="FAIL", errors=[*errors, f"receipt not written: {error}"])
            status = "FAIL"
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return EXIT[status]


if __name__ == "__main__":
    raise SystemExit(main())
