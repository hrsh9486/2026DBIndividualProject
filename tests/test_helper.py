"""Tests for the shared pipeline helpers."""

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import helper  # noqa: E402


class CleanFloatTests(unittest.TestCase):
    def test_converts_and_rounds_numeric_values(self):
        self.assertEqual(helper.clean_float("1.23456"), 1.2346)
        self.assertEqual(helper.clean_float("1.23456", 2), 1.23)
        self.assertEqual(helper.clean_float("1.23456", None), 1.23456)

    def test_maps_non_finite_and_invalid_values_to_none(self):
        values = [None, "not-a-number", math.nan, math.inf, -math.inf]
        for value in values:
            with self.subTest(value=value):
                self.assertIsNone(helper.clean_float(value))


class JsonExportTests(unittest.TestCase):
    def test_creates_nested_directory_and_writes_strict_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = helper.write_json(
                {"label": "Rupee ₹", "value": 1.25},
                "nested/result.json",
                temp_dir,
            )

            self.assertEqual(
                json.loads(output_path.read_text(encoding="utf-8")),
                {"label": "Rupee ₹", "value": 1.25},
            )

    def test_serialization_failure_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "result.json"
            output_path.write_text('{"status": "valid"}\n', encoding="utf-8")

            with self.assertRaises(ValueError):
                helper.write_json({"value": math.nan}, output_path.name, temp_dir)

            self.assertEqual(
                json.loads(output_path.read_text(encoding="utf-8")),
                {"status": "valid"},
            )


if __name__ == "__main__":
    unittest.main()
