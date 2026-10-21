"""Applicability-aware comparisons, not content decisions or release gates."""
from collections import Counter

from validate_draft import nonempty

STATUSES = ("pass", "fail", "not_applicable", "needs_review", "not_tested")
PENDING = ("needs_review", "not_tested")
OUTCOMES = ("true_positive", "false_positive", "false_negative", "true_negative",
            "correct_exception", "incorrect_exception", "incorrect_inclusion",
            "correct_uncertainty", "uncertainty_mismatch", "unsupported_certainty", "unresolved")


def validate_label(label, finding, evidence_ids):
    if not isinstance(label, dict) or set(label) != {"applicability", "status", "reason", "evidence_ids"}:
        raise ValueError("V2 labels require applicability, status, reason and evidence_ids")
    scope, status = label["applicability"], label["status"]
    allowed = {"applicable": ("pass", "fail", "needs_review", "not_tested"),
               "not_applicable": ("not_applicable",), "unknown": ("needs_review",)}
    if not isinstance(scope, str) or scope not in allowed or status not in allowed[scope]:
        raise ValueError("Inconsistent expected applicability and status")
    if status == "not_tested" and finding["method"] not in ("rendered", "live"):
        raise ValueError("not_tested labels require a rendered or live check")
    if not nonempty(label["reason"]):
        raise ValueError("V2 labels require an evidence-scoped reason")
    refs = label["evidence_ids"]
    if (not isinstance(refs, list) or any(not nonempty(r) for r in refs)
            or len(refs) != len(set(refs)) or not set(refs) <= evidence_ids
            or (status not in PENDING and not refs)):
        raise ValueError("Resolved V2 labels require distinct known evidence IDs")


def compare(label, finding):
    status = finding["status"]
    if status not in STATUSES:
        raise ValueError("Unknown observed status")
    # Receipts do not carry a separate scope verdict. Keep the proxy and its limits explicit.
    observed_scope = ("unknown" if status == "needs_review" else
                      "not_applicable" if status == "not_applicable" else "applicable")
    scope = label["applicability"]
    scope_outcome = (("correct_uncertainty" if observed_scope == "unknown" else "unsupported_certainty")
                     if scope == "unknown" else
                     "unresolved" if observed_scope == "unknown" else
                     "correct" if scope == observed_scope else "incorrect")
    expected = label["status"]
    if expected in ("pass", "fail"):
        outcome = ({("fail", "fail"): "true_positive", ("pass", "fail"): "false_positive",
                    ("fail", "pass"): "false_negative", ("pass", "pass"): "true_negative"}[(expected, status)]
                   if status in ("pass", "fail") else
                   "incorrect_exception" if status == "not_applicable" else "unresolved")
    elif expected == "not_applicable":
        outcome = ("correct_exception" if status == expected else
                   "unresolved" if status in PENDING else "incorrect_inclusion")
    else:
        outcome = ("correct_uncertainty" if status == expected else
                   "uncertainty_mismatch" if status in PENDING else "unsupported_certainty")
    return {"expected": expected, "expected_applicability": scope,
            "label_reason": label["reason"], "label_evidence_ids": label["evidence_ids"],
            "observed": status, "observed_applicability": observed_scope,
            "applicability_outcome": scope_outcome, "outcome": outcome}


def rate(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def summarize_v2(rows):
    counts = Counter(r["outcome"] for r in rows)
    scope_counts = Counter(r["applicability_outcome"] for r in rows)
    known_scope = [r for r in rows if r["expected_applicability"] != "unknown"]
    unknown_scope = [r for r in rows if r["expected_applicability"] == "unknown"]
    determinate = [r for r in rows if r["expected"] in ("pass", "fail")]
    positive = [r for r in determinate if r["expected"] == "fail"]
    negative = [r for r in determinate if r["expected"] == "pass"]
    pending = [r for r in rows if r["expected"] in PENDING]
    excluded = [r for r in rows if r["expected"] == "not_applicable"]
    critical = [r for r in positive if r["severity"] == "critical"]
    tp, fp, fn = (counts[k] for k in ("true_positive", "false_positive", "false_negative"))
    false_blocks = sum(r["observed"] == "fail" and r["failure_blocks"] for r in negative)
    return {
        "label_count": len(rows), "case_count": len({r["case_id"] for r in rows}),
        "counts": {k: counts[k] for k in OUTCOMES},
        "status_confusion": {expected: dict(Counter(r["observed"] for r in rows if r["expected"] == expected))
                             for expected in STATUSES},
        "applicability": {
            "counts": {k: scope_counts[k] for k in ("correct", "incorrect", "unresolved", "correct_uncertainty", "unsupported_certainty")},
            "agreement": rate(scope_counts["correct"], len(known_scope)),
            "resolution": rate(sum(r["observed_applicability"] != "unknown" for r in known_scope), len(known_scope)),
            "unknown_label_count": len(unknown_scope),
            "correct_abstention": rate(scope_counts["correct_uncertainty"], len(unknown_scope)),
        },
        "defects": {
            "gold_applicable_determinate_count": len(determinate),
            "resolution": rate(sum(r["observed"] in ("pass", "fail") for r in determinate), len(determinate)),
            "precision_resolved_only": rate(tp, tp + fp),
            "recall_resolved_only": rate(tp, tp + fn),
            "detection_all_gold_failures": rate(tp, len(positive)),
            "false_passes": rate(fn, len(positive)),
            "false_defects": rate(fp, len(negative)),
            "false_blocks": rate(false_blocks, len(negative)),
            "false_blocks_are_check_level_not_whole_page": True,
            "incorrect_exceptions_on_failures": rate(sum(r["observed"] == "not_applicable" for r in positive), len(positive)),
            "unresolved_failures": rate(sum(r["observed"] in PENDING for r in positive), len(positive)),
            "critical_false_passes": rate(sum(r["observed"] == "pass" for r in critical), len(critical)),
            "critical_incorrect_exceptions": rate(sum(r["observed"] == "not_applicable" for r in critical), len(critical)),
            "critical_unresolved": rate(sum(r["observed"] in PENDING for r in critical), len(critical)),
        },
        "exceptions": {
            "gold_count": len(excluded),
            "correct": counts["correct_exception"],
            "incorrect_inclusions": counts["incorrect_inclusion"],
            "false_blocks_on_excluded": rate(sum(r["observed"] == "fail" and r["failure_blocks"] for r in excluded), len(excluded)),
            "incorrect_exclusions": sum(r["expected_applicability"] == "applicable" and r["observed"] == "not_applicable" for r in rows),
        },
        "uncertainty": {
            "gold_pending_count": len(pending),
            "correct_status": rate(counts["correct_uncertainty"], len(pending)),
            "wrong_pending_status": counts["uncertainty_mismatch"],
            "unsupported_certainty": counts["unsupported_certainty"],
            "observed_pending_count": sum(r["observed"] in PENDING for r in rows),
        },
    }


def build_report(rows, cases, warnings, content_count, manifest_hash, matrix, engine_hash):
    summary = summarize_v2(rows)
    errors = {"false_positive", "false_negative", "incorrect_exception", "incorrect_inclusion",
              "uncertainty_mismatch", "unsupported_certainty", "unresolved"}
    mismatch = any(r["outcome"] in errors or r["applicability_outcome"] in
                   ("incorrect", "unresolved", "unsupported_certainty") for r in rows)
    group_fields = ("kind", "split", "page_type", "method", "labeler_kind")
    groups = []
    for key in sorted({tuple(r[k] for k in group_fields) for r in rows}):
        selected = [r for r in rows if tuple(r[k] for k in group_fields) == key]
        groups.append(dict(zip(group_fields, key)) | summarize_v2(selected))
    by_check = []
    for identifier, page_type in sorted({(r["rule_id"], r["page_type"]) for r in rows}):
        selected = [r for r in rows if (r["rule_id"], r["page_type"]) == (identifier, page_type)]
        by_check.append({k: selected[0][k] for k in ("rule_id", "check_kind", "page_type", "method", "severity", "basis_class")}
                        | summarize_v2(selected))
    return {
        "schema_version": 3, "manifest_schema_version": 2, "manifest_sha256": manifest_hash,
        "evaluation_engine_sha256": engine_hash,
        "applicability_matrix": {k: matrix[k] for k in ("schema_version", "matrix_version", "matrix_sha256", "catalog_version", "mapping_version")},
        **summary, "comparison_status": "mismatch_or_unresolved" if mismatch else "matched_supplied_labels",
        "results": rows, "groups": groups, "by_check": by_check,
        "by_page_type": {p: summarize_v2([r for r in rows if r["page_type"] == p]) for p in ("article", "landing")},
        "automatic_metrics": summarize_v2([r for r in rows if r["method"] == "auto"]),
        "review_agreement_metrics": summarize_v2([r for r in rows if r["method"] != "auto"]),
        "case_reports": cases,
        "dataset_summary": {
            "counts": {field: dict(Counter(c[field] for c in cases)) for field in ("kind", "split", "brand", "page_type", "stage")},
            "unique_draft_count": content_count,
            "source_family_count": len({c["source_family_id"] for c in cases}),
            "family_case_counts": dict(Counter(c["source_family_id"] for c in cases)),
            "warnings": warnings, "leakage_check": "exact_draft_bytes_and_declared_source_family",
            "semantic_leakage_checked": False, "source_family_identity_verified": False,
        },
        "applicability_observation": "Status proxy only: pass/fail/not_tested imply applicable, not_applicable implies excluded, needs_review leaves scope unknown. Receipts do not separately attest applicability.",
        "independence_verified": False, "calibration_status": "not_established",
        "release_approved": False, "publication_approved": False,
        "limits": ["Labels, source families and identities are supplied attestations, not authenticated facts.",
                   "Counts are check-level observations, not independent pages; related variants and criteria are correlated.",
                   "Resolved-only precision/recall omit abstentions; inspect all-gold failure detection, resolution and incorrect exceptions.",
                   "No semantic leakage detection, confidence intervals, reliability score or automatic release threshold.",
                   "Matching expected uncertainty is not a content pass or publication permission. Real corpus and reviewers remain operator-owned."],
    }
