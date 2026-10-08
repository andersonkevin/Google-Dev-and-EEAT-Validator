"""Synthetic acceptance and safety tests; never mutate project content."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from rule_catalog import catalog
from validate_draft import Page, automatic, coverage, read_json, sha, validate, write_report, usable_url, valid_date
from evaluate_validator import evaluate


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.snapshot = self.root / "snapshot"
        (self.snapshot / "knowledge").mkdir(parents=True)
        (self.snapshot / "source.txt").write_text("Synthetic source")
        raw_hash = sha(b"Synthetic source")
        (self.snapshot / "manifest.json").write_text("{}")
        chunks = [{"id": "chunk-" + str(i), "citation": r["source"], "source_file": "source.txt", "source_sha256": raw_hash}
                  for i, r in enumerate(catalog())]
        data = "".join(json.dumps(c) + "\n" for c in chunks).encode()
        (self.snapshot / "knowledge/chunks.jsonl").write_bytes(data)
        (self.snapshot / "knowledge/audit.json").write_text(json.dumps({"manifest_sha256": sha(b"{}"), "chunks_sha256": sha(data), "complete_within_scope": False, "source_exceptions": []}))
        self.bundle = {"schema_version": 1, "stage": "draft", "page_type": "article", "content": "draft.html",
            "brief": {"audience": "Operators", "market": "US", "purpose": "Explain exports", "intent": "Informational",
                      "next_action": "Read related documentation", "responsible_party": "Example publisher",
                      "ymyl": False, "updated": False, "video_search_claim": False,
                      "canonical_url": "https://example.test/guide", "indexing": "noindex"},
            "claims": [{"id": "c1", "quote": "Exports preserve records.", "evidence_ids": ["e1"]}],
            "evidence": [{"id": "e1", "file": "evidence.txt", "title": "Export test", "origin": "Internal test", "captured_at": "2026-10-08"}]}
        (self.root / "evidence.txt").write_text("Synthetic test evidence; no real publication approval.")
        self.html = '<html lang="en"><head><title>Export guide</title><meta name="description" content="How exports work"><link rel="canonical" href="https://example.test/guide"><meta name="robots" content="noindex"></head><body><h1>Export guide</h1><p>Exports preserve records.</p></body></html>'
        self.path = self.root / "bundle.json"
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.bundle))
        (self.root / "draft.html").write_text(self.html)

    def report(self, review=None):
        return validate(self.path, self.snapshot, review)

    def statuses(self, report):
        return {r["rule_id"]: r["status"] for r in report["findings"]}

    def reviews(self, changes=None):
        report = self.report()
        decisions = [{"rule_id": f["rule_id"], "status": "pass", "reviewer": "Synthetic owner",
                      "reason": "Fixture adjudication", "reviewed_at": "2026-10-08", "evidence_ids": ["e1"]}
                     for f in report["findings"] if f["status"] == "needs_review"]
        for d in decisions:
            if changes and d["rule_id"] in changes:
                d.update(changes[d["rule_id"]])
        path = self.root / "reviews.json"
        path.write_text(json.dumps({"fingerprint": report["fingerprint"], "decisions": decisions}))
        return path

    def test_clean_draft_requires_human_review(self):
        report = self.report()
        self.assertEqual(report["readiness"], "review_required")
        self.assertEqual(self.statuses(report)["ACCESS-001"], "not_applicable")

    def test_manual_failure_survives_absent_feature(self):
        review = self.reviews()
        receipt = json.loads(review.read_text())
        receipt["decisions"].append({"rule_id": "MEDIA-003", "status": "fail",
            "reviewer": "Synthetic reviewer", "reason": "Feature declaration conflicts with evidence",
            "reviewed_at": "2026-10-08", "evidence_ids": ["e1"]})
        review.write_text(json.dumps(receipt))
        result = self.report(review)
        self.assertEqual(self.statuses(result)["MEDIA-003"], "fail")
        self.assertEqual(result["readiness"], "blocked")

    def test_http_url_requires_host(self):
        self.assertTrue(automatic("ANCHOR-001", self.bundle, Page('<a href="https://">Open</a>')))

    def test_hidden_descendant_does_not_name_link(self):
        self.assertTrue(automatic("ANCHOR-003", self.bundle,
            Page('<a href="/x"><span aria-hidden="true">Hidden</span></a>')))

    def test_hidden_heading_does_not_supply_main_title(self):
        self.assertTrue(automatic("HTML-001", self.bundle, Page('<h1 hidden>Hidden</h1>')))

    def test_ymyl_false_still_requires_scope_review(self):
        self.assertEqual(self.statuses(self.report())["RATER-003"], "needs_review")

    def test_ymyl_failure_blocks_despite_false_declaration(self):
        review = self.reviews({"RATER-003": {"status": "fail", "reason": "Specialist advice needs review"}})
        self.assertEqual(self.report(review)["readiness"], "blocked")

    def test_empty_boolean_attributes_do_not_crash(self):
        page = Page('<a href aria-label><img alt></a><h1 hidden>Title</h1>')
        self.assertTrue(automatic("ANCHOR-001", self.bundle, page))
        self.assertTrue(automatic("ANCHOR-003", self.bundle, page))

    def test_observation_paths_cannot_escape_bundle(self):
        self.bundle["observations"] = ["../outside.json"]
        self.save()
        with self.assertRaises(ValueError):
            self.report()

    def test_hidden_heading_ancestor_and_descendant(self):
        for html in ('<div hidden><h1>Title</h1></div>', '<h1><span hidden>Title</span></h1>'):
            with self.subTest(html=html):
                self.assertTrue(automatic("HTML-001", self.bundle, Page(html)))

    def test_hidden_referenced_label_is_allowed(self):
        html = '<span id="label" hidden>Read guide</span><a href="/guide" aria-labelledby="label"></a>'
        self.assertFalse(automatic("ANCHOR-003", self.bundle, Page(html)))

    def test_visible_reference_excludes_hidden_children(self):
        html = '<span id="label"><span hidden>Hidden</span></span><a href="/x" aria-labelledby="label"></a>'
        self.assertTrue(automatic("ANCHOR-003", self.bundle, Page(html)))

    def test_hidden_image_does_not_name_link(self):
        self.assertTrue(automatic("ANCHOR-003", self.bundle, Page('<a href="/x"><img hidden alt="Read"></a>')))

    def test_label_cycles_terminate(self):
        html = '<a id="a" href="/x" aria-labelledby="b"></a><span id="b" aria-labelledby="a"></span>'
        self.assertTrue(automatic("ANCHOR-003", self.bundle, Page(html)))

    def test_aria_label_and_title_fallback(self):
        for attrs in ('aria-label="Read"', 'title="Read"'):
            self.assertFalse(automatic("ANCHOR-003", self.bundle, Page('<a href="/x" ' + attrs + '></a>')))

    def test_url_syntax_boundaries(self):
        for value in ('https://', '//', 'https://[broken', 'https://example.test:99999', 'mailto:', 'tel:', 'javascript:go()', 'https://exa mple.test', 'https://ex\nample.test'):
            with self.subTest(value=value):
                self.assertFalse(usable_url(value))
        for value in ('https://example.test/a', '/guide', '../guide', '#section', 'mailto:a@example.test', 'tel:+123', '//example.test/a'):
            with self.subTest(value=value):
                self.assertTrue(usable_url(value))

    def test_invalid_canonical_rejected_even_if_matches(self):
        self.bundle["brief"]["canonical_url"] = "https://"
        self.assertTrue(automatic("META-003", self.bundle, Page('<link rel="canonical" href="https://">')))

    def test_date_syntax_is_not_presence_only(self):
        for value in ('yesterday', '2026-02-30', '2026-10-08T12:00:00', True):
            self.assertFalse(valid_date(value))
        for value in ('2026-10-08', '2026-10-08T12:00:00Z', '2026-10-08T12:00:00+02:00'):
            self.assertTrue(valid_date(value))

    def test_invalid_evidence_date_fails(self):
        self.bundle["evidence"][0]["captured_at"] = "recently"
        self.save()
        self.assertEqual(self.statuses(self.report())["EVIDENCE-001"], "fail")

    def test_invalid_review_date_rejected(self):
        with self.assertRaises(ValueError):
            self.report(self.reviews({"TRUST-001": {"reviewed_at": "yesterday"}}))

    def test_boolean_schema_version_rejected(self):
        self.bundle["schema_version"] = True
        self.save()
        with self.assertRaises(ValueError):
            self.report()

    def test_profiles_have_distinct_editorial_requirements(self):
        article = next(f for f in self.report()["findings"] if f["rule_id"] == "TRUST-001")
        self.bundle["page_type"] = "landing"
        self.save()
        landing = next(f for f in self.report()["findings"] if f["rule_id"] == "TRUST-001")
        self.assertNotEqual(article["profile_prompt"], landing["profile_prompt"])

    def test_rule_contract_fields(self):
        fields = {"id", "version", "family", "source", "source_class", "applies", "method", "severity", "pass_condition", "fail_condition", "exceptions", "remediation", "reviewer_role"}
        for rule in catalog():
            self.assertTrue(fields <= rule.keys(), rule["id"])

    def observation(self, status="pass", rid="ACCESS-001"):
        self.bundle["stage"] = "live"
        self.save()
        report = self.report()
        receipt = {"schema_version": 1, "content_sha256": report["content_sha256"],
            "context_sha256": report["context_sha256"], "url": self.bundle["brief"]["canonical_url"],
            "reviewer": "Synthetic operator", "captured_at": "2026-10-08",
            "checks": [{"rule_id": rid, "status": status, "reason": "Synthetic HTTP observation",
                        "evidence_sha256": {"e1": sha((self.root / "evidence.txt").read_bytes())}}]}
        path = self.root / "observation.json"
        path.write_text(json.dumps(receipt))
        self.bundle["observations"] = [path.name]
        self.save()
        return path

    def test_imported_live_observation_is_rule_specific(self):
        self.observation()
        statuses = self.statuses(self.report())
        self.assertEqual(statuses["ACCESS-001"], "pass")
        self.assertEqual(statuses["ACCESS-002"], "not_tested")

    def test_stale_observation_content_rejected(self):
        self.observation()
        self.html += "<p>Changed</p>"
        self.save()
        with self.assertRaises(ValueError):
            self.report()

    def test_stale_observation_context_rejected(self):
        self.observation()
        self.bundle["brief"]["indexing"] = "index"
        self.save()
        with self.assertRaises(ValueError):
            self.report()

    def test_observation_wrong_url_or_hash_rejected(self):
        path = self.observation()
        original = json.loads(path.read_text())
        for key, value in (("url", "https://elsewhere.test"), ("content_sha256", "0" * 64)):
            path.write_text(json.dumps(original | {key: value}))
            with self.assertRaises(ValueError):
                self.report()

    def test_observation_does_not_override_human_failure(self):
        self.observation(rid="A11Y-001")
        review = self.reviews()
        receipt = json.loads(review.read_text())
        receipt["decisions"].append({"rule_id": "A11Y-001", "status": "fail", "reviewer": "Synthetic reviewer",
            "reason": "Keyboard defect", "reviewed_at": "2026-10-08", "evidence_ids": ["e1"]})
        review.write_text(json.dumps(receipt))
        self.assertEqual(self.statuses(self.report(review))["A11Y-001"], "fail")

    def test_observation_failure_cannot_be_waived(self):
        self.observation(status="fail", rid="A11Y-001")
        review = self.reviews()
        receipt = json.loads(review.read_text())
        receipt["decisions"].append({"rule_id": "A11Y-001", "status": "pass", "reviewer": "Synthetic reviewer",
            "reason": "Attempted waiver", "reviewed_at": "2026-10-08", "evidence_ids": ["e1"]})
        review.write_text(json.dumps(receipt))
        self.assertEqual(self.statuses(self.report(review))["A11Y-001"], "fail")

    def test_observation_cannot_supply_automatic_pass(self):
        self.observation(rid="HTML-001")
        with self.assertRaises(ValueError):
            self.report()

    def test_observation_evidence_change_rejected(self):
        self.observation()
        (self.root / "evidence.txt").write_text("Changed record")
        with self.assertRaises(ValueError):
            self.report()

    def test_export_completion_receipt_hashes_outputs(self):
        target = self.root / "export"
        write_report(target, self.report(), True)
        receipt = json.loads((target / "COMPLETE.json").read_text())
        for name, digest in receipt["files"].items():
            self.assertEqual(sha((target / name).read_bytes()), digest)

    def test_interrupted_export_has_no_completion_receipt(self):
        target = self.root / "export"
        original = Path.write_text
        def interrupted(path, *args, **kwargs):
            if path.name == "report.txt":
                raise OSError("Simulated interrupted export")
            return original(path, *args, **kwargs)
        with patch.object(Path, "write_text", interrupted):
            with self.assertRaises(OSError):
                write_report(target, self.report(), True)
        self.assertFalse((target / "COMPLETE.json").exists())

    def triage(self):
        report = coverage(self.snapshot)
        receipt = {"chunks_sha256": report["chunks_sha256"], "decisions": [{
            "chunk_id": report["rows"][0]["chunk_id"], "disposition": "context",
            "reviewer": "Synthetic reviewer", "reviewed_at": "2026-10-08", "reason": "Fixture context"}]}
        path = self.root / "triage.json"
        path.write_text(json.dumps(receipt))
        return path

    def test_triage_preserves_unreviewed_and_exceptions(self):
        report = coverage(self.snapshot, self.triage())
        self.assertEqual(report["adjudicated_chunks"], 1)
        self.assertEqual(report["unresolved_chunks"], report["chunks"] - 1)
        self.assertFalse(report["complete"])

    def test_triage_rejects_stale_index(self):
        path = self.triage()
        receipt = json.loads(path.read_text())
        receipt["chunks_sha256"] = "0" * 64
        path.write_text(json.dumps(receipt))
        with self.assertRaises(ValueError):
            coverage(self.snapshot, path)

    def test_triage_rejects_duplicate_and_unproven_decisions(self):
        path = self.triage()
        original = json.loads(path.read_text())
        for changes in ({"reviewer": ""}, {"disposition": "active_evidence"}, {"disposition": "duplicate"}, {"chunk_id": "unknown"}):
            receipt = original | {"decisions": [original["decisions"][0] | changes]}
            path.write_text(json.dumps(receipt))
            with self.assertRaises(ValueError):
                coverage(self.snapshot, path)
        original["decisions"] *= 2
        path.write_text(json.dumps(original))
        with self.assertRaises(ValueError):
            coverage(self.snapshot, path)

    def evaluation(self, expected=None):
        manifest = {"schema_version": 1, "cases": [{"id": "fixture", "kind": "synthetic",
            "split": "development", "brand": "synthetic", "labeler": "Test designer",
            "labeled_at": "2026-10-08", "bundle": self.path.name,
            "bundle_sha256": sha(self.path.read_bytes()), "fingerprint": self.report()["fingerprint"],
            "expected": expected or {"HTML-001": "pass"}}]}
        path = self.root / "evaluation.json"
        path.write_text(json.dumps(manifest))
        return path

    def test_evaluation_uses_expected_labels_not_model_output(self):
        result = evaluate(self.evaluation({"HTML-001": "fail"}), self.snapshot)
        self.assertEqual(result["counts"]["false_negative"], 1)
        self.assertEqual(result["recall"], 0)
        self.assertFalse(result["release_approved"])

    def test_evaluation_unresolved_not_counted_as_pass(self):
        result = evaluate(self.evaluation({"TRUST-001": "pass"}), self.snapshot)
        self.assertEqual(result["counts"]["unresolved"], 1)
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["recall"])

    def test_evaluation_rejects_changed_case(self):
        path = self.evaluation()
        self.html += "<p>Different case</p>"
        self.save()
        with self.assertRaises(ValueError):
            evaluate(path, self.snapshot)

    def test_evaluation_rejects_changed_bundle(self):
        path = self.evaluation()
        self.bundle["brief"]["purpose"] = "Different purpose"
        self.save()
        with self.assertRaises(ValueError):
            evaluate(path, self.snapshot)

    def test_evaluation_rejects_missing_labeler(self):
        path = self.evaluation()
        manifest = json.loads(path.read_text())
        del manifest["cases"][0]["labeler"]
        path.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            evaluate(path, self.snapshot)

    def test_evaluation_preserves_cases_readonly(self):
        path = self.evaluation()
        before = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = evaluate(path, self.snapshot)
        after = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result["counts"]["true_negative"], 1)

    def test_recorded_reviews_make_ready_only_for_owner(self):
        self.assertEqual(self.report(self.reviews())["readiness"], "ready_for_owner_review")

    def test_fabricated_author_adjudication_blocks(self):
        review = self.reviews({"TRUST-001": {"status": "fail", "reason": "Credentials contradicted by supplied record"}})
        self.assertEqual(self.report(review)["readiness"], "blocked")

    def test_contradictory_source_blocks_even_with_valid_schema(self):
        self.html += '<script type="application/ld+json">{"@type":"Article"}</script>'
        self.save()
        review = self.reviews({"CLAIM-002": {"status": "fail", "reason": "Source contradicts claim"}})
        result = self.report(review)
        self.assertEqual(self.statuses(result)["JSONLD-001"], "pass")
        self.assertEqual(result["readiness"], "blocked")

    def test_changed_content_invalidates_reviews(self):
        review = self.reviews()
        self.html += "<p>New material.</p>"
        self.save()
        self.assertIsNotNone(self.report(review)["review_error"])

    def test_changed_evidence_invalidates_reviews(self):
        review = self.reviews()
        (self.root / "evidence.txt").write_text("Changed evidence")
        self.assertIsNotNone(self.report(review)["review_error"])

    def test_human_cannot_override_automatic_failure(self):
        review = self.reviews()
        receipt = json.loads(review.read_text())
        receipt["decisions"].append({"rule_id": "HTML-001", "status": "pass"})
        review.write_text(json.dumps(receipt))
        with self.assertRaises(ValueError):
            self.report(review)

    def test_review_requires_reason_reviewer_and_evidence(self):
        for field in ("reason", "reviewer", "reviewed_at", "evidence_ids"):
            with self.subTest(field=field):
                review = self.reviews({"TRUST-001": {field: ""}})
                with self.assertRaises(ValueError):
                    self.report(review)

    def test_short_landing_no_wordcount_penalty(self):
        self.bundle["page_type"] = "landing"
        self.save()
        self.assertEqual(self.report(self.reviews())["readiness"], "ready_for_owner_review")

    def test_staging_noindex_does_not_fail_indexability(self):
        self.bundle["stage"] = "staging"
        self.save()
        report = self.report()
        self.assertEqual(self.statuses(report)["ROBOTS-001"], "pass")
        self.assertEqual(self.statuses(report)["ACCESS-002"], "not_applicable")

    def test_live_cannot_be_certified_by_static_html(self):
        self.bundle["stage"] = "live"
        self.save()
        report = self.report(self.reviews())
        self.assertEqual(self.statuses(report)["ACCESS-001"], "not_tested")
        self.assertEqual(report["readiness"], "review_required")

    def test_missing_claim_reference_blocks(self):
        self.bundle["claims"][0]["evidence_ids"] = ["missing"]
        self.save()
        self.assertEqual(self.statuses(self.report())["CLAIM-001"], "fail")

    def test_empty_ledger_does_not_prove_no_claims(self):
        self.bundle["claims"] = []
        self.save()
        self.assertEqual(self.statuses(self.report())["CLAIM-003"], "needs_review")

    def test_microdata_requires_semantic_review_not_jsonld_pass(self):
        self.html += '<div itemscope itemtype="https://schema.org/Article">Article</div>'
        self.save()
        statuses = self.statuses(self.report())
        self.assertEqual(statuses["SCHEMA-001"], "needs_review")
        self.assertEqual(statuses["JSONLD-001"], "not_applicable")

    def test_malformed_review_receipt_rejected(self):
        path = self.root / "reviews.json"
        path.write_text("[]")
        with self.assertRaises(ValueError):
            self.report(path)

    def test_duplicate_claim_ids_rejected(self):
        self.bundle["claims"].append(dict(self.bundle["claims"][0]))
        self.save()
        with self.assertRaises(ValueError):
            self.report()

    def test_auto_checks_not_applicable_without_optional_features(self):
        statuses = self.statuses(self.report())
        for rid in ("IMAGE-001", "ANCHOR-001", "ANCHOR-002", "ANCHOR-003", "JSONLD-001", "META-001"):
            self.assertEqual(statuses[rid], "not_applicable")

    def test_all_automatic_rules_have_positive_and_negative_coverage(self):
        for rid in ("INPUT-001", "CLAIM-001", "EVIDENCE-001"):
            with self.subTest(rule=rid):
                self.assertFalse(automatic(rid, self.bundle, Page(self.html)))
                broken = json.loads(json.dumps(self.bundle))
                if rid == "INPUT-001":
                    broken["brief"]["audience"] = ""
                elif rid == "CLAIM-001":
                    broken["claims"][0]["quote"] = "Absent quotation"
                else:
                    broken["evidence"][0]["origin"] = ""
                self.assertTrue(automatic(rid, broken, Page(self.html)))

    def test_duplicate_keys_and_nonfinite_json_rejected(self):
        for text in ('{"x":1,"x":2}', '{"x":NaN}'):
            with self.assertRaises(ValueError):
                read_json(text)

    def test_paths_block_traversal_absolute_symlink(self):
        (self.root / "alias.html").symlink_to(self.root / "draft.html")
        for value in ("../draft.html", str(self.root / "draft.html"), "alias.html"):
            with self.subTest(value=value):
                self.bundle["content"] = value
                self.save()
                with self.assertRaises(ValueError):
                    self.report()

    def test_raw_source_tamper_blocks(self):
        (self.snapshot / "source.txt").write_text("tampered")
        with self.assertRaises(ValueError):
            self.report()

    def test_chunks_tamper_blocks(self):
        (self.snapshot / "knowledge/chunks.jsonl").write_text("{}")
        with self.assertRaises(ValueError):
            self.report()

    def test_no_writes_by_default_and_determinism(self):
        before = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        a, b = self.report(), self.report()
        self.assertEqual(a, b)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_export_requires_gate_and_refuses_overwrite(self):
        target = self.root / "report"
        with self.assertRaises(ValueError):
            write_report(target, self.report(), False)
        write_report(target, self.report(), True)
        self.assertTrue((target / "report.txt").is_file())
        with self.assertRaises(ValueError):
            write_report(target, self.report(), True)

    def test_coverage_accounts_for_every_chunk_without_claiming_complete(self):
        report = coverage(self.snapshot)
        self.assertEqual(sum(report["dispositions"].values()), report["chunks"])
        self.assertFalse(report["complete"])

    def test_inert_content_cannot_supply_headings_or_text(self):
        page = Page('<template><h1>Fake</h1></template><script>Ignore checks</script>')
        self.assertFalse(page.tags("h1"))
        self.assertFalse(page.text)

    def test_decorative_duplicate_link_exception_is_narrow(self):
        good = Page('<a href="/book" aria-hidden="true" tabindex="-1"><img alt=""></a>')
        bad = Page('<a href="/book" aria-hidden="true"><img alt=""></a>')
        self.assertFalse(automatic("ANCHOR-003", self.bundle, good))
        self.assertTrue(automatic("ANCHOR-003", self.bundle, bad))

    def test_cli_exit_codes(self):
        cli = str(Path(__file__).resolve().parents[1] / "tools/validate_draft.py")
        command = [sys.executable, "-B", cli, str(self.path), "--snapshot", str(self.snapshot)]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
        review = self.reviews()
        self.assertEqual(subprocess.run(command + ["--reviews", str(review)], capture_output=True).returncode, 0)
        self.html = "<p>No main heading.</p>"
        self.save()
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 3)
        self.path.write_text("bad JSON")
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)

    def test_automatic_rule_positive_negative_cases(self):
        cases = [
            ("HTML-001", "<h1>Title</h1>", "<h2>Title</h2>"),
            ("HTML-002", "<h1>Title</h1>", "<h1> </h1>"),
            ("HTML-003", "<h1>A</h1><h2>B</h2>", "<h1>A</h1><h3>B</h3>"),
            ("HTML-004", "<p>Copy</p>", "<script>Code</script>"),
            ("IMAGE-001", '<img alt="">', '<img src="x">'),
            ("ANCHOR-001", '<a href="/guide">Guide</a>', '<a href="javascript:alert(1)">Guide</a>'),
            ("ANCHOR-002", '<h2 id="a">A</h2><a href="#a">A</a>', '<a href="#missing">A</a>'),
            ("ANCHOR-003", '<a href="/guide"><img alt="Guide"></a>', '<a href="/guide"></a>'),
            ("JSONLD-001", '<script type="application/ld+json">{"@type":"Article"}</script>', '<script type="application/ld+json">[1]</script>'),
            ("META-001", '<title>Guide</title>', '<title></title>'),
            ("META-002", '<meta name="description" content="Guide">', '<meta name="description" content="">'),
            ("META-003", '<link rel="canonical" href="https://example.test/guide">', '<link rel="canonical" href="https://example.test/wrong">'),
            ("ROBOTS-001", '<meta name="robots" content="noindex">', '<meta name="robots" content="index">'),
            ("LANG-001", '<html lang="en">', '<html>'),
        ]
        for rid, good, bad in cases:
            with self.subTest(rule=rid):
                self.assertFalse(automatic(rid, self.bundle, Page(good)))
                self.assertTrue(automatic(rid, self.bundle, Page(bad)))


if __name__ == "__main__":
    unittest.main()
