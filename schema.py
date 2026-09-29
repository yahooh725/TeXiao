"""Small strict validator for plans and tool arguments."""

from __future__ import annotations

from typing import Any


TOOLS = {
    "search_effect_catalog",
    "face_detect_and_track",
    "apply_face_asset",
    "apply_beauty_effect",
    "compose_timeline",
    "render_preview",
    "verify_result",
}


class SchemaError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _number(value: Any, name: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaError("invalid_params", f"{name} must be a number")
    if not low <= float(value) <= high:
        raise SchemaError("invalid_params", f"{name} must be in [{low}, {high}]")
    return float(value)


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, dict):
        raise SchemaError("invalid_plan", "plan must be an object")
    required = {"schema_version", "prompt", "input", "steps", "expected"}
    if set(plan) != required:
        raise SchemaError("invalid_plan", "plan keys do not match the fixed contract")
    if plan["schema_version"] != "facestyle.agent.plan.v1":
        raise SchemaError("invalid_plan", "unsupported schema version")
    if not isinstance(plan["prompt"], str) or not plan["prompt"].strip():
        raise SchemaError("invalid_plan", "prompt must be non-empty")
    if plan["input"] != {"video_ref": "input_video", "mode": "fixture"}:
        raise SchemaError("invalid_plan", "only the fixture input contract is allowed")
    if not isinstance(plan["steps"], list) or not plan["steps"]:
        raise SchemaError("invalid_plan", "steps must be a non-empty list")
    for step in plan["steps"]:
        if not isinstance(step, dict) or set(step) != {"tool", "args"}:
            raise SchemaError("invalid_step", "each step must contain only tool and args")
        tool = step["tool"]
        if tool not in TOOLS:
            raise SchemaError("tool_not_allowed", f"tool is not allow-listed: {tool}")
        if not isinstance(step["args"], dict):
            raise SchemaError("invalid_step", f"args for {tool} must be an object")
        _validate_args(tool, step["args"])
    expected = plan["expected"]
    if not isinstance(expected, dict) or set(expected) != {"fps", "duration_frames", "output_kind"}:
        raise SchemaError("invalid_plan", "expected output contract is incomplete")
    if expected["fps"] != 30 or not isinstance(expected["duration_frames"], int) or expected["duration_frames"] <= 0:
        raise SchemaError("invalid_plan", "expected fps/duration is invalid")
    if expected["output_kind"] not in {"mp4", "png"}:
        raise SchemaError("invalid_plan", "output_kind must be mp4 or png")
    return plan


def _validate_args(tool: str, args: dict[str, Any]) -> None:
    if tool == "search_effect_catalog":
        if set(args) != {"query"} or not isinstance(args["query"], str) or not 1 <= len(args["query"].strip()) <= 64:
            raise SchemaError("invalid_params", "search query must be a 1–64 character string")
    elif tool == "face_detect_and_track":
        if args != {"video_ref": "input_video", "mode": "fixture"}:
            raise SchemaError("invalid_params", "only fixture-aware tracking is allowed")
    elif tool == "apply_face_asset":
        allowed = {"asset_id", "tracks_ref", "opacity", "scale", "anchor"}
        if set(args) != allowed or not isinstance(args["asset_id"], str) or args["tracks_ref"] != "face_tracks":
            raise SchemaError("invalid_params", "face asset args are invalid")
        _number(args["opacity"], "opacity", 0, 1)
        _number(args["scale"], "scale", 0.5, 2)
        if args["anchor"] not in {"forehead", "nose", "cheeks"}:
            raise SchemaError("invalid_params", "unsupported face anchor")
    elif tool == "apply_beauty_effect":
        if set(args) != {"preset", "strength"} or args["preset"] != "natural_skin":
            raise SchemaError("unsupported_preset", "only natural_skin is available in the MVP")
        _number(args["strength"], "strength", 0, 1)
    elif tool == "compose_timeline":
        allowed = {"duration_frames", "fps", "zoom_from", "zoom_to", "overlay_refs", "beauty_ref"}
        if set(args) != allowed or args["fps"] != 30 or not isinstance(args["duration_frames"], int):
            raise SchemaError("invalid_timeline", "timeline args are invalid")
        _number(args["zoom_from"], "zoom_from", 1, 1.2)
        _number(args["zoom_to"], "zoom_to", 1, 1.2)
        if not isinstance(args["overlay_refs"], list) or not args["overlay_refs"]:
            raise SchemaError("invalid_timeline", "at least one overlay is required")
    elif tool == "render_preview":
        if set(args) != {"output_kind", "props_ref"} or args["output_kind"] not in {"mp4", "png"}:
            raise SchemaError("invalid_params", "render output contract is invalid")
    elif tool == "verify_result":
        if set(args) != {"output_ref", "expected_ref"}:
            raise SchemaError("invalid_params", "verification contract is invalid")
