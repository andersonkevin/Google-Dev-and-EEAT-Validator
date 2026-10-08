"""Synthetic correction in temporary files; no model, source research or approvals."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from validate_draft import validate


def walkthrough():
    examples = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="editorial-review-demo-") as directory:
        root = Path(directory).resolve()
        bundle = json.loads((examples / "bundle.json").read_text())
        correct = (examples / "draft.html").read_text()
        bundle["claims"][0]["quote"] = bundle["claims"][0]["quote"].replace("three", "300")
        (root / "bundle.json").write_text(json.dumps(bundle))
        (root / "draft.html").write_text(correct.replace("three", "300"))
        (root / "evidence.txt").write_bytes((examples / "evidence.txt").read_bytes())
        path = root / "bundle.json"
        first = validate(path, references_only=True)
        decision = {"status": "fail", "reviewer": "Synthetic AI reviewer",
                    "reason": "The draft says 300 records; the fixture records three. Synthetic contradiction.",
                    "reviewed_at": "2026-10-08", "evidence_ids": ["export-test"]}
        receipt = {"schema_version": 2, "purpose": "illustration", "fingerprint": first["fingerprint"],
                   "actor": {"kind": "ai", "identity": "Synthetic AI reviewer", "model": "fixture-not-a-model",
                             "run_id": "synthetic-walkthrough", "relationship_to_author": "same_agent"},
                   "decisions": [decision | {"rule_id": "CLAIM-002"}],
                   "criteria": [decision | {"criterion_id": "TRUST-02"}], "sources": []}
        review_path = root / "review-before.json"
        review_path.write_text(json.dumps(receipt))
        reviewed = validate(path, review_path=review_path, references_only=True)
        bundle["claims"][0]["quote"] = bundle["claims"][0]["quote"].replace("300", "three")
        (root / "bundle.json").write_text(json.dumps(bundle))
        (root / "draft.html").write_text(correct)
        stale = validate(path, review_path=review_path, references_only=True)
        corrected = validate(path, references_only=True)
        after = json.loads(json.dumps(receipt))
        after["fingerprint"] = corrected["fingerprint"]
        for group in ("decisions", "criteria"):
            after[group][0].update(status="pass", reason="Rechecked corrected text: three records, matching synthetic record-count evidence only.")
        new_review = root / "review-after.json"
        new_review.write_text(json.dumps(after))
        final = validate(path, review_path=new_review, references_only=True)
        return {"synthetic": True, "model_called": False, "source_research_performed": False,
                "before_review": first["readiness"], "supported_contradiction": reviewed["readiness"],
                "old_receipt_rejected_after_correction": bool(stale["review_error"]),
                "after_correction": final["readiness"], "publication_approved": final["publication_approved"],
                "remaining_criteria": sum(c["status"] == "needs_review" for c in final["eeat_criteria"]),
                "source_review_required": final["source_review_required"],
                "explanation": "The claim was corrected, not the page approved. Temporary files only; no actual AI review or calibration was performed."}


if __name__ == "__main__":
    print(json.dumps(walkthrough(), indent=2))
