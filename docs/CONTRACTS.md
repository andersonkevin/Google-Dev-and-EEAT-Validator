# Input, Evidence And Decision Contracts

## Bundle

Use `examples/bundle.json` as the starting point. Schema version is 1.

- `page_type`: article or landing.
- `stage`: draft, staging or live.
- `content`: relative path to HTML, including the intended main heading.
- `brief`: audience, market, purpose, intent, next_action, responsible_party,
  and explicit booleans ymyl, updated and video_search_claim.
- Later stages also need canonical_url and indexing (index or noindex).
- `claims`: unique ID, exact normalized quote and evidence_ids.
- `evidence`: unique ID, relative file, title, origin and ISO captured_at.
- Optional `observations`: relative receipt file paths.

All referenced bundle files must stay inside its directory, be nonsymlink files
and not exceed 8 MiB. JSON rejects duplicate keys and nonfinite values.
Dates accept YYYY-MM-DD or an ISO datetime with timezone. Syntax is not proof of
historical accuracy or currency.

## Review Receipt

Run once to obtain the current fingerprint. A separate review receipt contains:

```json
{
  "fingerprint": "exact current report fingerprint",
  "decisions": [{
    "rule_id": "CLAIM-002",
    "status": "fail",
    "reviewer": "Actual responsible reviewer",
    "reviewed_at": "2026-10-08",
    "reason": "Explain the precise claim and evidence conflict.",
    "evidence_ids": ["actual-evidence-id"]
  }]
}
```

Pass it with `--reviews PATH`. Statuses: pass, fail or not_applicable. Every
decision requires evidence, reason, reviewer and date. Do not use this illustrative
record as approval. Identities are operator attestations, not authenticated signatures.

The fingerprint binds the draft, brief, evidence, rules, engine, source mode and
observations. Changing any of these invalidates the receipt. Existing failures
cannot be waived by claiming non-applicability; automatic rules cannot be overridden
by a human receipt. YMYL false still requires a contextual scope review.

## Decision Precedence

1. Invalid input/integrity produces invalid_input, not a content verdict.
2. A stale receipt supplies no decisions and leaves review outstanding.
3. A current explicit failure is retained, including applicability conflicts.
4. Otherwise, inapplicable stage/feature produces not_applicable.
5. Applicable automatic checks compute their own result.
6. Applicable imported observations or human decisions supply their narrow result.
7. Missing live evidence is not_tested; missing semantic assessment needs_review.

Error/critical failures block. Warning failures and unresolved reviews require
review. References-only source mode always requires review. No readiness state
authorizes publication or guarantees a ranking result.

## Optional Local Source Snapshot

No reference snapshot is included. A compatible snapshot is an operator-prepared
directory with the following files, read without executing any content:

```text
snapshot/
  manifest.json
  knowledge/audit.json
  knowledge/chunks.jsonl
  local source files referenced by chunks
```

`audit.json` requires manifest_sha256, chunks_sha256, complete_within_scope and
source_exceptions. Hash the exact bytes of the two corresponding files.
Each JSONL chunk requires id, citation, source_file and source_sha256. All
runtime rule citations must resolve to at least one chunk, and all referenced
source file hashes are checked. Source paths must stay within the snapshot and
cannot traverse symlinks. Review the original license before acquiring any material.

These integrity checks do not prove that supplied source text is genuinely from
Google or current. A complete_within_scope flag does not constitute editorial
adjudication. Do not fabricate a snapshot merely to obtain a ready result.

```sh
python3 -B tools/validate_draft.py examples/bundle.json --snapshot /path/to/private-snapshot
python3 -B tools/validate_draft.py --coverage --snapshot /path/to/private-snapshot
```

Coverage accepts optional `--triage PATH`: chunks_sha256 and decisions containing
chunk_id, disposition, reviewer, reviewed_at and reason. Dispositions are
active_evidence, context, example, duplicate, retired, out_of_scope or unresolved.
Active evidence needs rule_ids; duplicate needs a distinct known duplicate_of.
Unknown chunks and source exceptions remain visible. Coverage never certifies release.

## Imported Observations

A receipt has schema_version 1, content_sha256 and context_sha256 from the report,
url matching the declared canonical_url, captured_at, reviewer and nonempty checks.
Each check contains rule_id, pass/fail/not_tested status, reason and an
evidence_sha256 object mapping bundle evidence IDs to their exact hashes.
Only live/rendered rule IDs are accepted, once each. No network or browser is run.
Receipt hashes enter the review fingerprint. Re-run after attaching observations.
Capture age, environment suitability and authenticity remain human responsibilities.

## Independent Evaluation

```sh
python3 -B tools/evaluate_validator.py /path/to/private-cases.json --snapshot /path/to/private-snapshot
```

An evaluation manifest uses schema_version 1 and a nonempty cases list. Each case
has a unique id, kind (synthetic/real), split (development/holdout), brand, actual
labeler, labeled_at, relative bundle, bundle_sha256, validator fingerprint and
expected rule IDs mapped to pass/fail. An optional reviews path supplies decisions.
Prepare expected labels independently before examining output.

Results include raw confusion outcomes, precision/recall and unresolved findings.
No denominator gives null, not a claimed zero error rate. Unresolved results are
not successes. The evaluator requires a snapshot; it has no references-only mode.
Exit 0 means no mismatch/unresolved in the supplied set, 1 invalid input, 2 a mismatch
or unresolved result. Evaluation never issues release approval.

## Export Integrity

Only `--output NEW_DIRECTORY --execute` writes. The parent must exist; existing
destinations and symlink paths are rejected. report.json and report.txt are followed
by COMPLETE.json with their hashes and the fingerprint. Reject incomplete or
mismatched receipts. Interrupted files remain for inspection rather than being
silently overwritten or deleted.
