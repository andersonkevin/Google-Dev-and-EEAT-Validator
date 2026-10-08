"""Public mode and distribution contracts; no private archive required."""
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from rule_catalog import VERSION, catalog
from validate_draft import validate


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_validator.ValidatorTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def public_report(self, review=None):
        return validate(self.fixture.path, review_path=review, references_only=True)

    def test_references_only_does_not_read_snapshot(self):
        with patch("validate_draft.source_index", side_effect=AssertionError("No archive access")):
            result = self.public_report()
        self.assertEqual(result["source_verification"], "references_only_not_verified")
        self.assertTrue(result["source_review_required"])
        self.assertFalse(result["source_coverage_complete"])
        self.assertTrue(all(not f["source_chunk_ids"] for f in result["findings"]))

    def test_completed_editorial_receipts_do_not_remove_source_gate(self):
        report = self.public_report()
        receipt = {"fingerprint": report["fingerprint"], "decisions": [
            {"rule_id": f["rule_id"], "status": "pass", "reviewer": "Synthetic reviewer",
             "reason": "Synthetic adjudication", "reviewed_at": "2026-10-08", "evidence_ids": ["e1"]}
            for f in report["findings"] if f["status"] == "needs_review"]}
        path = self.fixture.root / "reviews.json"
        path.write_text(json.dumps(receipt))
        self.assertEqual(self.public_report(path)["readiness"], "review_required")

    def test_static_failures_still_block_public_mode(self):
        self.fixture.html = "<p>No main title</p>"
        self.fixture.save()
        self.assertEqual(self.public_report()["readiness"], "blocked")

    def test_mode_changes_fingerprint(self):
        self.assertNotEqual(self.public_report()["fingerprint"], self.fixture.report()["fingerprint"])

    def test_missing_or_conflicting_modes_rejected(self):
        with self.assertRaises(ValueError):
            validate(self.fixture.path)
        with self.assertRaises(ValueError):
            validate(self.fixture.path, self.fixture.snapshot, references_only=True)

    def test_readonly_quickstart_exit_code(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/validate_draft.py"),
            str(ROOT / "examples/bundle.json"), "--references-only"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["readiness"], "review_required")

    def test_coverage_cannot_use_references_only(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/validate_draft.py"),
            "--references-only", "--coverage"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)

    def test_map_has_public_urls_not_snapshot_bindings(self):
        mapping = json.loads((ROOT / "references/eeat-map.json").read_text())
        self.assertNotIn("snapshot", mapping)
        self.assertNotIn("chunks_sha256", mapping)
        self.assertEqual(len(mapping["criteria"]), 20)
        known = {r["id"] for r in catalog()}
        for source in mapping["sources"].values():
            self.assertNotIn("chunk_ids", source)
            self.assertTrue(all(url.startswith("https://") for url in source["urls"]))
        for criterion in mapping["criteria"]:
            self.assertTrue(set(criterion["direct_rules"] + criterion["supporting_rules"]) <= known)

    def test_version_and_license(self):
        self.assertEqual((ROOT / "VERSION").read_text().strip(), VERSION)
        self.assertIn("MIT License", (ROOT / "LICENSE").read_text())

    def test_no_absolute_personal_paths_in_distributed_text(self):
        for directory in ("tools", "references", "examples", "docs"):
            for path in (ROOT / directory).rglob("*"):
                if path.is_file() and path.suffix in (".py", ".md", ".json", ".txt", ".html"):
                    self.assertIsNone(re.search(r"/(?:Users|home)/[^/\s]+/", path.read_text()), path.name)


if __name__ == "__main__":
    unittest.main()
