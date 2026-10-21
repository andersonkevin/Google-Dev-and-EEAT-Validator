"""Read-only editorial trace audit; preserve native verdicts and disclose missing detail."""
import argparse
from collections import Counter
from pathlib import Path
import sys

from validate_draft import Page, canonical, load_bundle, nonempty, read_input, read_json, sha, validate

CLAIM_TYPES = {"documented_fact", "interpretation", "recommendation", "hypothetical_example"}
SCOPES = {"article", "project", "method", "rendered"}
ARTICLE_SPECIFIC = {
    "QUALITY-001", "QUALITY-002", "CLAIM-002", "CLAIM-003", "META-004", "STYLE-003",
    "MEDIA-003", "INTENT-001", "CONTEXT-01", "EXPERIENCE-01", "EXPERIENCE-02",
    "EXPERIENCE-03", "EXPERTISE-02", "EXPERTISE-03", "TRUST-02", "TRUST-05", "QUALITY-01",
}
PROJECT_CONTEXT = {"TRUST-001", "TRUST-01", "AUTHORITY-01", "AUTHORITY-03", "RATER-001"}
SOURCE_FIELDS = ("source_id", "location", "source_version", "reading_note", "supports", "does_not_support", "evidence_scope")


def normalize(value):
    return " ".join(value.split())


def evidence_trace(bundle, root, shared_root):
    records = []
    for item in bundle["evidence"]:
        missing = [k for k in SOURCE_FIELDS if not nonempty(item.get(k))]
        for key in SOURCE_FIELDS:
            if key in item and not nonempty(item[key]):
                raise ValueError("Invalid evidence annotation: " + key)
        if item.get("evidence_scope") not in (None, "method", "project", "article"):
            raise ValueError("Invalid evidence scope")
        capture = item.get("shared_capture")
        reuse = "not_declared"
        if capture is not None:
            if not isinstance(capture, dict) or set(capture) != {"file", "sha256"}:
                raise ValueError("shared_capture requires file and sha256")
            local_hash = sha(read_input(root, item["file"]))
            if capture["sha256"] != local_hash:
                raise ValueError("Shared capture does not match the bundle snapshot")
            # Validate the relative selector even when no shared directory was selected.
            selector = capture["file"]
            if (not nonempty(selector) or Path(selector).is_absolute() or ".." in Path(selector).parts
                    or "\\" in selector):
                raise ValueError("Shared capture path must be confined")
            reuse = "not_checked_no_shared_root"
            if shared_root is not None:
                if sha(read_input(shared_root, selector)) != local_hash:
                    raise ValueError("Shared capture changed; refresh the local snapshot and reassess before review reuse")
                reuse = "same_bytes_only_not_reused_interpretation"
        records.append({"evidence_id": item["id"], "document": item.get("origin"),
                        "accessed_at": item.get("captured_at"), "file_sha256": sha(read_input(root, item["file"])),
                        **{k: item.get(k) for k in SOURCE_FIELDS},
                        "missing_trace_fields": missing, "reuse_check": reuse,
                        "support_verified": False})
    return records


def review_trace(report, page, claims):
    records = []
    for finding in report["findings"] + report["eeat_criteria"]:
        if finding.get("method") == "auto" or ("rule_id" in finding and finding["method"] == "live"):
            continue
        decision = finding.get("decision")
        if not decision:
            continue
        identifier = finding.get("rule_id", finding.get("criterion_id"))
        scope = decision.get("assessment_scope")
        if scope is not None and scope not in SCOPES:
            raise ValueError("Invalid assessment_scope")
        passage = decision.get("passage")
        claim_id = decision.get("claim_id")
        if claim_id is not None:
            if not isinstance(claim_id, str) or claim_id not in claims:
                raise ValueError("Review claim_id is not in the current ledger")
            passage = passage or claims[claim_id]["quote"]
        location = decision.get("passage_location", "body")
        if location not in ("body", "title", "description"):
            raise ValueError("Unsupported passage_location")
        available = page.text if location == "body" else " ".join(
            n["text"] if location == "title" else n["attrs"].get("content", "")
            for n in page.nodes if n["tag"] == ("title" if location == "title" else "meta")
            and (location == "title" or n["attrs"].get("name", "").lower() == "description"))
        if passage is not None and (not nonempty(passage) or normalize(passage) not in normalize(available)):
            raise ValueError("Review passage is absent from the stated current content location")
        flags = []
        if scope is None:
            flags.append("assessment_scope_not_recorded")
        if identifier in ARTICLE_SPECIFIC and (scope != "article" or not passage):
            flags.append("article_specific_reference_not_recorded")
        if scope == "article" and not passage:
            flags.append("passage_or_claim_reference_not_recorded")
        if finding["status"] == "fail" and not nonempty(decision.get("correction")):
            flags.append("concrete_correction_not_recorded")
        records.append({"check_id": identifier, "status": finding["status"],
                        "assessment_scope": scope, "passage": passage, "passage_location": location,
                        "claim_id": claim_id, "evidence_ids": decision["evidence_ids"],
                        "conclusion": decision["reason"], "correction": decision.get("correction"),
                        "trace_flags": flags, "semantic_adequacy_verified": False})
    return records


def audit(path, snapshot=None, review_path=None, references_only=False, *, shared_root=None, peers=()):
    path = Path(path).absolute()
    root = path.parent
    report = validate(path, snapshot, review_path, references_only)
    bundle, content, _ = load_bundle(path)
    evidence = evidence_trace(bundle, root, shared_root)
    indexed = {e["evidence_id"]: e for e in evidence}
    claims = []
    for claim in bundle["claims"]:
        kind = claim.get("claim_type")
        if kind is not None and kind not in CLAIM_TYPES:
            raise ValueError("Unsupported claim_type")
        sources = [indexed[k] for k in claim["evidence_ids"] if k in indexed]
        claims.append({"claim_id": claim["id"], "quote": claim["quote"], "claim_type": kind,
                       "evidence_ids": claim["evidence_ids"], "sources": sources,
                       "trace_detail_recorded": bool(kind and sources and all(not s["missing_trace_fields"] for s in sources)),
                       "entailment_verified": False})
    judgments = review_trace(report, Page(content.decode("utf-8")), {c["id"]: c for c in bundle["claims"]})
    repetitions = []
    for peer in peers:
        raw = read_input(root, peer)
        record = read_json(raw)
        if not isinstance(record, dict) or type(record.get("schema_version")) is not int or record["schema_version"] != 2:
            raise ValueError("Peer receipt must use schema 2")
        reasons = {d.get("criterion_id", d.get("rule_id")): d.get("reason")
                   for field in ("decisions", "criteria") for d in record.get(field, []) if isinstance(d, dict)}
        for decision in judgments:
            if reasons.get(decision["check_id"]) == decision["conclusion"]:
                repetitions.append({"check_id": decision["check_id"], "peer_sha256": sha(raw),
                                    "assessment_scope": decision["assessment_scope"],
                                    "interpretation": "Repeated reason; inspect relevance, not an automatic defect"})
    layers = {"automatic_checks": [], "operator_judgments": [], "scope_exclusions": [],
              "pending_assessments": [], "rendered_or_live": [],
              "project_context_pending": [], "content_corrections": []}
    actions = []
    for finding in report["findings"] + report["eeat_criteria"]:
        identifier = finding.get("rule_id", finding.get("criterion_id"))
        method = finding.get("method", "editorial")
        row = {"check_id": identifier, "status": finding["status"], "method": method,
               "kind": "rule" if "rule_id" in finding else "criterion"}
        layer = ("automatic_checks" if method == "auto" else "rendered_or_live" if method in ("rendered", "live") else
                 "operator_judgments" if finding.get("decision") else
                 "scope_exclusions" if finding["status"] == "not_applicable" else "pending_assessments")
        if layer == "rendered_or_live":
            row["evidence_kind"] = ("imported_observation" if finding.get("observation") else
                                    "operator_attestation" if finding.get("decision") else "not_observed")
        layers[layer].append(row)
        if finding["status"] in ("needs_review", "not_tested", "fail"):
            rendered = method in ("rendered", "live") or identifier == "QUALITY-03"
            owner = "rendered_reviewer" if rendered else "project_owner" if identifier in PROJECT_CONTEXT else "editor"
            if identifier in PROJECT_CONTEXT and finding["status"] != "fail":
                layers["project_context_pending"].append(row)
            if finding["status"] == "fail" and method not in ("rendered", "live"):
                layers["content_corrections"].append(row)
            actions.append(row | {"owner": owner, "next_action":
                "Correct the supported finding or preserve a locked-copy blocker" if finding["status"] == "fail" else
                "Supply actual rendered/live evidence" if rendered else
                "Resolve project identity or reputation context; missing reputation is not adverse evidence" if owner == "project_owner" else
                "Assess the named criterion against the current passage and evidence"})
    for source in report["source_reviews"]:
        if source["status"] != "pass":
            actions.append({"source": source["source"], "status": source["status"],
                            "owner": "source_reviewer", "next_action": "Read and evidence the required source; inactive rules do not waive it"})
    if report["review_error"]:
        actions.append({"owner": "reviewer", "next_action": "Reassess current inputs; do not replace only the old receipt fingerprint"})
    for judgment in judgments:
        if judgment["trace_flags"]:
            actions.append({"check_id": judgment["check_id"], "owner": "editor",
                            "next_action": "Supply missing review trace details, not an invented correction",
                            "trace_flags": judgment["trace_flags"]})
    for claim in claims:
        if not claim["trace_detail_recorded"]:
            actions.append({"claim_id": claim["claim_id"], "owner": "researcher",
                            "next_action": "Identify the specific source, location, claim type, support and limits"})
    return {"schema_version": 1, "kind": "editorial_audit", "validator_version": report["validator_version"],
            "readiness": report["readiness"], "publication_approved": False,
            "native_report": report, "native_report_sha256": sha(canonical(report)),
            "audit_engine_sha256": sha(Path(__file__).read_bytes()),
            "integrity": {"bundle_inputs": "validated_by_native_tool", "ghosteditor_package": "not_checked_here",
                          "review_supplied": review_path is not None, "review_current": review_path is not None and not report["review_error"],
                          "review_error": report["review_error"], "fingerprint": report["fingerprint"]},
            "assurance": {"actor": report["review_actor"], "source_verification": report["source_verification"],
                          "source_review_assurance": report["source_review_assurance"],
                          "independence_verified": False, "calibration_status": "not_established"},
            "layers": layers, "layer_counts": {k: dict(Counter(r["status"] for r in v)) for k, v in layers.items()},
            "operator_counts": {kind: dict(Counter(r["status"] for r in layers["operator_judgments"] if r["kind"] == kind))
                                for kind in ("rule", "criterion")},
            "source_attestation_counts": dict(Counter(s["status"] for s in report["source_reviews"])),
            "claim_trace": claims, "evidence_inventory": evidence, "judgment_trace": judgments,
            "repeated_reasons": repetitions, "next_actions": actions,
            "trace_complete": bool(judgments) and all(c["trace_detail_recorded"] for c in claims) and all(not d["trace_flags"] for d in judgments),
            "limits": ["Trace completeness is metadata coverage, not factual accuracy or substantive review.",
                       "No semantic detector, model call, browser observation or publication permission.",
                       "Shared snapshots reuse bytes, never source attestations, article judgments or approvals.",
                       "Zero edit rounds and repeated project context are legitimate; verify content-specific reasoning."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snapshot", type=Path)
    mode.add_argument("--references-only", action="store_true")
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--shared-root", type=Path)
    parser.add_argument("--peer-reviews", action="append", default=[])
    args = parser.parse_args()
    try:
        result = audit(args.bundle, args.snapshot, args.reviews, args.references_only,
                       shared_root=args.shared_root, peers=args.peer_reviews)
        print(canonical(result).decode())
        return {"ready_for_owner_review": 0, "review_required": 2, "blocked": 3}[result["readiness"]]
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, RecursionError) as exc:
        print(canonical({"readiness": "invalid_input", "publication_approved": False, "error": str(exc)}).decode(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
