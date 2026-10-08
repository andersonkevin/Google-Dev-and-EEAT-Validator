"""Evaluate frozen, independently supplied labels without modifying cases or approvals."""
import argparse
from collections import Counter
from pathlib import Path
import sys

from validate_draft import canonical, nonempty, read_input, read_json, sha, valid_date, validate


def evaluate(manifest_path, snapshot):
    root = manifest_path.parent.resolve()
    raw = read_input(root, manifest_path.name)
    manifest = read_json(raw)
    if not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise ValueError("Expected evaluation schema_version 1")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Evaluation requires pre-labeled cases")
    rows, seen, metrics = [], set(), Counter()
    for case in cases:
        if not isinstance(case, dict) or not nonempty(case.get("id")) or case["id"] in seen:
            raise ValueError("Invalid or duplicate evaluation case")
        seen.add(case["id"])
        if case.get("kind") not in ("synthetic", "real") or case.get("split") not in ("development", "holdout"):
            raise ValueError("Case requires kind and fixed split")
        if not nonempty(case.get("labeler")) or not valid_date(case.get("labeled_at")) or not nonempty(case.get("brand")):
            raise ValueError("Case requires label provenance and brand")
        expected = case.get("expected")
        if not isinstance(expected, dict) or not expected or any(v not in ("pass", "fail") for v in expected.values()):
            raise ValueError("Expected findings must be independently labeled pass/fail")
        bundle_raw = read_input(root, case.get("bundle"))
        if case.get("bundle_sha256") != sha(bundle_raw):
            raise ValueError("Labeled bundle has changed")
        bundle_path = root / case["bundle"]
        review_path = None
        if case.get("reviews"):
            read_input(root, case["reviews"])
            review_path = root / case["reviews"]
        report = validate(bundle_path, snapshot, review_path)
        if case.get("fingerprint") != report["fingerprint"]:
            raise ValueError("Evaluation fingerprint changed; preserve labels and explicitly rebaseline")
        findings = {f["rule_id"]: f for f in report["findings"]}
        for rid, label in expected.items():
            if rid not in findings:
                raise ValueError("Unknown expected rule")
            finding = findings[rid]
            observed = finding["status"]
            outcome = "unresolved" if observed not in ("pass", "fail") else {
                ("fail", "fail"): "true_positive", ("pass", "fail"): "false_positive",
                ("fail", "pass"): "false_negative", ("pass", "pass"): "true_negative",
            }[(label, observed)]
            metrics[outcome] += 1
            rows.append({"case_id": case["id"], "kind": case["kind"], "split": case["split"],
                         "brand": case["brand"], "page_type": report["page_type"],
                         "rule_id": rid, "family": finding["family"], "expected": label,
                         "observed": observed, "outcome": outcome})
    tp, fp, fn = (metrics[k] for k in ("true_positive", "false_positive", "false_negative"))
    return {"schema_version": 1, "manifest_sha256": sha(raw), "case_count": len(cases),
            "counts": dict(metrics), "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None, "results": rows,
            "release_approved": False,
            "limits": "Labels are operator attestations; unresolved cases are excluded from binary metrics and must be reviewed. No release threshold is implied."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.manifest, args.snapshot)
        print(canonical(result).decode())
        counts = result["counts"]
        return 2 if any(counts.get(k, 0) for k in ("false_positive", "false_negative", "unresolved")) else 0
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as exc:
        print(canonical({"error": str(exc)}).decode(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
