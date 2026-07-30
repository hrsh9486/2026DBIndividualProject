"""Catalogue registration tests for lens-level evidence assets."""

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evidence_fixtures import digital_report, supported_result  # noqa: E402
from sync_focused_catalogue import build_catalogue  # noqa: E402


class CatalogueEvidenceTests(unittest.TestCase):
    def test_registers_only_existing_valid_lens_evidence(self):
        catalogue = {
            "schema_version": "1.0.0",
            "generated_at": "2026-07-28T00:00:00+00:00",
            "public_data_root": "/data",
            "assets": {},
            "sections": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            evidence_path = (
                Path(directory)
                / "evidence"
                / "digital-integration.json"
            )
            evidence_path.parent.mkdir(parents=True)
            evidence_path.write_text(
                json.dumps(digital_report(supported_result())),
                encoding="utf-8",
            )

            payload = build_catalogue(
                catalogue,
                public_data_dir=Path(directory),
            )

        digital = next(
            section
            for section in payload["sections"]
            if section["id"] == "digital-integration"
        )
        fiscal = next(
            section
            for section in payload["sections"]
            if section["id"] == "fiscal-capacity"
        )
        self.assertEqual(
            digital["evidence_asset_id"],
            "digital-integration-evidence",
        )
        self.assertNotIn("evidence_asset_id", fiscal)
        self.assertEqual(
            payload["assets"]["digital-integration-evidence"]["schema"],
            "evidence_report",
        )
        self.assertNotIn("fiscal-capacity-evidence", payload["assets"])


if __name__ == "__main__":
    unittest.main()
