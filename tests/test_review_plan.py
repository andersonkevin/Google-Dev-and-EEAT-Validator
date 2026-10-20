"""Synthetic interactive-state regressions and read-only review planning contracts."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from urllib.parse import urldefrag

import test_validator
from validate_draft import Page, automatic, review_plan

ROOT = Path(__file__).resolve().parents[1]


class HiddenLinkTests(unittest.TestCase):
    def failures(self, html, rule="ANCHOR-003"):
        return automatic(rule, {"brief": {}}, Page(html))

    def test_html_hidden_links_are_outside_initial_name_check(self):
        for html in ('<a hidden href="/guide">Read guide</a>',
                     '<section hidden><div><a href="/guide">Read guide</a></div></section>',
                     '<section hidden="until-found"><a href="/guide"></a></section>',
                     '<a hidden="false" href="/guide"></a>'):
            with self.subTest(html=html):
                self.assertEqual(self.failures(html), [])

    def test_visible_unnamed_link_is_not_hidden_by_previous_sibling(self):
        html = '<section hidden><a href="/one">One</a></section>\n<a href="/two"></a>'
        self.assertEqual(self.failures(html), ["line:2"])

    def test_activated_state_is_checked_again(self):
        hidden = '<section hidden><a href="/guide">{}</a></section>'
        self.assertEqual(self.failures(hidden.format("")), [])
        self.assertEqual(self.failures(hidden.replace(" hidden", "").format("")), ["line:1"])
        self.assertEqual(self.failures(hidden.replace(" hidden", "").format("Read guide")), [])

    def test_aria_hiding_does_not_excuse_focusable_links(self):
        for html in ('<a aria-hidden="true" href="/guide">Read guide</a>',
                     '<section aria-hidden="true"><a href="/guide">Read guide</a></section>',
                     '<a aria-hidden="true" tabindex="0" href="/guide">Read guide</a>'):
            with self.subTest(html=html):
                self.assertEqual(self.failures(html), ["line:1"])

    def test_explicit_decorative_duplicate_exception_is_preserved(self):
        self.assertEqual(self.failures('<a href="/guide" aria-hidden="true" tabindex="-1"></a>'), [])

    def test_hidden_descendants_do_not_name_visible_links(self):
        for attrs in ("hidden", 'aria-hidden="true"'):
            with self.subTest(attrs=attrs):
                self.assertEqual(self.failures(f'<a href="/guide"><span {attrs}>Read</span></a>'), ["line:1"])

    def test_hidden_referenced_label_can_name_visible_link(self):
        html = '<div hidden><span id="label">Read guide</span></div><a href="/guide" aria-labelledby="label"></a>'
        self.assertEqual(self.failures(html), [])

    def test_hidden_content_keeps_other_link_checks(self):
        self.assertTrue(self.failures('<a hidden href="javascript:go()">Read</a>', "ANCHOR-001"))
        self.assertTrue(self.failures('<a hidden href="#missing">Read</a>', "ANCHOR-002"))


class ReviewPlanTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_validator.ValidatorTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def run_cli(self, *options, snapshot=False):
        mode = ["--snapshot", str(self.fixture.snapshot)] if snapshot else ["--references-only"]
        return subprocess.run([sys.executable, "-B", str(ROOT / "tools/validate_draft.py"),
                               str(self.fixture.path), *mode, "--review-plan", *options],
                              capture_output=True, text=True)

    def file_hashes(self):
        return {p.relative_to(self.fixture.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.fixture.root.rglob("*") if p.is_file()}

    def test_plan_preserves_readiness_and_does_not_mutate_report(self):
        report = self.fixture.report()
        before = json.dumps(report, sort_keys=True)
        plan = review_plan(report)
        self.assertEqual(json.dumps(report, sort_keys=True), before)
        self.assertEqual(plan["kind"], "review_plan")
        self.assertEqual(plan["schema_version"], 1)
        self.assertEqual(plan["fingerprint"], report["fingerprint"])
        self.assertEqual(plan["readiness"], report["readiness"])
        self.assertFalse(plan["publication_approved"])
        self.assertEqual(len(plan["criterion_tasks"]), 20)
        self.assertTrue(all(c["evidence_needed"] and c["exception"] for c in plan["criterion_tasks"]))

    def test_sources_group_sections_without_waiving_inactive_sources(self):
        report = self.fixture.report()
        plan = review_plan(report)
        grouped = {s["source"]: s for s in plan["sources"]}
        self.assertEqual(len(grouped), len(plan["sources"]))
        self.assertEqual(set(grouped), {s["source"] for s in report["source_reviews"]})
        for finding in report["findings"]:
            source = grouped[urldefrag(finding["source"])[0]]
            self.assertIn(finding["source"], source["sections"])
            self.assertIn(finding["rule_id"], source["rule_ids"])
            if finding["status"] == "not_applicable":
                self.assertNotIn(finding["rule_id"], source["pending_rule_ids"])
                self.assertTrue(source["required"])
        for criterion in report["eeat_criteria"]:
            for ref in criterion["sources"]:
                self.assertIn(ref, grouped[urldefrag(ref)[0]]["sections"])
                self.assertIn(criterion["criterion_id"], grouped[urldefrag(ref)[0]]["pending_criterion_ids"])

    def test_failures_keep_location_and_remediation(self):
        self.fixture.html += '\n<a href="/guide"></a>'
        self.fixture.save()
        plan = review_plan(self.fixture.report())
        self.assertEqual(plan["readiness"], "blocked")
        finding = next(f for f in plan["mechanical_failures"] if f["rule_id"] == "ANCHOR-003")
        self.assertEqual(finding["locations"], ["line:2"])
        self.assertTrue(finding["remediation"])

    def test_hidden_link_exclusion_is_disclosed_in_report_and_plan(self):
        self.fixture.html += '<div hidden><a href="/one">One</a><a href="/two">Two</a></div>'
        self.fixture.save()
        report = self.fixture.report()
        finding = next(f for f in report["findings"] if f["rule_id"] == "ANCHOR-003")
        self.assertEqual(finding["status"], "pass")
        self.assertIn("Excluded 2 link(s)", finding["observed_evidence"])
        self.assertIn("activated states", review_plan(report)["static_scope_notes"][0]["note"])

    def test_current_reviews_leave_only_unresolved_criterion_tasks(self):
        path = self.fixture.reviews()
        receipt = json.loads(path.read_text())
        pending_id = receipt["criteria"][0]["criterion_id"]
        receipt["criteria"][0]["status"] = "needs_review"
        path.write_text(json.dumps(receipt))
        plan = review_plan(self.fixture.report(path))
        self.assertEqual(plan["review_tasks"], [])
        self.assertEqual([c["criterion_id"] for c in plan["criterion_tasks"]], [pending_id])
        self.assertEqual(plan["readiness"], "review_required")
        self.assertTrue(all(s["status"] == "pass" for s in plan["sources"]))

    def test_explicit_scope_conflict_is_kept_in_plan(self):
        path = self.fixture.reviews()
        receipt = json.loads(path.read_text())
        receipt["decisions"].append(receipt["decisions"][0] | {
            "rule_id": "MEDIA-003", "status": "fail", "reason": "Conflicting feature evidence"})
        path.write_text(json.dumps(receipt))
        plan = review_plan(self.fixture.report(path))
        task = next(t for t in plan["review_tasks"] if t["rule_id"] == "MEDIA-003")
        self.assertEqual(task["status"], "fail")
        self.assertTrue(task["scope_conflict"])
        self.assertEqual(plan["readiness"], "blocked")

    def test_stale_review_cannot_reduce_plan(self):
        path = self.fixture.reviews()
        self.fixture.html += "<p>Updated explanation.</p>"
        self.fixture.save()
        plan = review_plan(self.fixture.report(path))
        self.assertTrue(plan["review_error"])
        self.assertEqual(len(plan["criterion_tasks"]), 20)
        self.assertTrue(all(s["status"] == "needs_review" for s in plan["sources"]))
        self.assertEqual(plan["readiness"], "review_required")

    def test_source_failure_keeps_reason_and_blocks_plan(self):
        path = self.fixture.reviews()
        receipt = json.loads(path.read_text())
        receipt["sources"][0].update(status="fail", reason="The cited section conflicts with the rule.")
        path.write_text(json.dumps(receipt))
        plan = review_plan(self.fixture.report(path))
        source = next(s for s in plan["sources"] if s["status"] == "fail")
        self.assertEqual(source["decision"]["reason"], receipt["sources"][0]["reason"])
        self.assertEqual(source["decision"]["evidence_ids"], ["e1"])
        self.assertEqual(plan["readiness"], "blocked")

    def test_criterion_failure_keeps_reason_and_blocks_plan(self):
        path = self.fixture.reviews()
        receipt = json.loads(path.read_text())
        receipt["criteria"][0].update(status="fail", reason="The demonstration does not support the claim.")
        path.write_text(json.dumps(receipt))
        plan = review_plan(self.fixture.report(path))
        self.assertEqual(len(plan["criterion_tasks"]), 1)
        self.assertEqual(plan["criterion_tasks"][0]["decision"]["reason"], receipt["criteria"][0]["reason"])
        self.assertEqual(plan["readiness"], "blocked")

    def test_live_plan_preserves_missing_observation_tasks(self):
        self.fixture.bundle["stage"] = "live"
        self.fixture.save()
        plan = review_plan(self.fixture.report())
        task = next(t for t in plan["review_tasks"] if t["rule_id"] == "ACCESS-001")
        self.assertEqual(task["method"], "live")
        self.assertEqual(task["status"], "not_tested")

    def test_cli_is_deterministic_readonly_and_keeps_review_exit_code(self):
        before = self.file_hashes()
        result = self.run_cli()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["readiness"], "review_required")
        self.assertEqual(self.run_cli().stdout, result.stdout)
        self.assertEqual(self.file_hashes(), before)

    def test_cli_blocked_and_ready_exit_codes(self):
        self.fixture.html += '<a href="/guide"></a>'
        self.fixture.save()
        blocked = self.run_cli()
        self.assertEqual(blocked.returncode, 3, blocked.stderr)
        self.assertEqual(json.loads(blocked.stdout)["readiness"], "blocked")
        self.fixture.html = self.fixture.html.replace('<a href="/guide"></a>', '<a href="/guide">Guide</a>')
        self.fixture.save()
        ready = self.run_cli("--reviews", str(self.fixture.reviews()), snapshot=True)
        self.assertEqual(ready.returncode, 0, ready.stderr)
        plan = json.loads(ready.stdout)
        self.assertEqual(plan["readiness"], "ready_for_owner_review")
        self.assertFalse(plan["publication_approved"])

    def test_cli_rejects_export_template_and_coverage_combinations_without_writes(self):
        target = self.fixture.root / "must-not-exist"
        before = self.file_hashes()
        for flags in (("--output", str(target)), ("--output", str(target), "--execute"),
                      ("--execute",), ("--review-template",), ("--coverage",)):
            with self.subTest(flags=flags):
                result = self.run_cli(*flags, snapshot=True)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(json.loads(result.stderr)["readiness"], "invalid_input")
                self.assertFalse(target.exists())
        self.assertEqual(self.file_hashes(), before)

    def test_cli_reuses_bundle_path_safety(self):
        self.fixture.bundle["content"] = "../outside.html"
        self.fixture.save()
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stderr)["readiness"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
