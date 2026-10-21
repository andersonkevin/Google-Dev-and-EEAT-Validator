"""Resolve the review-reference matrix without changing production gates."""
from pathlib import Path

from rule_catalog import VERSION, catalog, criteria_map, profile_prompt
from validate_draft import read_json, sha

MATRIX = Path(__file__).resolve().parents[1] / "references/applicability-matrix.json"


def applicability_matrix():
    raw = MATRIX.read_bytes()
    matrix = read_json(raw)
    mapping = criteria_map()
    if (type(matrix.get("schema_version")) is not int or matrix["schema_version"] != 1
            or matrix.get("matrix_version") != "1.0.0"
            or matrix.get("catalog_version") != VERSION
            or matrix.get("mapping_version") != mapping["mapping_version"]):
        raise ValueError("Applicability matrix version mismatch")
    profiles = matrix.get("profiles")
    if (not isinstance(profiles, dict) or set(profiles) != {"article", "landing", "draft", "staging", "live"}
            or any(not isinstance(v, str) or not v.strip() for v in profiles.values())):
        raise ValueError("Invalid applicability profiles")
    entries = []
    for field, originals, required in (
            ("rules", catalog(), ("when", "evidence", "exception", "limit")),
            ("criteria", mapping["criteria"], ("not_applicable_when",))):
        rows = matrix.get(field)
        if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
            raise ValueError("Invalid applicability matrix entries")
        identifiers = [r.get("id") for r in rows]
        if (any(not isinstance(identifier, str) for identifier in identifiers)
                or len(identifiers) != len(set(identifiers)) or set(identifiers) != {r["id"] for r in originals}):
            raise ValueError("Applicability matrix must cover each rule and criterion exactly once")
        indexed = {r["id"]: r for r in rows}
        for original in originals:
            row = indexed[original["id"]]
            if any(not isinstance(row.get(k), str) or not row[k].strip() for k in required if k != "evidence"):
                raise ValueError("Incomplete applicability entry: " + original["id"])
            if field == "rules" and (not isinstance(row.get("evidence"), list) or not row["evidence"]
                                     or any(not isinstance(v, str) or not v.strip() for v in row["evidence"])):
                raise ValueError("Invalid applicability evidence: " + original["id"])
            if field == "rules":
                stages = (["live"] if original["method"] == "live" else
                          ["staging", "live"] if original["method"] == "rendered" or original["applies"] == "page"
                          else ["draft", "staging", "live"])
                entries.append(row | {
                    "kind": "rule", "title": original["title"], "method": original["method"],
                    "severity": original["severity"], "basis_class": original["source_class"],
                    "sources": [original["source"]], "stages": stages,
                    "current_gate": "always_scope_review" if original["applies"] == "ymyl" else original["applies"],
                    "article": profile_prompt(original, "article"),
                    "landing": profile_prompt(original, "landing"),
                    "failure_precedence": "Explicit supported failure survives inferred scope exclusion",
                })
            else:
                entries.append(row | {
                    "kind": "criterion", "title": original["title"], "method": "editorial",
                    "severity": "criterion_failure_blocks", "current_gate": "explicit_contextual_decision",
                    "basis_class": "contextual_quality_interpretation",
                    "source_classes": sorted({mapping["sources"][s]["class"] for s in original["sources"]}),
                    "sources": sorted({u for s in original["sources"] for u in mapping["sources"][s]["urls"]}),
                    "stages": ["draft", "staging", "live"],
                    "when": original["applies_when"], "evidence": original["evidence"],
                    "exception": original["exception"], "limit": original["automation_limit"],
                    "article": original["article"], "landing": original["landing"],
                    "pass_condition": original["pass"], "fail_condition": original["fail"],
                    "unknown_condition": original["unknown"],
                    "failure_precedence": "Every supported criterion failure blocks owner readiness",
                })
    return {k: v for k, v in matrix.items() if k not in ("rules", "criteria")} | {
        "matrix_sha256": sha(raw), "entries": entries,
        "publication_approved": False, "calibration_status": "not_established",
    }
