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

V2 keeps bundle schema 1 but requires review schema 2. Run once for the current
fingerprint or use `--review-template` for an unresolved scaffold. A partial receipt:

```json
{
  "schema_version": 2,
  "purpose": "content_review",
  "fingerprint": "exact current report fingerprint",
  "actor": {
    "kind": "ai",
    "identity": "Operating review agent",
    "model": "not_exposed",
    "run_id": "review-001",
    "relationship_to_author": "same_agent"
  },
  "decisions": [{
    "rule_id": "CLAIM-002",
    "status": "fail",
    "reviewer": "Operating review agent",
    "reviewed_at": "2026-10-08",
    "reason": "Explain the precise claim and evidence conflict.",
    "evidence_ids": ["actual-evidence-id"]
  }],
  "criteria": [],
  "sources": []
}
```

Pass it with `--reviews PATH`. Statuses are pass, fail, not_applicable or needs_review.
Every decision requires reason, reviewer and date. Resolved decisions also require
nonempty, distinct local evidence IDs; needs_review may have no evidence. Reviewer
must match actor.identity. These identities are attestations, not authenticated signatures.

Actor kind is ai or human. AI requires model, run_id and relationship_to_author
(same_agent, separate_context or unknown); human uses human_review or unknown.
Use not_exposed when the actual model name is unavailable; never invent it.
Purpose is content_review or illustration. Illustrations cannot become ready.

The decisions list accepts only editorial and rendered rules. Automatic findings
cannot be overridden. Live observations retain their separate receipt contract.

The criteria list uses criterion_id for each of the 20 map entries, with the same
status/reviewer/reason/date/evidence fields. All start needs_review, including the
two areas that previously lacked dedicated review coverage. Applicability is a
reasoned reviewer decision, not inferred from related-rule passes. Conditional
criteria can be not_applicable with evidence explaining the exception. Missing
proof remains needs_review. Every explicit criterion failure blocks readiness.

The sources list uses source for each exact URL in report.source_reviews. URL
fragments are grouped by document, but the reviewer must inspect the cited sections.
Only pass, fail and needs_review are accepted: a source cannot be waived with
not_applicable. Attach actual capture/review notes as bundle evidence. Never copy
synthetic source assertions into a real review. Source conflicts block readiness.

The fingerprint binds draft, brief, evidence, rules, criterion map, engine, source
mode and observations. Changing any invalidates the receipt. Existing failures
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

Error/critical rule failures, criterion failures and source failures block.
Warning failures and unresolved reviews require review. References-only may reach
ready_for_owner_review after all required assessments, but source_verification
remains references_only_not_verified and source_review_assurance explicitly reports
operator_attestation_only. Even snapshot mode requires source-review decisions;
file integrity is not interpretation. No state authorizes publication.

Report schema is 2, with review_actor, review_purpose, review_receipt_sha256,
eeat_criteria, eeat_counts and source_reviews. Counts for rules and criteria remain
separate; they are not a score. publication_approved and reviewer_identity_verified
are always false. V1 receipts must be replaced by fresh review, not migrated by
editing their schema or fingerprint without reassessment.

## Review Plan

`--review-plan` prints schema 1 with `kind: review_plan`. It is a read-only view of
the normal validation result, not a review receipt or source verification.
It may be combined with `--reviews` to show remaining work after a current review.
It cannot be combined with `--review-template`, `--coverage`, `--output` or
`--execute`. It retains normal readiness exit codes: 0, 2 or 3; invalid input is 1.
Unlike the receipt scaffold, successfully printing a plan does not always exit 0.

The plan retains validator version, fingerprint, stage, page type, readiness,
review error and source-assurance state. `publication_approved` remains false.

- `mechanical_failures`: automatic failures with locations and remediation.
- `review_tasks`: unresolved or failed editorial, rendered and live checks,
  including explicit scope conflicts.
- `criterion_tasks`: unresolved or failed criteria with scope, exceptions,
  evidence requirements and any current decision.
- `sources`: every required source document, grouped without URL fragments,
  with exact cited `sections`, associated rule/criterion IDs, pending IDs,
  current status and any current decision. `required` is always true.
- `static_scope_notes`: the link-name check's reported scope, including any
  HTML-hidden link exclusions that require activated-state review.

Grouping does not narrow the catalog-wide source requirement: even a document
linked only to inactive rules remains required. Existing pass/not_applicable
decisions remove resolved tasks from the queue, not from the underlying report.
A stale receipt supplies no decisions to either output. The plan never fetches
sources, collects evidence or creates assessments. Use the full report and
original receipt for provenance and final handoff.

`ANCHOR-003` skips links with HTML `hidden` ancestry in the supplied state and
discloses how many were excluded. This does not exempt visible links whose
children are hidden, or focusable links hidden only from the accessibility tree
with `aria-hidden`. CSS visibility, future revealed states and browser accessible
names require rendered review. Other link checks retain their existing scope.

See [integration guidance](INTEGRATION.md) for a project-neutral adapter sequence.

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
python3 -B tools/evaluate_validator.py /path/to/private-cases.json --references-only
```

The legacy evaluation manifest uses schema_version 1 and a nonempty cases list. Each case
has a unique id, kind (synthetic/real), split (development/holdout), brand, actual
labeler, labeled_at, relative bundle, bundle_sha256, validator fingerprint and
expected rule or criterion IDs mapped to pass/fail. Optional reviews supplies
decisions and requires reviews_sha256 binding the exact receipt bytes.
Optional labeler_kind is ai, human or unspecified; ai also requires labeler_model.
Prepare expected labels independently before examining output.

Results include raw confusion outcomes, precision/recall and unresolved findings,
automatic_metrics, review_agreement_metrics and resolved_fraction. Groups separate
kind, split, page_type, method and labeler_kind. AI review agreement is not
independent accuracy; identity and label independence are not authenticated.
No denominator gives null, not a claimed zero error rate. Unresolved results are
not successes. Choose either --snapshot or --references-only, matching the fingerprint.
Exact draft bytes cannot occur in both development and holdout, even with different
bundle context. `dataset_summary` adds per-case coverage counts, unique draft count
and declared-provenance warnings; it does not detect semantic leakage or authenticate
labelers. Manifest 1 still returns report 2 with unchanged binary semantics,
including treating an observed not_applicable as unresolved.
Exit 0 means no mismatch/unresolved in the supplied set, 1 invalid input, 2 a mismatch
or unresolved result. Evaluation never issues release approval or calibration claims.
See [CALIBRATION.md](CALIBRATION.md).

## Applicability-Aware Evaluation

Opt in with evaluation **manifest schema 2**; the same command returns
**evaluation report schema 3**. Production bundles remain schema 1 and production
reports/review receipts remain schema 2. `tools/describe.py` preserves its legacy
scalar contract fields and advertises both explicit evaluation schema pairs in
`supported_evaluation_contracts`. No automatic manifest conversion occurs.

All legacy case provenance, file/hash, mode and fingerprint requirements remain.
Each case additionally requires a nonempty `source_family_id`, shared by an
original and all rewrites, variants and controlled synthetic derivatives. Neither
exact draft bytes nor a declared source family may cross development/holdout.
Same-split variants remain allowed and counted, not independent real pages.
Family identity is supplied metadata: dishonest or missing lineage cannot be
detected semantically by this tool. A stale supplied receipt is invalid input in
manifest 2, even if its current bytes are hash-bound.

Each `expected` rule/criterion value is now an object, for example:

```json
{
  "applicability": "not_applicable",
  "status": "not_applicable",
  "reason": "The reviewed draft has no first-hand testing claim.",
  "evidence_ids": ["scope-review"]
}
```

This is an illustrative label shape, not supplied evidence or an approval.
`scope-review` must be an actual evidence ID in that case's hash-bound bundle.
Allowed combinations:

| Expected applicability | Expected status |
| --- | --- |
| applicable | pass, fail, needs_review, or not_tested |
| not_applicable | not_applicable |
| unknown | needs_review |

Exactly `applicability`, `status`, `reason` and `evidence_ids` are required in a
label. Reason must be nonempty; references must be distinct, known bundle evidence
IDs. Resolved labels require evidence; pending labels may have an empty list.
`not_tested` is allowed only for rendered/live checks. Reference checks do not
establish the truth, independence or sufficiency of a label.

**Observed applicability is explicitly a status proxy**, not a new production
receipt field: pass/fail/not_tested imply applicable, not_applicable implies
excluded, needs_review leaves scope unknown. A pending contextual review cannot
prove its own scope. Thus an expected applicable/needs_review label can match the
pending status while still leaving applicability unresolved. This limitation is
reported, not silently treated as scope agreement.

Report 3 provides:

- Full expected/observed status confusion and applicability outcomes per label.
- Raw counts plus `{numerator, denominator, value}` for each rate; zero denominators
  are null. Applicability agreement uses all gold-known scope labels, not only
  those the reviewer resolved. Unknown-scope labels have separate abstention counts.
- Defect precision/recall explicitly marked resolved-only, alongside resolution,
  detection across all gold failures, false passes, false defects, check-level false
  blocks, wrong exceptions and unresolved failures. These cannot disappear into a
  favorable binary denominator. Critical counters use existing critical rule
  severity, not an invented new E-E-A-T importance score.
- Correct/incorrect exclusions, unsupported certainty and wrong pending status.
  Blocking failures on gold-excluded cases are counted separately under exceptions;
  defect false-block rates use gold applicable/pass labels only. Correctly
  predicting uncertainty is not a content pass.
- Groups by kind/split/page type/method/labeler kind, per-check and per-page-type
  summaries, exact source-family counts, per-case readiness and report hashes.
- Matrix version/hash and evaluation-code hash. These identify evaluation policy;
  matrix/evaluation code does not enter production validation fingerprints and prior
  review schemas are unchanged. The v2.2.0 version/catalog bump does change native
  fingerprints, so earlier receipts require fresh assessment.

Exit 0 means supplied status and applicability expectations match, including
correctly expected uncertainty; 2 means disagreement or unresolved comparison;
1 means invalid input. Exit 0 does not mean the whole page passed: only supplied
labels are compared, and `case_reports` retains actual production readiness.
`independence_verified`, `release_approved` and `publication_approved` stay false;
`calibration_status` stays not_established. Missing real/holdout/development cases
and declared shared labeler/reviewer/model provenance remain visible warnings.
No rates authorize release or establish real-content reliability.

## Export Integrity

Optional [editorial trace annotations and layered output](EDITORIAL-TRACE.md)
reuse bundle 1 and receipt 2 extension fields. No historical package migration,
production schema change or new semantic verdict is introduced.

Only `--output NEW_DIRECTORY --execute` writes. The parent must exist; existing
destinations and symlink paths are rejected. report.json and report.txt are followed
by COMPLETE.json with their hashes and the fingerprint. Reject incomplete or
mismatched receipts. Interrupted files remain for inspection rather than being
silently overwritten or deleted.
