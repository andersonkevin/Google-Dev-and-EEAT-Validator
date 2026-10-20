"""Print the local integration contract without reading a project or writing files."""
import json

from rule_catalog import VERSION, catalog, criteria_map


def describe():
    return {
        "schema_version": 1,
        "tool": "Google-Dev-and-EEAT-Validator",
        "version": VERSION,
        "python_minimum": "3.10",
        "contracts": {
            "bundle": 1, "review_receipt": 2, "report": 2,
            "observation": 1, "review_plan": 1,
            "evaluation_manifest": 1, "evaluation_report": 2,
        },
        "mapping_version": criteria_map()["mapping_version"],
        "catalog_version": criteria_map()["catalog_version"],
        "page_types": ["article", "landing"],
        "stages": ["draft", "staging", "live"],
        "rule_count": len(catalog()),
        "criterion_count": len(criteria_map()["criteria"]),
        "read_only_commands": {
            "describe": "tools/describe.py",
            "validate": "tools/validate_draft.py",
            "evaluate": "tools/evaluate_validator.py",
        },
        "validation_exit_codes": {
            "0": "ready_for_owner_review", "1": "invalid_input",
            "2": "review_required", "3": "blocked",
        },
        "network_calls": False,
        "model_calls": False,
        "publication_approved": False,
        "report_export_requires_execute": True,
        "limits": "Contract discovery is not a source, content, security or publication approval.",
    }


if __name__ == "__main__":
    print(json.dumps(describe(), indent=2))
