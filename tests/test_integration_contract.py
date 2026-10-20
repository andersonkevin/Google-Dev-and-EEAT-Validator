"""Local contract discovery and evaluation-design safeguards."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_validator
from describe import describe
from evaluate_validator import evaluate
from rule_catalog import VERSION

ROOT = Path(__file__).resolve().parents[1]


class IntegrationContractTests(unittest.TestCase):
    def test_describe_cli_needs_no_bundle_and_matches_supported_schemas(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/describe.py")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        contract = json.loads(result.stdout)
        self.assertEqual(contract, describe())
        self.assertEqual(contract["version"], VERSION)
        self.assertEqual(contract["catalog_version"], VERSION)
        self.assertEqual(contract["mapping_version"], "2.0.0")
        self.assertEqual(contract["contracts"], {
            "bundle": 1, "review_receipt": 2, "report": 2, "observation": 1,
            "review_plan": 1, "evaluation_manifest": 1, "evaluation_report": 2})
        self.assertFalse(contract["publication_approved"])
        self.assertFalse(contract["network_calls"])
        self.assertFalse(contract["model_calls"])

    def test_command_paths_are_present_in_distribution(self):
        from release import FILES
        for command in describe()["read_only_commands"].values():
            self.assertIn(command, FILES)
            self.assertTrue((ROOT / command).is_file())


class EvaluationDesignTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_validator.ValidatorTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def manifest(self):
        path = self.fixture.evaluation()
        return path, json.loads(path.read_text())

    def evaluate(self, path, value):
        path.write_text(json.dumps(value))
        return evaluate(path, self.fixture.snapshot)

    def test_exact_draft_cannot_appear_in_both_splits(self):
        path, value = self.manifest()
        value["cases"].append(value["cases"][0] | {"id": "held-out", "split": "holdout"})
        with self.assertRaisesRegex(ValueError, "crosses development/holdout"):
            self.evaluate(path, value)

    def test_changing_bundle_context_does_not_hide_leakage(self):
        path, value = self.manifest()
        self.fixture.bundle["brief"]["purpose"] = "Another purpose"
        self.fixture.path = self.fixture.root / "second-bundle.json"
        self.fixture.save()
        other = json.loads(self.fixture.evaluation().read_text())["cases"][0]
        value["cases"].append(other | {"id": "held-out", "split": "holdout"})
        with self.assertRaisesRegex(ValueError, "crosses development/holdout"):
            self.evaluate(path, value)

    def test_same_split_repeats_are_disclosed_without_rejecting_stage_variants(self):
        path, value = self.manifest()
        value["cases"].append(value["cases"][0] | {"id": "second-check"})
        result = self.evaluate(path, value)
        self.assertEqual(result["case_count"], 2)
        self.assertEqual(result["dataset_summary"]["unique_draft_count"], 1)
        self.assertEqual(result["dataset_summary"]["counts"]["split"], {"development": 2})
        self.assertEqual(result["dataset_summary"]["leakage_check"], "exact_draft_bytes_only")

    def test_missing_design_coverage_is_not_silently_calibrated(self):
        path, value = self.manifest()
        result = self.evaluate(path, value)
        codes = {w["code"] for w in result["dataset_summary"]["warnings"]}
        self.assertTrue({"labeler_kind_unspecified", "no_holdout_cases", "no_real_content_cases"} <= codes)
        self.assertEqual(result["calibration_status"], "not_established")
        self.assertFalse(result["independence_verified"])

    def test_shared_reviewer_and_model_are_disclosed(self):
        receipt = self.fixture.reviews()
        record = json.loads(receipt.read_text())
        record["actor"] = {"kind": "ai", "identity": "Synthetic reviewer", "model": "fixture-model",
                           "run_id": "fixture", "relationship_to_author": "same_agent"}
        receipt.write_text(json.dumps(record))
        path, value = self.manifest()
        value["cases"][0].update(labeler="Synthetic reviewer", labeler_kind="ai", labeler_model="fixture-model",
                                 reviews=receipt.name, reviews_sha256=test_validator.sha(receipt.read_bytes()))
        result = self.evaluate(path, value)
        codes = {w["code"] for w in result["dataset_summary"]["warnings"]}
        self.assertTrue({"labeler_is_reviewer", "labeler_and_reviewer_same_model", "reviewer_is_author"} <= codes)
        self.assertFalse(result["independence_verified"])

    def test_distinct_drafts_can_use_separate_splits(self):
        path, value = self.manifest()
        original = (self.fixture.root / "draft.html").read_bytes()
        self.fixture.html = "<h1>Distinct held-out page</h1><p>Exports preserve records.</p>"
        self.fixture.bundle["content"] = "held-out.html"
        self.fixture.path = self.fixture.root / "held-out-bundle.json"
        self.fixture.save()
        (self.fixture.root / "held-out.html").write_text(self.fixture.html)
        # save() writes draft.html; restore the development content before validation.
        (self.fixture.root / "draft.html").write_bytes(original)
        other = json.loads(self.fixture.evaluation().read_text())["cases"][0]
        value["cases"].append(other | {"id": "held-out", "split": "holdout"})
        result = self.evaluate(path, value)
        self.assertEqual(result["dataset_summary"]["unique_draft_count"], 2)
        self.assertFalse(any(w["code"] in ("no_holdout_cases", "no_development_cases")
                             for w in result["dataset_summary"]["warnings"]))


if __name__ == "__main__":
    unittest.main()
