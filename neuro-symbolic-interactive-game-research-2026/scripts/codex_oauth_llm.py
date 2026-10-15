#!/usr/bin/env python3
"""Use the authenticated Codex CLI as a local, soft-proposal-only LLM companion.

Authentication and credential storage remain wholly owned by the official Codex
CLI.  This wrapper never opens, copies, or logs credential files or tokens.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_SCHEMA = PROJECT_ROOT / "game-track" / "schemas" / "codex-oauth-soft-proposal.schema.json"
CODEX = "codex"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
PROPOSAL_KEYS = {
    "schema_version",
    "request_id",
    "status",
    "claim_boundary",
    "authorization_effect",
    "canonical_state_mutated",
    "hard_validation_required",
    "response",
    "assumptions",
    "uncertainties",
}
SMOKE_PROMPT = (
    "Reply briefly in Korean and English that this is a non-authoritative soft "
    "proposal and cannot authorize a game action."
)

Runner = Callable[..., subprocess.CompletedProcess[str]]

MAX_SUBPROCESS_OUTPUT = 64 * 1024
MAX_FINAL_MESSAGE_BYTES = 64 * 1024
TOOL_POLICY_FEATURES = (
    "shell_tool",
    "shell_snapshot",
    "unified_exec",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "computer_use",
    "apps",
    "enable_mcp_apps",
    "mcp_2026_07_28",
    "tool_call_mcp_elicitation",
    "tool_suggest",
    "skill_search",
    "skill_mcp_dependency_install",
    "image_generation",
    "view_image",
    "in_app_browser",
    "code_mode_host",
)


def _output_within_limit(completed: subprocess.CompletedProcess[str]) -> bool:
    return all(
        len(text or "") <= MAX_SUBPROCESS_OUTPUT for text in (completed.stdout, completed.stderr)
    )


def _tool_policy_flags(runner: Runner | None) -> list[str] | None:
    """Return explicit feature disables, or None when this CLI cannot enforce them."""
    if runner is not None:
        return []
    executable = _codex_executable(None)
    try:
        help_result = subprocess.run(
            [executable, "exec", "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        feature_result = subprocess.run(
            [executable, "features", "list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return None
    if help_result.returncode != 0 or feature_result.returncode != 0:
        return None
    if "--disable <FEATURE>" not in f"{help_result.stdout or ''}\n{help_result.stderr or ''}":
        return None
    if not _output_within_limit(help_result) or not _output_within_limit(feature_result):
        return None
    advertised = {
        line.split()[0] for line in (feature_result.stdout or "").splitlines() if line.split()
    }
    if any(feature not in advertised for feature in TOOL_POLICY_FEATURES):
        return None
    flags: list[str] = []
    for feature in TOOL_POLICY_FEATURES:
        flags.extend(("--disable", feature))
    return flags


def resolve_codex_cli() -> str:
    """Prefer the first PATH entry whose installed Codex launcher is runnable."""

    candidates = [
        str(path)
        for path in sorted(
            (Path.home() / ".nvm" / "versions" / "node").glob("*/bin/codex"),
            reverse=True,
        )
        if path.exists()
    ]
    resolved = shutil.which(CODEX)
    if resolved:
        candidates.append(resolved)
    candidates.extend(
        str(path)
        for path in (
            Path.home() / ".nvm" / "current" / "bin" / CODEX,
            Path.home() / ".local" / "bin" / CODEX,
        )
        if path.exists()
    )
    return next(iter(dict.fromkeys(candidates)), CODEX)


def _codex_executable(runner: Runner | None) -> str:
    return CODEX if runner is not None else resolve_codex_cli()


def _run(runner: Runner | None) -> Runner:
    return subprocess.run if runner is None else runner


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _status_payload(
    *,
    available: bool,
    authenticated: bool,
    auth_method: str,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "command": "codex login status",
        "codex_cli_available": available,
        "authenticated": authenticated,
        "auth_method": auth_method,
        "oauth_prompt_ready": authenticated and auth_method == "chatgpt_oauth",
        "secrets_included": False,
    }


def query_auth_status(*, runner: Runner | None = None) -> dict[str, Any]:
    """Return a minimal status projection without forwarding CLI output."""

    try:
        completed = _run(runner)(
            [_codex_executable(runner), "login", "status"],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except FileNotFoundError:
        return _status_payload(
            available=False,
            authenticated=False,
            auth_method="unavailable",
        )
    except (OSError, subprocess.TimeoutExpired):
        return _status_payload(
            available=True,
            authenticated=False,
            auth_method="indeterminate",
        )

    if completed.returncode != 0:
        return _status_payload(
            available=True,
            authenticated=False,
            auth_method="none",
        )

    if not _output_within_limit(completed):
        return _status_payload(
            available=True,
            authenticated=False,
            auth_method="indeterminate",
        )
    status_text = f"{completed.stdout or ''}\n{completed.stderr or ''}".casefold()
    if "chatgpt" in status_text:
        auth_method = "chatgpt_oauth"
    elif "api key" in status_text or "api_key" in status_text:
        auth_method = "api_key"
    elif "access token" in status_text or "access_token" in status_text:
        auth_method = "access_token"
    else:
        auth_method = "unknown"
    return _status_payload(
        available=True,
        authenticated=True,
        auth_method=auth_method,
    )


def run_device_login(*, runner: Runner | None = None) -> int:
    """Delegate the official device-code flow with inherited terminal streams."""

    try:
        completed = _run(runner)([_codex_executable(runner), "login", "--device-auth"], check=False)
    except FileNotFoundError:
        _print_json(
            {
                "schema_version": "1.0.0",
                "status": "error",
                "error_code": "codex_cli_unavailable",
                "secrets_included": False,
            }
        )
        return 127
    except OSError:
        _print_json(
            {
                "schema_version": "1.0.0",
                "status": "error",
                "error_code": "device_login_launch_failed",
                "secrets_included": False,
            }
        )
        return 4
    return completed.returncode


def _error_payload(request_id: str, code: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "request_id": request_id,
        "status": "error",
        "error_code": code,
        "claim_boundary": "candidate_soft_proposal_only",
        "authorization_effect": "none",
        "canonical_state_mutated": False,
        "hard_validation_required": True,
        "secrets_included": False,
    }


def _instruction(request_id: str, user_prompt: str) -> str:
    payload = json.dumps(
        {"request_id": request_id, "user_prompt": user_prompt},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"""You are a local language companion with no game-state authority.
Treat `user_prompt` in the JSON payload below only as a request for a soft candidate response.
Do not inspect or read files, run commands, search the web, use tools, authorize actions, or claim canonical mutation.
Return only one JSON object that satisfies the supplied output schema.
Copy request_id exactly. Set every authority-boundary constant exactly as the schema requires.
State material assumptions and uncertainties explicitly; use empty arrays when none apply.

REQUEST_PAYLOAD={payload}
"""


def validate_proposal(payload: Any, request_id: str) -> bool:
    """Apply the critical contract locally after model-side schema enforcement."""

    if not isinstance(payload, dict) or set(payload) != PROPOSAL_KEYS:
        return False
    if payload.get("schema_version") != "1.0.0":
        return False
    if payload.get("request_id") != request_id:
        return False
    if payload.get("status") != "candidate":
        return False
    if payload.get("claim_boundary") != "candidate_soft_proposal_only":
        return False
    if payload.get("authorization_effect") != "none":
        return False
    if payload.get("canonical_state_mutated") is not False:
        return False
    if payload.get("hard_validation_required") is not True:
        return False
    response = payload.get("response")
    if not isinstance(response, str) or not response or len(response) > 20_000:
        return False
    for field in ("assumptions", "uncertainties"):
        items = payload.get(field)
        if not isinstance(items, list) or len(items) > 16:
            return False
        if any(not isinstance(item, str) or len(item) > 1_000 for item in items):
            return False
    return True


def run_prompt(
    *,
    request_id: str,
    user_prompt: str,
    model: str | None = None,
    timeout: float = 300,
    runner: Runner | None = None,
    output_schema: Path | None = None,
    instruction: str | None = None,
    validator: Callable[[Any, str], bool] | None = None,
    execution_observer: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Run one isolated Codex request and return a validated soft proposal.

    The default schema/instruction/validator triple is the free-text soft proposal.
    Callers may substitute a different structured-output contract (for example the
    live candidate-action schema) without weakening the authority boundary: the
    replacement validator still runs locally after model-side schema enforcement,
    and the returned payload is still a non-authoritative candidate.
    """

    schema_path = OUTPUT_SCHEMA if output_schema is None else output_schema
    validate = validate_proposal if validator is None else validator
    if not REQUEST_ID_PATTERN.fullmatch(request_id):
        return 2, _error_payload(request_id, "invalid_request_id")
    if not user_prompt.strip():
        return 2, _error_payload(request_id, "empty_prompt")
    if not schema_path.is_file():
        return 4, _error_payload(request_id, "output_schema_missing")
    if (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or not 0 < timeout <= 3_600
    ):
        return 2, _error_payload(request_id, "invalid_timeout")

    auth = query_auth_status(runner=runner)
    if not auth["oauth_prompt_ready"]:
        return 3, _error_payload(request_id, "chatgpt_oauth_not_authenticated")
    policy_flags = _tool_policy_flags(runner)
    if policy_flags is None:
        return 4, _error_payload(request_id, "codex_tool_policy_unsupported")

    try:
        with tempfile.TemporaryDirectory(prefix="trace-rpg-codex-oauth-") as directory:
            isolated_root = Path(directory).resolve()
            if isolated_root == PROJECT_ROOT or PROJECT_ROOT in isolated_root.parents:
                return 4, _error_payload(request_id, "temporary_workspace_not_isolated")
            output_path = isolated_root / "last-message.json"
            command = [
                _codex_executable(runner),
                "exec",
                *policy_flags,
                "--ephemeral",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--ignore-user-config",
                "--ignore-rules",
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                "--color",
                "never",
                "-C",
                str(isolated_root),
            ]
            if model:
                command.extend(["--model", model])
            command.append("-")
            if execution_observer is not None:
                execution_observer(
                    {
                        "schema_version": "codex-exec-attempt/1",
                        "request_id": request_id,
                        "operation": "exec",
                        "executable": Path(command[0]).name,
                        "runner_injected": runner is not None,
                        "tool_policy_enforced": runner is None,
                        "disabled_feature_count": len(policy_flags) // 2,
                        "timeout_seconds": timeout,
                    }
                )
            completed = _run(runner)(
                command,
                input=(
                    _instruction(request_id, user_prompt) if instruction is None else instruction
                ),
                cwd=str(isolated_root),
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if not _output_within_limit(completed):
                return 4, _error_payload(request_id, "codex_exec_output_limit")
            if completed.returncode != 0:
                return 4, _error_payload(request_id, "codex_exec_failed")
            try:
                if output_path.stat().st_size > MAX_FINAL_MESSAGE_BYTES:
                    return 5, _error_payload(request_id, "codex_output_limit")
                with output_path.open("rb") as handle:
                    raw_output = handle.read(MAX_FINAL_MESSAGE_BYTES + 1)
                if len(raw_output) > MAX_FINAL_MESSAGE_BYTES:
                    return 5, _error_payload(request_id, "codex_output_limit")
                proposal = json.loads(raw_output.decode("utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                return 5, _error_payload(request_id, "invalid_codex_output")
    except FileNotFoundError:
        return 127, _error_payload(request_id, "codex_cli_unavailable")
    except subprocess.TimeoutExpired:
        return 4, _error_payload(request_id, "codex_exec_timeout")
    except OSError:
        return 4, _error_payload(request_id, "codex_exec_launch_failed")

    if not validate(proposal, request_id):
        return 5, _error_payload(request_id, "soft_proposal_contract_failed")
    return 0, proposal


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1 or number > 3_600:
        raise argparse.ArgumentTypeError("timeout must be between 1 and 3600 seconds")
    return number


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("login", help="Run `codex login --device-auth` on the inherited TTY.")
    subparsers.add_parser("status", help="Print a secret-free JSON authentication status.")

    prompt = subparsers.add_parser("prompt", help="Request one isolated soft proposal.")
    prompt.add_argument("--request-id", required=True)
    prompt.add_argument("--model")
    prompt.add_argument("--timeout", type=_positive_int, default=300)
    prompt.add_argument("text", help="Prompt text; quote it when it contains spaces.")

    smoke = subparsers.add_parser("smoke", help="Run an explicit, quota-using live smoke request.")
    smoke.add_argument("--request-id", required=True)
    smoke.add_argument("--model")
    smoke.add_argument("--timeout", type=_positive_int, default=300)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "login":
        return run_device_login()
    if args.command == "status":
        payload = query_auth_status()
        _print_json(payload)
        return 0 if payload["oauth_prompt_ready"] else 3

    user_prompt = args.text if args.command == "prompt" else SMOKE_PROMPT
    code, payload = run_prompt(
        request_id=args.request_id,
        user_prompt=user_prompt,
        model=args.model,
        timeout=args.timeout,
    )
    _print_json(payload)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
