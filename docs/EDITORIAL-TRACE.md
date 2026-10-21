# Editorial Trace Audit

This optional read-only view connects claims and review decisions to specific
evidence. It preserves the native report, readiness and exit codes. It does not
detect truth, run a model, collect sources, create reviews or grant publication.
It is included from v2.2.0 and is not available in the v2.1.0 distribution.

```sh
python3 -B tools/editorial_audit.py /private/new-run/bundle.json --references-only --reviews /private/new-run/reviews.json
```

Use `--snapshot PATH` instead when appropriate. JSON goes to stdout. Exit codes
remain 0 owner-review-ready, 1 invalid input, 2 review required, 3 blocked.
An annotated report never converts `review_required` into approval. Trace flags
are advisory metadata gaps, not new failures in the 46-rule catalog.

## Compatible Input Annotations

Bundle schema 1 and receipt schema 2 remain unchanged. Existing parsers allow
additional object fields; these optional annotations are included in the normal
bundle/receipt hashes. Old packages remain valid and are not rewritten. The audit
shows missing detail rather than inventing it. Malformed annotations, unavailable
quoted passages and inconsistent shared hashes are invalid input in this opt-in
command. The normal validator's behavior is unchanged.

A claim retains `id`, exact `quote` and `evidence_ids`. Add `claim_type`:
`documented_fact`, `interpretation`, `recommendation` or `hypothetical_example`.
Types are supplied classifications, not automatically inferred. A numeric result
still needs its actual period, denominator and support; labeling it interpretation
does not make it valid.

Reuse existing evidence fields `id`, `file`, `title`, `origin` (URL or document)
and `captured_at` (consultation/capture date). Add:

| Field | Meaning |
| --- | --- |
| source_id | Stable identifier for the actual document, not just a folder of sources |
| location | Section, page, anchor or equivalent locator relevant to the claim |
| source_version | Consulted revision/effective version, or an explicit unversioned designation |
| reading_note | Brief exact excerpt or precise reading note, identified honestly as such |
| supports | What this source supports for the linked claim in context |
| does_not_support | Material limits, exclusions or unknowns; do not invent generic disclaimers |
| evidence_scope | method, project or article |

Each material claim should link to the pertinent evidence entry. A file can contain
several notes, but each entry needs an identifiable source and locator. A general
`sources` container without a specific passage is visible as incomplete trace.
The tool checks annotation coverage and reference integrity, **not entailment**.

Within existing receipt `decisions` or `criteria`, retain the native ID, status,
reviewer/date, evidence IDs and reason. Add `assessment_scope`:
`article`, `project`, `method` or `rendered`. For content-specific decisions, add
an exact `passage` or `claim_id`. Optional `passage_location` is `body` (default),
`title` or `description`. The cited passage must occur in that current location.
`reason` explains the conclusion; `correction` describes an actual remedy when a
defect exists. A locked-content defect can name the needed owner decision instead
of changing the approved copy.

Accuracy, usefulness, content promises and similar checks cannot gain specificity
merely by being labeled project-wide: the audit flags a missing article reference.
It does not decide whether an explanation is persuasive or substantively correct.
Project identity, policy and research context can legitimately be shared. Do not
invent different wording or a minimum number of edits. Initial and final drafts
may be identical after a real, traceable review.

## Layered Output

`native_report` and its hash retain all authoritative findings. The additional
layers distinguish mechanical checks, actual operator judgments, inferred scope
exclusions, pending assessments, rendered/live evidence, project-context pending
items and content corrections. Operator counts separate rules from criteria.
Unobserved rendered/live checks are not called successful browser tests.

`integrity` distinguishes current bundle/review binding from GhostEditor package
checking, which this command does not perform. A stale receipt applies no old
decisions. `assurance` retains `same_agent`, `references_only_not_verified` and
`operator_attestation_only` where supplied by the native engine. An attestation is
not independent source authentication.

`next_actions` names the editor, researcher, project owner, source reviewer or
rendered reviewer and the required action. These are role recommendations, not
assigned people or a background task queue. `trace_complete` describes only the
recorded annotations on supplied claims/judgments, not complete substantive review.

Optional repeated `--peer-reviews RELATIVE_FILE` reads receipt copies confined to
the current bundle directory. Matching reasons become observations, not automatic
defects. Peer content is not applied as current review or authenticated as independent.

## Reuse Captures, Not Decisions

Separate method references, project evidence and article evidence. An operator
may keep reusable captures in an explicitly selected private directory. Copy the
relevant bytes into each bundle's confined evidence path before fingerprinting.
There is no downloader, cache writer, global store or approval inheritance.

An evidence entry may additionally declare:

```json
{"shared_capture": {"file": "method/source-note.txt", "sha256": "SHA256_OF_THE_CAPTURE_BYTES"}}
```

The value above is a placeholder, not a valid digest. The actual hash must match
the bundle's local evidence bytes. Select `--shared-root /private/shared-captures`
to compare the current shared file too. Paths are confined and symlinks rejected.
Without that option, shared currency is explicitly not checked. Shared-root drift
fails the audit with invalid input: refresh the bounded copy, review its relevance
and obtain a new native fingerprint and receipt. Do not patch an old fingerprint.
Version labels and capture dates remain operator attestations; matching bytes do
not verify that the publisher has not released a newer document.

Changes to content, context, evidence annotations/captures, rules or native engine
invalidate affected native receipts. Receipt annotation changes require a new
report because the receipt digest changes. Audit-code changes alter its separate
hash, not the production engine fingerprint. Required source gates remain intact,
including sources whose linked rules are currently inactive.

## Responsibilities and Limits

The editorial method owns research, prose, passage-level judgment and correction.
This tool owns neutral parsing, binding and trace presentation. A consuming adapter
owns explicit tool selection and distribution integrity. The project owns private
proof, identity, route/offer approval and final decisions.

Synthetic tests verify those software boundaries. Known-defect judgments made by
an agent that created or saw the labels are development rehearsals, not blind
evaluation, calibrated accuracy or SEO evidence. Keep real content outside this
public repository and reserve new cases for later human adjudication.
