"""V2 actor, criterion and source-review boundaries using synthetic temporary data."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import test_validator
from evaluate_validator import evaluate
from rule_catalog import criteria_map
from validate_draft import read_json, review_template, sha, validate, write_report

ROOT = Path(__file__).resolve().parents[1]


class V2Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_validator.ValidatorTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def report(self, path=None):
        return validate(self.fixture.path, review_path=path, references_only=True)

    def receipt(self):
        path = self.fixture.reviews()
        data = json.loads(path.read_text())
        data["fingerprint"] = self.report()["fingerprint"]
        data["actor"] = {"kind": "ai", "identity": "Synthetic reviewer", "model": "fixture-only",
                         "run_id": "test-01", "relationship_to_author": "same_agent"}
        return path, data

    def run_receipt(self, path, data):
        path.write_text(json.dumps(data))
        return self.report(path)

    def test_ai_review_can_reach_owner_without_archive_not_publication(self):
        result = self.run_receipt(*self.receipt())
        self.assertEqual(result["readiness"], "ready_for_owner_review")
        self.assertFalse(result["publication_approved"])
        self.assertFalse(result["reviewer_identity_verified"])
        self.assertFalse(result["source_coverage_complete"])
        self.assertEqual(result["source_verification"], "references_only_not_verified")
        self.assertEqual(result["source_review_assurance"], "operator_attestation_only")
        self.assertEqual(result["review_actor"]["relationship_to_author"], "same_agent")

    def test_all_criteria_have_individual_pending_findings(self):
        result = self.report()
        self.assertEqual(result["eeat_counts"], {"needs_review": 20})
        self.assertTrue({"TRUST-06", "QUALITY-02"} <= {c["criterion_id"] for c in result["eeat_criteria"]})

    def test_broad_rule_pass_does_not_fill_criteria(self):
        path, receipt = self.receipt()
        receipt["criteria"] = []
        result = self.run_receipt(path, receipt)
        self.assertEqual(result["eeat_counts"], {"needs_review": 20})
        self.assertEqual(result["readiness"], "review_required")

    def test_each_criterion_failure_blocks(self):
        for index in range(20):
            with self.subTest(index=index):
                path, receipt = self.receipt()
                receipt["criteria"][index]["status"] = "fail"
                self.assertEqual(self.run_receipt(path, receipt)["readiness"], "blocked")

    def test_source_failure_blocks(self):
        path, receipt = self.receipt()
        receipt["sources"][0]["status"] = "fail"
        self.assertEqual(self.run_receipt(path, receipt)["readiness"], "blocked")

    def test_missing_source_stays_unresolved(self):
        path, receipt = self.receipt()
        receipt["sources"].pop()
        result = self.run_receipt(path, receipt)
        self.assertTrue(result["source_review_required"])
        self.assertEqual(result["readiness"], "review_required")

    def test_source_not_applicable_cannot_bypass_review(self):
        path, receipt = self.receipt()
        receipt["sources"][0]["status"] = "not_applicable"
        with self.assertRaises(ValueError):
            self.run_receipt(path, receipt)

    def test_unknown_evidence_is_rejected_in_all_receipt_groups(self):
        for group in ("decisions", "criteria", "sources"):
            with self.subTest(group=group):
                path, receipt = self.receipt()
                receipt[group][0]["evidence_ids"] = ["invented"]
                with self.assertRaises(ValueError):
                    self.run_receipt(path, receipt)

    def test_duplicate_records_are_rejected(self):
        for group in ("decisions", "criteria", "sources"):
            with self.subTest(group=group):
                path, receipt = self.receipt()
                receipt[group].append(receipt[group][0])
                with self.assertRaises(ValueError):
                    self.run_receipt(path, receipt)

    def test_unknown_criterion_rejected(self):
        path, receipt = self.receipt()
        receipt["criteria"][0]["criterion_id"] = "UNKNOWN"
        with self.assertRaises(ValueError):
            self.run_receipt(path, receipt)

    def test_unavailable_evidence_may_remain_unresolved(self):
        path, receipt = self.receipt()
        receipt["criteria"][0].update(status="needs_review", evidence_ids=[], reason="No supporting evidence supplied")
        self.assertEqual(self.run_receipt(path, receipt)["readiness"], "review_required")

    def test_exception_requires_evidence(self):
        path, receipt = self.receipt()
        receipt["criteria"][0].update(status="not_applicable", evidence_ids=[])
        with self.assertRaises(ValueError):
            self.run_receipt(path, receipt)

    def test_evidenced_exception_is_explicit_not_inferred(self):
        path, receipt = self.receipt()
        receipt["criteria"][2].update(status="not_applicable", reason="Fixture has no first-hand claim; scope reviewed")
        result = self.run_receipt(path, receipt)
        self.assertEqual(result["eeat_counts"], {"pass": 19, "not_applicable": 1})

    def test_actor_identity_must_match_decisions(self):
        path, receipt = self.receipt()
        receipt["actor"]["identity"] = "Different identity"
        with self.assertRaises(ValueError):
            self.run_receipt(path, receipt)

    def test_ai_actor_requires_model_run_and_author_relationship(self):
        for key in ("model", "run_id", "relationship_to_author", "identity", "kind"):
            with self.subTest(key=key):
                path, receipt = self.receipt()
                receipt["actor"].pop(key)
                with self.assertRaises(ValueError):
                    self.run_receipt(path, receipt)

    def test_ai_cannot_label_relationship_human_review(self):
        path, receipt = self.receipt()
        receipt["actor"]["relationship_to_author"] = "human_review"
        with self.assertRaises(ValueError):
            self.run_receipt(path, receipt)

    def test_illustration_never_reaches_owner_readiness(self):
        path, receipt = self.receipt()
        receipt["purpose"] = "illustration"
        self.assertEqual(self.run_receipt(path, receipt)["readiness"], "review_required")

    def test_stale_receipt_applies_no_actor_or_decisions(self):
        path, receipt = self.receipt()
        receipt["fingerprint"] = "old"
        result = self.run_receipt(path, receipt)
        self.assertIsNone(result["review_actor"])
        self.assertEqual(result["eeat_counts"], {"needs_review": 20})

    def test_mapping_changes_invalidate_receipts(self):
        path, receipt = self.receipt()
        path.write_text(json.dumps(receipt))
        mapping = criteria_map()
        mapping["criteria"][0]["review"] += " Changed policy"
        with patch("validate_draft.criteria_map", return_value=mapping):
            self.assertIsNotNone(self.report(path)["review_error"])

    def test_old_schema_rejected(self):
        path, receipt = self.receipt()
        for version in (1, True, "2"):
            with self.subTest(version=version):
                receipt["schema_version"] = version
                with self.assertRaises(ValueError):
                    self.run_receipt(path, receipt)

    def test_review_digest_records_exact_receipt(self):
        path, receipt = self.receipt()
        result = self.run_receipt(path, receipt)
        self.assertEqual(result["review_receipt_sha256"], sha(path.read_bytes()))

    def test_template_has_no_approved_decisions(self):
        report = self.report()
        template = review_template(report)
        self.assertEqual(len(template["criteria"]), 20)
        self.assertEqual(len(template["sources"]), len(report["source_reviews"]))
        for group in ("decisions", "criteria", "sources"):
            self.assertTrue(all(d["status"] == "needs_review" and not d["evidence_ids"] for d in template[group]))

    def test_template_cli_is_readonly(self):
        before = {p: p.read_bytes() for p in self.fixture.root.rglob('*') if p.is_file()}
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/validate_draft.py"),
            str(self.fixture.path), "--references-only", "--review-template"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(read_json(result.stdout)["schema_version"], 2)
        self.assertEqual(before, {p: p.read_bytes() for p in self.fixture.root.rglob('*') if p.is_file()})

    def test_template_cannot_write_export(self):
        target = self.fixture.root / "no-output"
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/validate_draft.py"),
            str(self.fixture.path), "--references-only", "--review-template", "--output", str(target), "--execute"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(target.exists())

    def test_text_export_includes_criteria_and_source_review(self):
        target = self.fixture.root / "report"
        write_report(target, self.report(), True)
        text = (target / "report.txt").read_text()
        self.assertIn("TRUST-06 | needs_review", text)
        self.assertIn("QUALITY-02 | needs_review", text)
        self.assertIn("Source reviews", text)

    def manifest(self, expected, reviews=None):
        report = self.report(reviews)
        case = {"id": "case-1", "kind": "synthetic", "split": "holdout", "brand": "Fixture",
                "labeler": "Synthetic labeler", "labeler_kind": "ai", "labeler_model": "fixture-only",
                "labeled_at": "2026-10-08", "bundle": self.fixture.path.name,
                "bundle_sha256": sha(self.fixture.path.read_bytes()), "fingerprint": report["fingerprint"],
                "expected": expected}
        if reviews:
            case.update(reviews=reviews.name, reviews_sha256=sha(reviews.read_bytes()))
        path = self.fixture.root / "eval-v2.json"
        path.write_text(json.dumps({"schema_version": 1, "cases": [case]}))
        return path

    def test_evaluation_separates_automatic_and_review_metrics(self):
        result = evaluate(self.manifest({"HTML-001": "pass", "TRUST-02": "fail"}), references_only=True)
        self.assertEqual(result["automatic_metrics"]["counts"], {"true_negative": 1})
        self.assertEqual(result["review_agreement_metrics"]["counts"], {"unresolved": 1})
        self.assertEqual(result["resolved_fraction"], 0.5)
        self.assertIsNone(result["review_agreement_metrics"]["recall"])
        self.assertFalse(result["independence_verified"])
        self.assertEqual(result["calibration_status"], "not_established")

    def test_evaluation_records_ai_agreement_not_human_truth(self):
        path, receipt = self.receipt()
        self.run_receipt(path, receipt)
        result = evaluate(self.manifest({"TRUST-02": "pass"}, path), references_only=True)
        self.assertEqual(result["results"][0]["reviewer_kind"], "ai")
        self.assertEqual(result["groups"][0]["labeler_kind"], "ai")
        self.assertFalse(result["release_approved"])

    def test_evaluation_rejects_changed_review(self):
        path, receipt = self.receipt()
        self.run_receipt(path, receipt)
        manifest = self.manifest({"TRUST-02": "pass"}, path)
        path.write_text(path.read_text() + "\n")
        with self.assertRaises(ValueError):
            evaluate(manifest, references_only=True)

    def test_synthetic_walkthrough_never_claims_real_evaluation(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "examples/review_walkthrough.py")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["supported_contradiction"], "blocked")
        self.assertTrue(summary["old_receipt_rejected_after_correction"])
        self.assertEqual(summary["after_correction"], "review_required")
        self.assertFalse(summary["model_called"])
        self.assertFalse(summary["publication_approved"])


if __name__ == "__main__":
    unittest.main()
