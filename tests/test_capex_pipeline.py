"""Integration tests for the validation-first CapEx ETL orchestrator."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
import ast
from dataclasses import fields
from typing import get_type_hints


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_capex_pipeline import (  # noqa: E402
    _publish_artifacts,
    _select_artifact_entries,
    _validate_all_artifacts,
    _verify_written_artifacts,
)
from builders.capex_artifacts import CapexArtifacts  # noqa: E402
from config.capex_analysis import OUTPUTS  # noqa: E402
from models.capex_metrics import (  # noqa: E402
    FiscalMetrics,
    GovernmentMetrics,
    PrivateMetrics,
)
from transforms.capex_metrics import (  # noqa: E402
    calculate_fiscal_metrics,
    calculate_government_metrics,
    calculate_private_metrics,
)


def _existing_artifacts() -> CapexArtifacts:
    processed = ROOT / "data" / "processed"
    return CapexArtifacts(
        outputs={
            key: json.loads((processed / relative).read_text(encoding="utf-8"))
            for key, relative in OUTPUTS.items()
        },
    )


class CapexPipelineTests(unittest.TestCase):
    def test_structural_intermediates_are_typed_metrics_not_json_payloads(self):
        expectations = (
            (calculate_government_metrics, GovernmentMetrics),
            (calculate_private_metrics, PrivateMetrics),
            (calculate_fiscal_metrics, FiscalMetrics),
        )
        for calculation, expected_type in expectations:
            self.assertIs(get_type_hints(calculation)["return"], expected_type)
            self.assertEqual(
                tuple(field.name for field in fields(expected_type)),
                ("records", "sources"),
            )
        self.assertFalse((ROOT / "scripts/builders/capex_inputs.py").exists())

    def test_artifact_assembly_calls_typed_metric_calculations_directly(self):
        path = ROOT / "scripts/builders/capex_artifacts.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        assembly = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "build_capex_artifacts"
        )
        called_names = {
            node.func.id
            for node in ast.walk(assembly)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        expected_output_builders = {
            "build_execution_payload",
            "build_allocation_payload",
            "build_delivery_payload",
            "build_production_payload",
            "build_sector_payload",
            "build_correlations_payload",
            "build_private_response_payload",
            "build_fiscal_sustainability_payload",
            "build_summary_payload",
            "build_corporate_payload",
            "build_quality_payload",
            "build_states_payload",
            "build_crowding_in_payload",
        }
        self.assertTrue({
            "calculate_government_metrics",
            "calculate_private_metrics",
            "calculate_fiscal_metrics",
        }.issubset(called_names))
        self.assertEqual(
            {name for name in called_names if name.startswith("build_")},
            expected_output_builders,
        )
        self.assertTrue({
            "build_government_payload",
            "build_private_payload",
            "build_fiscal_payload",
        }.isdisjoint(called_names))
        for obsolete in ("capex_analysis.py", "capex_delivery.py", "capex_depth.py"):
            self.assertFalse((ROOT / "scripts/builders" / obsolete).exists())

    def test_pipeline_python_does_not_use_lambdas(self):
        for path in (ROOT / "scripts").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            self.assertFalse(
                any(isinstance(node, ast.Lambda) for node in ast.walk(tree)),
                f"{path} passes anonymous behavior instead of making the call explicit",
            )

    def test_orchestrator_calls_concrete_pipeline_functions(self):
        path = ROOT / "scripts" / "build_capex_pipeline.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        run_pipeline = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "run_pipeline"
        )
        called_names = {
            node.func.id
            for node in ast.walk(run_pipeline)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue({
            "acquire_capex_sources",
            "load_landed_capex_sources",
            "build_capex_artifacts",
            "_validate_all_artifacts",
            "_select_artifact_entries",
            "_publish_artifacts",
            "_verify_written_artifacts",
        }.issubset(called_names))
        parameter_names = {
            argument.arg
            for argument in (*run_pipeline.args.args, *run_pipeline.args.kwonlyargs)
        }
        self.assertTrue({"acquire", "build", "writer"}.isdisjoint(parameter_names))

    def test_layers_do_not_import_executable_build_modules(self):
        for folder in (ROOT / "scripts/builders", ROOT / "scripts/transforms"):
            for path in folder.glob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                imports = [
                    alias.name
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Import)
                    for alias in node.names
                ] + [
                    node.module or ""
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom)
                ]
                self.assertFalse(
                    any(name.startswith("build_") for name in imports),
                    f"{path} imports an executable build module",
                )
                self.assertFalse(
                    any(name.startswith("extractors") for name in imports),
                    f"{path} crosses from transformation into extraction",
                )

    def test_validated_artifacts_are_written_to_processed_and_public_paths(self):
        artifacts = _existing_artifacts()
        with tempfile.TemporaryDirectory() as project_root:
            root = Path(project_root)
            entries = _validate_all_artifacts(artifacts)
            written = _publish_artifacts(root, entries)
            _verify_written_artifacts(root, entries)
            self.assertEqual(len(written), 26)
            for relative in OUTPUTS.values():
                processed = root / "data/processed" / relative
                public = root / "frontend/public/data" / relative
                self.assertEqual(processed.read_bytes(), public.read_bytes())

    def test_output_target_writes_only_its_processed_and_public_files(self):
        entries = _validate_all_artifacts(_existing_artifacts())
        selected = _select_artifact_entries(entries, "output:quality")
        with tempfile.TemporaryDirectory() as project_root:
            root = Path(project_root)
            written = _publish_artifacts(root, selected)
            _verify_written_artifacts(root, selected)
            self.assertEqual(len(written), 2)
            self.assertTrue((root / "data/processed" / OUTPUTS["quality"]).is_file())
            self.assertTrue((root / "frontend/public/data" / OUTPUTS["quality"]).is_file())
            self.assertFalse((root / "data/processed" / OUTPUTS["states"]).exists())

    def test_incomplete_output_set_is_rejected_before_publication(self):
        artifacts = _existing_artifacts()
        artifacts.outputs.pop("summary")
        with tempfile.TemporaryDirectory() as project_root:
            with self.assertRaisesRegex(ValueError, "artifact set mismatch"):
                _validate_all_artifacts(artifacts)
            self.assertFalse((Path(project_root) / "data").exists())

    def test_every_artifact_is_validated_before_the_first_write(self):
        artifacts = _existing_artifacts()
        artifacts.outputs["summary"] = {}
        with tempfile.TemporaryDirectory() as project_root:
            with self.assertRaisesRegex(Exception, "validation failed"):
                _validate_all_artifacts(artifacts)
            self.assertFalse((Path(project_root) / "data").exists())


if __name__ == "__main__":
    unittest.main()
