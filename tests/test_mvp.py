from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mvp.executor import execute
from mvp.planner import FIXED_PROMPT, make_plan
from mvp.schema import SchemaError, validate_plan


ROOT = Path(__file__).resolve().parents[2]


class MvpContractTests(unittest.TestCase):
    def test_fixed_prompt_plan_is_valid(self) -> None:
        plan = make_plan(FIXED_PROMPT)
        self.assertEqual(plan["schema_version"], "facestyle.agent.plan.v1")
        validate_plan(plan)

    def test_arbitrary_tool_is_rejected(self) -> None:
        plan = make_plan(FIXED_PROMPT)
        plan["steps"].append({"tool": "run_shell", "args": {"command": "echo unsafe"}})
        with self.assertRaises(SchemaError):
            validate_plan(plan)

    def test_no_face_is_expected_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = execute(ROOT, make_plan(FIXED_PROMPT, scenario="no_face"), "no_face", Path(tmp), render_mp4=False)
            self.assertEqual(report["status"], "expected_failure")
            self.assertEqual(report["error_code"], "no_face_detected")
            self.assertFalse((Path(tmp) / "result.mp4").exists())

    def test_multiple_faces_is_expected_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = execute(ROOT, make_plan(FIXED_PROMPT, scenario="multiple_faces"), "multiple_faces", Path(tmp), render_mp4=False)
            self.assertEqual(report["status"], "expected_failure")
            self.assertEqual(report["error_code"], "multiple_faces")

    def test_missing_asset_does_not_fabricate_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = execute(ROOT, make_plan(FIXED_PROMPT, scenario="missing_asset"), "missing_asset", Path(tmp), render_mp4=False)
            self.assertEqual(report["status"], "expected_failure")
            self.assertEqual(report["error_code"], "asset_not_found")
            trace = json.loads((Path(tmp) / "execution_trace.json").read_text(encoding="utf-8"))
            self.assertIn("asset_not_found", json.dumps(trace, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
