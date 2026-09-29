"""Deterministic planner for the fixed MVP scenario."""

from __future__ import annotations

from typing import Any


FIXED_PROMPT = "加小兔子特效，轻微美颜，镜头慢慢推进。"


def make_plan(prompt: str, scenario: str = "normal") -> dict[str, Any]:
    text = prompt.strip()
    lower = text.lower()
    bunny = any(term in text or term in lower for term in ("兔", "bunny"))
    query = "小兔子" if bunny else ("龙" if scenario == "unsupported_effect" else "小兔子")
    missing_id = "local.missing.asset" if scenario == "missing_asset" else None
    assets = [
        ("兔耳朵", "forehead", 0.92, 1.0),
        ("兔鼻子", "nose", 0.88, 0.72),
        ("兔胡须", "cheeks", 0.72, 0.82),
    ]
    steps: list[dict[str, Any]] = []
    steps.append({"tool": "face_detect_and_track", "args": {"video_ref": "input_video", "mode": "fixture"}})
    for query_part, anchor, opacity, scale in assets:
        steps.append({"tool": "search_effect_catalog", "args": {"query": query_part if bunny else query}})
        steps.append({
            "tool": "apply_face_asset",
            "args": {
                "asset_id": missing_id or {"兔耳朵": "local.bunny.ears", "兔鼻子": "local.bunny.nose", "兔胡须": "local.bunny.whiskers"}[query_part],
                "tracks_ref": "face_tracks",
                "opacity": opacity,
                "scale": scale,
                "anchor": anchor,
            },
        })
    steps.extend([
        {"tool": "apply_beauty_effect", "args": {"preset": "natural_skin", "strength": 0.25}},
        {"tool": "compose_timeline", "args": {
            "duration_frames": 150,
            "fps": 30,
            "zoom_from": 1.0,
            "zoom_to": 1.08,
            "overlay_refs": ["local.bunny.ears", "local.bunny.nose", "local.bunny.whiskers"],
            "beauty_ref": "natural_skin",
        }},
        {"tool": "render_preview", "args": {"output_kind": "mp4", "props_ref": "timeline_props"}},
        {"tool": "verify_result", "args": {"output_ref": "result.mp4", "expected_ref": "expected_output"}},
    ])
    return {
        "schema_version": "facestyle.agent.plan.v1",
        "prompt": text,
        "input": {"video_ref": "input_video", "mode": "fixture"},
        "steps": steps,
        "expected": {"fps": 30, "duration_frames": 150, "output_kind": "mp4"},
    }
