"""Evaluate frozen, independently supplied labels without modifying cases or approvals."""
import argparse
from collections import Counter
from pathlib import Path
import sys

from validate_draft import canonical, nonempty, read_input, read_json, sha, valid_date, validate


def summarize(rows):
    metrics = Counter(row["outcome"] for row in rows)
    tp, fp, fn = (metrics[k] for k in ("true_positive", "false_positive", "false_negative"))
    return {"counts": dict(metrics), "label_count": len(rows),
            "resolved_fraction": (len(rows) - metrics["unresolved"]) / len(rows) if rows else None,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None}


def evaluate(manifest_path, snapshot=None, references_only=False):
    root = manifest_path.parent.resolve()
    raw = read_input(root, manifest_path.name)
    manifest = read_json(raw)
    if not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise ValueError("Expected evaluation schema_version 1")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Evaluation requires pre-labeled cases")
    rows, seen = [], set()
    for case in cases:
        if not isinstance(case, dict) or not nonempty(case.get("id")) or case["id"] in seen:
            raise ValueError("Invalid or duplicate evaluation case")
        seen.add(case["id"])
        if case.get("kind") not in ("synthetic", "real") or case.get("split") not in ("development", "holdout"):
            raise ValueError("Case requires kind and fixed split")
        if not nonempty(case.get("labeler")) or not valid_date(case.get("labeled_at")) or not nonempty(case.get("brand")):
            raise ValueError("Case requires label provenance and brand")
        labeler_kind = case.get("labeler_kind", "unspecified")
        if labeler_kind not in ("ai", "human", "unspecified"):
            raise ValueError("Unknown labeler kind")
        if labeler_kind == "ai" and not nonempty(case.get("labeler_model")):
            raise ValueError("AI labels require model provenance")
        expected = case.get("expected")
        if not isinstance(expected, dict) or not expected or any(v not in ("pass", "fail") for v in expected.values()):
            raise ValueError("Expected findings must be independently labeled pass/fail")
        bundle_raw = read_input(root, case.get("bundle"))
        if case.get("bundle_sha256") != sha(bundle_raw):
            raise ValueError("Labeled bundle has changed")
        bundle_path = root / case["bundle"]
        review_path = None
        if case.get("reviews"):
            review_raw = read_input(root, case["reviews"])
            if case.get("reviews_sha256") != sha(review_raw):
                raise ValueError("Evaluation review receipt has changed or is not hash-bound")
            review_path = root / case["reviews"]
        report = validate(bundle_path, snapshot, review_path, references_only)
        if case.get("fingerprint") != report["fingerprint"]:
            raise ValueError("Evaluation fingerprint changed; preserve labels and explicitly rebaseline")
        findings = {f["rule_id"]: f for f in report["findings"]}
        findings.update({f["criterion_id"]: f | {"method": "editorial", "family": f["dimension"]}
                         for f in report["eeat_criteria"]})
        for rid, label in expected.items():
            if rid not in findings:
                raise ValueError("Unknown expected rule")
            finding = findings[rid]
            observed = finding["status"]
            outcome = "unresolved" if observed not in ("pass", "fail") else {
                ("fail", "fail"): "true_positive", ("pass", "fail"): "false_positive",
                ("fail", "pass"): "false_negative", ("pass", "pass"): "true_negative",
            }[(label, observed)]
            rows.append({"case_id": case["id"], "kind": case["kind"], "split": case["split"],
                         "brand": case["brand"], "page_type": report["page_type"],
                         "rule_id": rid, "family": finding["family"], "expected": label,
                         "method": finding["method"], "labeler_kind": labeler_kind,
                         "reviewer_kind": (report["review_actor"] or {}).get("kind", "none"),
                         "observed": observed, "outcome": outcome})
    groups = []
    for key in sorted({(r["kind"], r["split"], r["page_type"], r["method"], r["labeler_kind"]) for r in rows}):
        selected = [r for r in rows if (r["kind"], r["split"], r["page_type"], r["method"], r["labeler_kind"]) == key]
        groups.append(dict(zip(("kind", "split", "page_type", "method", "labeler_kind"), key)) | summarize(selected))
    return {"schema_version": 2, "manifest_sha256": sha(raw), "case_count": len(cases),
            **summarize(rows), "results": rows, "groups": groups,
            "automatic_metrics": summarize([r for r in rows if r["method"] == "auto"]),
            "review_agreement_metrics": summarize([r for r in rows if r["method"] != "auto"]),
            "independence_verified": False, "calibration_status": "not_established",
            "release_approved": False,
            "limits": "Labels and reviewer identity are attestations. Review agreement is not independent model accuracy. Unresolved cases are excluded from binary metrics; inspect resolved_fraction. Synthetic cases do not establish real-content calibration. No release threshold is implied."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snapshot", type=Path)
    mode.add_argument("--references-only", action="store_true")
    args = parser.parse_args()
    try:
        result = evaluate(args.manifest, args.snapshot, args.references_only)
        print(canonical(result).decode())
        counts = result["counts"]
        return 2 if any(counts.get(k, 0) for k in ("false_positive", "false_negative", "unresolved")) else 0
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as exc:
        print(canonical({"error": str(exc)}).decode(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
