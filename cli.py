"""Command line entry point for the bounded FaceStyleLens Agent MVP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .executor import execute
from .planner import FIXED_PROMPT, make_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the FaceStyleLens Agent v2 MVP")
    parser.add_argument("--prompt", default=FIXED_PROMPT)
    parser.add_argument("--fixture", default="normal_single_face")
    parser.add_argument("--run-dir", default="mvp/runs/demo")
    parser.add_argument("--no-mp4", action="store_true", help="only produce the deterministic preview")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "mvp" / "fixtures" / "manifest.json").read_text(encoding="utf-8"))
    scenario = next(item["scenario"] for item in manifest["fixtures"] if item["id"] == args.fixture)
    plan = make_plan(args.prompt, scenario=scenario)
    report = execute(root, plan, args.fixture, (root / args.run_dir).resolve(), render_mp4=not args.no_mp4)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"verified", "expected_failure"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
