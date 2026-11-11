#!/usr/bin/env python3
"""Run an isolated, paired synthetic feedback pilot using the Codex subscription.

First prepare and review every request byte locally with prepare. Only then use
run. This is a development pilot, not a held-out or human-adjudicated study.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import codex_feedback_live_adapter
from run_local_signal_comparison import fixtures

from nesy_game.contracts import CandidateParseError, parse_candidate_mapping
from nesy_game.runtime import execute_with_repair, to_jsonable
from nesy_game.validator import validate_candidate

RUN_ROOT = ROOT / "research/codex_feedback_pilot"
LEGACY_RUN = RUN_ROOT / "codex-feedback-pilot-20261110"
MODELS = ("gpt-5.6-luna", "gpt-5.6-terra")
RUN = RUN_ROOT / "unselected"
MODEL = None
CODEX_BIN = None
AUTH_FILE = None
APPROVAL_SHA256 = None
TIMEOUT = 120
CONDITIONS = ("detailed", "generic")


def now():
    return datetime.now(UTC).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def codex_identity():
    if CODEX_BIN is None:
        raise RuntimeError("an explicit native Codex binary is required")
    executable = Path(CODEX_BIN).resolve(strict=True)
    binary = executable.read_bytes()
    if binary[:4] not in (
        b"\xcf\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xce",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
        b"\xca\xfe\xba\xbf",
        b"\xbf\xba\xfe\xca",
    ):
        raise RuntimeError("Codex executable must be a native Mach-O binary, not a launcher")
    digest = sha(binary)
    if digest != codex_feedback_live_adapter.isolation.EXPECTED_SHA256:
        raise RuntimeError("Codex executable differs from the audited native build")
    with tempfile.TemporaryDirectory(prefix="codex-version-") as directory:
        snapshot = codex_feedback_live_adapter.snapshot_executable(binary, Path(directory))
        profile = codex_feedback_live_adapter.isolation.sandbox_profile(
            Path(directory), snapshot, 1
        )
        profile += "(deny network-outbound)(deny file-write*)"
        version = subprocess.run(
            ["/usr/bin/sandbox-exec", "-p", profile, str(snapshot), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
            env={"PATH": "/usr/bin:/bin"},
            stdin=subprocess.DEVNULL,
        ).stdout.strip()
    if not version:
        raise RuntimeError("Codex native version unavailable")
    if sha(executable.read_bytes()) != digest:
        raise RuntimeError("Codex executable changed during identity check")
    return {
        "codex_executable": str(executable),
        "codex_executable_sha256": digest,
        "codex_version": version,
    }


def atomic_json(path, value):
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temp.replace(path)


def build_prompt(case_id, proposal, signal, state=None):
    payload = {
        "state": to_jsonable(state) if state is not None else None,
        "candidate": proposal,
        "validator_feedback": signal,
        "objective": "commit with signal_restored in final facts",
    }
    return (
        "Repair this fictional game action. Return only one JSON object with exactly the same candidate fields, no markdown. "
        "Keep action_id, actor_id and action_type unchanged. Do not use tools or network.\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    )


def pilot_cases():
    # Original descriptive fixture identifiers reveal error classes even in the generic arm.
    return [
        (state.state_id, replace(state, state_id="scene"), replace(action, action_id="event"))
        for state, action in fixtures()
    ]


def evaluate_response(state, original, response_text):
    parsed = json.loads(response_text)
    candidate = parse_candidate_mapping(parsed, allow_defaults=False)
    identity_preserved = all(
        getattr(candidate, key) == getattr(original, key)
        for key in ("action_id", "actor_id", "action_type")
    )
    if not identity_preserved:
        return {
            "identity_preserved": False,
            "outcome": "identity_rejected",
            "final_gate_accepted": False,
            "objective_reached": False,
            "final_state": to_jsonable(state),
            "final_candidate": to_jsonable(candidate),
        }
    outcome = execute_with_repair(state, candidate, repair_budget=0)
    validation = validate_candidate(state, candidate)
    return {
        "identity_preserved": True,
        "outcome": outcome.status,
        "final_gate_accepted": validation.valid,
        "objective_reached": outcome.status == "commit"
        and "signal_restored" in outcome.state.facts,
        "initial_state_unchanged": to_jsonable(state) == to_jsonable(outcome.prior_state),
        "fallback_state_unchanged": to_jsonable(outcome.state) == to_jsonable(state)
        if outcome.status == "fallback"
        else None,
        "final_state": to_jsonable(outcome.state),
        "final_candidate": to_jsonable(candidate),
        "validation": to_jsonable(validation),
        "trace": to_jsonable(outcome.trace),
        "trace_hash": outcome.trace_hash,
    }


def summarize(rows):
    out = {}
    for condition in CONDITIONS:
        subset = [r for r in rows if r["condition"] == condition]
        out[condition] = {
            "assigned": len(subset),
            "completed": sum(r["status"] == "COMPLETED" for r in subset),
            "failed": sum(r["status"] == "FAILED" for r in subset),
            "pending": sum(r["status"] in ("PENDING", "IN_PROGRESS") for r in subset),
            "gate_accepted": sum(
                (r.get("evaluation") or {}).get("final_gate_accepted") is True for r in subset
            ),
            "objective_reached": sum(
                (r.get("evaluation") or {}).get("objective_reached") is True for r in subset
            ),
        }
    return out


def status(rows, phase, current=None):
    done = sum(r["status"] == "COMPLETED" for r in rows)
    failed = sum(r["status"] == "FAILED" for r in rows)
    atomic_json(
        RUN / "status.json",
        {
            "scope": "synthetic development pilot, not held-out or human evaluated",
            "status": phase,
            "planned": len(rows),
            "completed": done,
            "failed": failed,
            "pending": len(rows) - done - failed,
            "current_case": current[0] if current else None,
            "current_condition": current[1] if current else None,
            "updated_at": now(),
            "result_file": "results.json",
            "model_selector": MODEL,
            "actual_model_identity": None,
            "cost_usd": None,
        },
    )


def write_results(rows, metadata):
    atomic_json(
        RUN / "results.json",
        {
            "scope": "synthetic development pilot; not a new holdout or population evidence",
            "human_evaluation": "NOT_RUN",
            "generic_rules_baseline": "NOT_IMPLEMENTED",
            "metadata": metadata,
            "cases": rows,
            "summary": summarize(rows),
        },
    )


def prepare():
    if RUN.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {RUN}")
    rows, prompts = [], []
    for case_id, state, action in pilot_cases():
        proposal = to_jsonable(action)
        detailed = to_jsonable(validate_candidate(state, action))
        if detailed["valid"]:
            raise ValueError("all pilot starting actions must be rejected")
        for condition in CONDITIONS:
            signal = (
                detailed
                if condition == "detailed"
                else {"valid": False, "message": "Action rejected."}
            )
            prompt = build_prompt(case_id, proposal, signal, state)
            name = f"{case_id}-{condition}.prompt.txt"
            prompts.append((name, prompt.encode("utf-8")))
            rows.append(
                {
                    "case_id": case_id,
                    "condition": condition,
                    "status": "PENDING",
                    "initial_state": to_jsonable(state),
                    "shared_proposal": proposal,
                    "input_signal": signal,
                    "prompt_file": name,
                    "prompt_sha256": sha(prompt.encode("utf-8")),
                    "seed": None,
                    "actual_model_identity": None,
                    "tokens": None,
                    "cost_usd": None,
                    "failure": None,
                    "evaluation": None,
                }
            )
    paths = [
        Path(__file__),
        ROOT / "scripts/run_local_signal_comparison.py",
        ROOT / "scripts/codex_feedback_live_adapter.py",
        ROOT / "scripts/codex_isolation_wrapper.py",
        ROOT / "src/nesy_game/contracts.py",
        ROOT / "src/nesy_game/runtime.py",
        ROOT / "src/nesy_game/validator.py",
    ]
    identity = codex_identity()
    metadata = {
        "created_at": now(),
        "python_version": platform.python_version(),
        **identity,
        "pilot_protocol": "model-separated-v2",
        "collector_protocol_amendment": {
            "id": "parse-failures-continue-v1",
            "expected_output_errors": ["JSONDecodeError", "CandidateParseError"],
            "continuation": "only after successful adapter receipt; FAILED/evaluation_error; no retry",
            "other_errors": "hard stop; remaining assignments stay pending",
            "denominator": "all assigned rows; failed outputs count as zero gate/objective successes",
            "completion": "COMPLETED_WITH_FAILURES means collection finished, not all tasks passed",
            "prompt_and_evaluator": "unchanged",
        },
        "model_selector": MODEL,
        "actual_model_identity": None,
        "cost_usd": None,
        "seed": None,
        "seed_note": "Codex CLI exposes no seed option",
        "timeout_seconds": TIMEOUT,
        "execution_order": "fixture order, detailed then generic; sequential; one fresh ephemeral session per request",
        "prompt_scope": "fictional synthetic state, candidate, goal and validator feedback; no private project context",
        "source_sha256": {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths},
        "fixture_sha256": sha(
            json.dumps(
                [
                    {"state": to_jsonable(s), "proposal": to_jsonable(a)}
                    for _, s, a in pilot_cases()
                ],
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ),
        "objective": "gate commits and final facts contain signal_restored",
        "usage_note": "only CLI-reported values, if present; actual model identity and cost unverified",
    }
    RUN.mkdir(parents=True, exist_ok=False)
    lock_fd = os.open(RUN / ".run.lock", os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(lock_fd)
    for name, prompt_bytes in prompts:
        (RUN / name).write_bytes(prompt_bytes)
    write_results(rows, metadata)
    (RUN / "approved_results.json").write_bytes((RUN / "results.json").read_bytes())
    status(rows, "AWAITING_REVIEW")


def run(max_attempts=None):
    if AUTH_FILE is None or APPROVAL_SHA256 is None:
        raise RuntimeError("authentication file and reviewed results SHA-256 are required")
    data = json.loads((RUN / "results.json").read_bytes())
    if data.get("metadata", {}).get("pilot_protocol") != "model-separated-v2":
        raise RuntimeError("prepared cohort protocol is not eligible for dispatch")
    fd = os.open(RUN / ".run.lock", os.O_RDWR | os.O_NOFOLLOW)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("cohort is already running") from exc
        return _run_locked(max_attempts=max_attempts)
    finally:
        os.close(fd)


def _run_locked(max_attempts=None):
    if max_attempts is not None and (type(max_attempts) is not int or max_attempts != 1):
        raise ValueError("max_attempts must be 1 or None")
    if AUTH_FILE is None or APPROVAL_SHA256 is None:
        raise RuntimeError("authentication file and reviewed results SHA-256 are required")
    reviewed = (RUN / "results.json").read_bytes()
    if sha(reviewed) != APPROVAL_SHA256 or (RUN / "approved_results.json").read_bytes() != reviewed:
        raise RuntimeError("reviewed results SHA-256 does not match")
    data = json.loads(reviewed)
    rows, metadata = data["cases"], data["metadata"]
    if (
        metadata.get("pilot_protocol") != "model-separated-v2"
        or metadata.get("model_selector") != MODEL
    ):
        raise RuntimeError("prepared cohort or model selector does not match this run")
    if any(r["status"] != "PENDING" for r in rows):
        raise RuntimeError("refusing to overwrite or resume an existing run")
    identity = codex_identity()
    if any(metadata.get(key) != value for key, value in identity.items()):
        raise RuntimeError("Codex executable identity changed after preparation")
    for path, expected in metadata["source_sha256"].items():
        if sha((ROOT / path).read_bytes()) != expected:
            raise RuntimeError(f"source changed after review: {path}")
    cases = {name: (s, a) for name, s, a in pilot_cases()}
    expected_pairs = {(name, condition) for name in cases for condition in CONDITIONS}
    if (
        len(rows) != len(expected_pairs)
        or {(r["case_id"], r["condition"]) for r in rows} != expected_pairs
    ):
        raise RuntimeError("case and condition assignment changed after preparation")
    reviewed_prompts = {}
    for row in rows:
        state, action = cases[row["case_id"]]
        proposal = to_jsonable(action)
        signal = (
            to_jsonable(validate_candidate(state, action))
            if row["condition"] == "detailed"
            else {"valid": False, "message": "Action rejected."}
        )
        if (
            row["initial_state"] != to_jsonable(state)
            or row["shared_proposal"] != proposal
            or row["input_signal"] != signal
        ):
            raise RuntimeError("case data changed after preparation")
        expected_prompt = build_prompt(row["case_id"], proposal, signal, state).encode("utf-8")
        if row["prompt_file"] != f"{row['case_id']}-{row['condition']}.prompt.txt":
            raise RuntimeError("prompt filename does not match assignment")
        prompt_bytes = (RUN / row["prompt_file"]).read_bytes()
        if prompt_bytes != expected_prompt:
            raise RuntimeError("prompt does not match assigned case and condition")
        if sha(prompt_bytes) != row["prompt_sha256"]:
            raise RuntimeError("prompt changed after review")
        reviewed_prompts[row["prompt_file"]] = prompt_bytes
    status(rows, "RUNNING")
    attempts = 0
    for row in rows:
        case, condition = row["case_id"], row["condition"]
        state, original = cases[case]
        status(rows, "RUNNING", (case, condition))
        row["started_at"] = now()
        row["attempt"] = 1
        row["timeout_seconds"] = TIMEOUT
        row["status"] = "IN_PROGRESS"
        write_results(rows, metadata)
        evaluating = False
        expected_output_error = False
        try:
            approval = {
                "model": metadata["model_selector"],
                "case_id": case,
                "condition": condition,
                "prompt_sha256": row["prompt_sha256"],
                "identity": identity,
                "results_sha256": APPROVAL_SHA256,
                "results_path": RUN / "approved_results.json",
            }
            attempts += 1
            result = codex_feedback_live_adapter.dispatch(
                prompt=reviewed_prompts[row["prompt_file"]],
                prompt_sha256=row["prompt_sha256"],
                model=MODEL,
                identity=identity,
                auth_file=AUTH_FILE,
                case_id=case,
                condition=condition,
                timeout=TIMEOUT,
                approval=approval,
            )
            row["response_text"] = result["response_text"]
            row["tokens"] = result["tokens"]
            row["tls_payload_observed"] = result["tls_payload_observed"]
            row["evidence"] = result["evidence"]
            evaluating = True
            row["evaluation"] = evaluate_response(state, original, row["response_text"])
            row["status"] = "COMPLETED"
        # Persist every failed attempt; unexpected faults still stop collection below.
        except Exception as exc:  # noqa: BLE001
            expected_output_error = evaluating and isinstance(
                exc, (json.JSONDecodeError, CandidateParseError)
            )
            row["status"] = "FAILED"
            row["failure"] = {
                "type": type(exc).__name__,
                "code": (
                    exc.code
                    if isinstance(exc, codex_feedback_live_adapter.DispatchError)
                    else "evaluation_error"
                    if evaluating
                    else "unclassified"
                ),
                "transmission": "unknown",
            }
            if "response_text" in row:
                response_text = row.pop("response_text")
                try:
                    response_bytes = response_text.encode("utf-8")
                except (AttributeError, UnicodeEncodeError):
                    row["response_sha256"] = None
                    row["response_bytes"] = None
                else:
                    row["response_sha256"] = sha(response_bytes)
                    row["response_bytes"] = len(response_bytes)
            if isinstance(exc, codex_feedback_live_adapter.DispatchError):
                row["evidence"] = exc.evidence
        row["finished_at"] = now()
        write_results(rows, metadata)
        if row["status"] == "FAILED" and not expected_output_error:
            metadata["stop_reason"] = "Attempt failed; remaining pairs were not attempted."
            write_results(rows, metadata)
            status(rows, "STOPPED")
            return False
        if (
            max_attempts is not None
            and attempts >= max_attempts
            and any(r["status"] == "PENDING" for r in rows)
        ):
            metadata["stop_reason"] = (
                "Dispatcher attempt limit reached; remaining pairs were not attempted."
            )
            write_results(rows, metadata)
            status(rows, "STOPPED")
            return True
        status(rows, "RUNNING")
    status(
        rows,
        "COMPLETED_WITH_FAILURES" if any(r["status"] == "FAILED" for r in rows) else "COMPLETED",
    )
    return True


def main():
    global RUN, MODEL, CODEX_BIN, AUTH_FILE, APPROVAL_SHA256
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--model", required=True, choices=MODELS)
    parser.add_argument("--codex-bin", required=True, type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--auth-file", type=Path)
    parser.add_argument("--approval-sha256")
    parser.add_argument(
        "--max-attempts", type=int, choices=(1,), help="limit this process to one dispatcher entry"
    )
    args = parser.parse_args()
    MODEL = args.model
    CODEX_BIN = args.codex_bin
    AUTH_FILE = args.auth_file
    APPROVAL_SHA256 = args.approval_sha256
    if args.mode == "run" and (AUTH_FILE is None or APPROVAL_SHA256 is None):
        parser.error("run requires --auth-file and --approval-sha256 of reviewed results.json")
    run_root = RUN_ROOT.resolve()
    RUN = (args.run_dir if args.run_dir is not None else run_root / MODEL).resolve()
    if RUN == run_root or run_root not in RUN.parents:
        parser.error("--run-dir must be a new child of research/codex_feedback_pilot")
    legacy_run = LEGACY_RUN.resolve()
    if RUN == legacy_run or legacy_run in RUN.parents:
        parser.error("--run-dir must not use the legacy cohort")
    if args.mode == "prepare":
        prepare()
    elif not run(max_attempts=args.max_attempts):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
