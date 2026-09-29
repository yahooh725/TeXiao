"""Engineering verifier for MVP artifacts and expected failure cases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def verify(run_dir: Path, scenario: str, *, render_attempted: bool, render_ok: bool, error_code: str | None = None) -> dict[str, Any]:
    result = run_dir / "result.mp4"
    preview = run_dir / "preview.png"
    plan = run_dir / "plan.json"
    trace = run_dir / "execution_trace.json"
    checks: list[dict[str, Any]] = []

    if scenario == "normal":
        checks.append({"name": "plan_exists", "ok": plan.is_file()})
        checks.append({"name": "trace_exists", "ok": trace.is_file()})
        checks.append({"name": "preview_exists", "ok": preview.is_file()})
        checks.append({"name": "render_attempted", "ok": render_attempted})
        checks.append({"name": "render_ok", "ok": render_ok and result.is_file()})
        if all(item["ok"] for item in checks):
            return {"status": "verified", "checks": checks, "error_code": None}
        return {"status": "failed", "checks": checks, "error_code": error_code or "render_unverified"}

    expected = {
        "no_face": "no_face_detected",
        "multiple_faces": "multiple_faces",
        "unsupported_effect": "asset_not_found",
        "missing_asset": "asset_not_found",
        "invalid_video": "invalid_video",
    }.get(scenario)
    checks.append({"name": "expected_error", "ok": error_code == expected})
    checks.append({"name": "no_stale_result", "ok": not result.exists()})
    status = "expected_failure" if all(item["ok"] for item in checks) else "failed"
    return {"status": status, "checks": checks, "error_code": error_code}


def write_verification(path: Path, report: dict[str, Any]) -> None:
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
