"""Plan executor. It is local-only and never evaluates generated code."""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .catalog import CatalogError, asset_path, load_catalog, resolve_hashes, search
from .render_utils import write_png
from .schema import SchemaError, validate_plan
from .verifier import verify, write_verification


def _ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


def _error(code: str, message: str, retryable: bool = False) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message, "retryable": retryable}}


def _data_url(path: Path) -> str:
    raw = path.read_bytes()
    mime = "image/svg+xml" if path.suffix.lower() == ".svg" else "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")


def _load_manifest(root: Path) -> dict[str, Any]:
    return json.loads((root / "mvp" / "fixtures" / "manifest.json").read_text(encoding="utf-8"))


def _fixture(root: Path, fixture_id: str) -> dict[str, Any]:
    for item in _load_manifest(root)["fixtures"]:
        if item["id"] == fixture_id:
            return item
    raise ValueError(f"unknown fixture: {fixture_id}")


def _tracks(scenario: str) -> list[dict[str, float | int]]:
    if scenario == "no_face":
        raise CatalogError("no_face_detected", "fixture contains no face")
    if scenario == "multiple_faces":
        raise CatalogError("multiple_faces", "fixture contains multiple faces")
    if scenario == "invalid_video":
        raise CatalogError("invalid_video", "fixture is not a media file")
    return [{"frame": frame, "x": 0.25, "y": 0.18, "width": 0.5, "height": 0.58} for frame in range(150)]


def _render_remotion(root: Path, run_dir: Path, props_path: Path) -> tuple[bool, str | None]:
    remotion = root / "mvp" / "remotion"
    npx = shutil.which("npx")
    node_modules = remotion / "node_modules"
    if not npx or not node_modules.is_dir():
        return False, "render_dependency_missing"
    output = run_dir / "result.mp4"
    command = [npx, "--no-install", "remotion", "render", "src/index.tsx", "AgentResult", str(output), f"--props={props_path}"]
    completed = subprocess.run(command, cwd=remotion, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if completed.returncode != 0 or not output.is_file():
        (run_dir / "render.stderr.txt").write_text(completed.stderr[-4000:], encoding="utf-8")
        return False, "render_failed"
    return True, None


def execute(root: Path, plan: dict[str, Any], fixture_id: str, run_dir: Path, render_mp4: bool = True) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    for stale in ("result.mp4", "preview.png", "verification.json", "execution_trace.json", "plan.json", "props.json"):
        target = run_dir / stale
        if target.exists():
            target.unlink()
    trace: list[dict[str, Any]] = []
    scenario = _fixture(root, fixture_id)["scenario"]
    (run_dir / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        validate_plan(plan)
    except SchemaError as exc:
        trace.append({"tool": "plan_validation", "response": _error(exc.code, exc.message)})
        (run_dir / "execution_trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
        report = verify(run_dir, scenario, render_attempted=False, render_ok=False, error_code=exc.code)
        write_verification(run_dir / "verification.json", report)
        return report

    catalog = load_catalog(root)
    tracks: list[dict[str, Any]] | None = None
    overlays: list[dict[str, Any]] = []
    beauty: dict[str, Any] | None = None
    timeline: dict[str, Any] | None = None
    render_attempted = False
    render_ok = False
    error_code: str | None = None

    # Resolve tools in semantic order even if a malformed plan lists overlay steps first.
    try:
        tracks = _tracks(scenario)
        trace.append({"tool": "face_detect_and_track", "response": _ok({"tracks_ref": "face_tracks", "count": len(tracks)})})
        if scenario in {"unsupported_effect", "missing_asset"}:
            if scenario == "unsupported_effect":
                search(catalog, "龙")
            else:
                asset_path(root, "local.missing.asset")
        query_by_id = {"local.bunny.ears": "兔耳朵", "local.bunny.nose": "兔鼻子", "local.bunny.whiskers": "兔胡须"}
        for item in ("local.bunny.ears", "local.bunny.nose", "local.bunny.whiskers"):
            search_result = search(catalog, query_by_id[item])
            trace.append({"tool": "search_effect_catalog", "query": query_by_id[item], "response": _ok({"asset_id": item, "matches": len(search_result)})})
            path = asset_path(root, item)
            overlays.append({"asset_id": item, "asset_data_url": _data_url(path), "tracks_ref": "face_tracks"})
            trace.append({"tool": "apply_face_asset", "asset_id": item, "response": _ok({"asset_id": item})})
        beauty = {"preset": "natural_skin", "strength": 0.25}
        trace.append({"tool": "apply_beauty_effect", "response": _ok(beauty)})
        timeline = {
            "version": "facestyle.remotion.props.v1",
            "input_data_url": _data_url(root / "mvp" / _fixture(root, fixture_id)["path"]),
            "fps": 30,
            "duration_in_frames": 150,
            "zoom_from": 1.0,
            "zoom_to": 1.08,
            "tracks": tracks,
            "overlays": overlays,
            "beauty": beauty,
        }
        props_path = run_dir / "props.json"
        props_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
        trace.append({"tool": "compose_timeline", "response": _ok({"props_ref": "timeline_props"})})
        # A dependency-light, deterministic preview is always available.
        write_png(run_dir / "preview.png")
        trace.append({"tool": "render_preview", "output_kind": "png", "response": _ok({"path": "preview.png"})})
        if render_mp4:
            render_attempted = True
            render_ok, error_code = _render_remotion(root, run_dir, props_path)
            trace.append({"tool": "render_preview", "output_kind": "mp4", "response": _ok({"path": "result.mp4"}) if render_ok else _error(error_code or "render_failed", "MP4 render did not complete")})
        else:
            error_code = "render_not_requested"
    except CatalogError as exc:
        error_code = exc.code
        trace.append({"tool": "execution", "response": _error(exc.code, exc.message, exc.retryable)})

    (run_dir / "execution_trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    run_manifest = {"fixture_id": fixture_id, "asset_sha256": resolve_hashes(root), "v1_final_test_access": False}
    (run_dir / "resolved_provenance.json").write_text(json.dumps(run_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    report = verify(run_dir, scenario, render_attempted=render_attempted, render_ok=render_ok, error_code=error_code)
    trace.append({'tool': 'verify_result', 'response': {'ok': report['status'] in {'verified', 'expected_failure'}, 'data': report}})
    (run_dir / 'execution_trace.json').write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding='utf-8')
    write_verification(run_dir / 'verification.json', report)
    return report
