# Applicability Before Verdict

The [matrix](../references/applicability-matrix.json) covers all **46 rules and
20 contextual criteria**. It is a versioned review reference, not an autonomous
scope classifier or a change to production validation. No corpus, reviewers or
real-content calibration are included.

## What an Entry Means

`tools/applicability.py` resolves the compact reference against the existing
catalog and E-E-A-T map. Each resolved entry has its purpose/title, sources,
basis class, current gate, stages, evidence, exception, automation limit,
article/landing interpretation and local failure severity. Criterion entries
also retain pass, fail and unknown conditions and name possible contextual
exclusions. Shared page/stage profiles are in the matrix's `profiles` object.
An exclusion requires a case-specific explanation and evidence, not just a
sentence copied from this reference.

The source class and local enforcement are distinct:

| Basis | Interpretation |
| --- | --- |
| Technical requirement | Relevant eligibility or access condition; an offline check does not prove live availability or indexing |
| Feature policy/guidance | Conditional on the actual feature or claim; no universal obligation to add schema or video |
| Quality/rater framework | Contextual guidance for evidence-led assessment, not Google's executable ranking algorithm |
| Editorial guidance | Audience-dependent writing/accessibility guidance; developer house style is not mandatory marketing voice |
| Local implementation policy | This tool's parsing, brief, evidence and severity conventions; not literal Google requirements |

All error/critical classifications and criterion blocking decisions are **local
review policy**, regardless of source class. The matrix adds no term quotas,
word counts, graphic counts, FAQ requirement, universal byline or blanket AI label.
The original criterion map's historical coverage/gap fields remain unchanged.

## Scope Boundaries

| Context | Decision |
| --- | --- |
| Article vs landing | Assess the informational task separately from offer, audience fit and organizational proof. Do not require both to follow one outline. |
| Educational landing | An intentional absence of contact/lead capture can satisfy intent; do not invent a commercial offer or CTA. |
| Identity | Honest organizational responsibility can be appropriate; an author box alone never verifies competence. |
| Reputation | No public recognition is not adverse reputation. Record research limitations without inventing recognition or declaring misconduct. |
| Risk | `ymyl: false` does not waive RATER-003 or CONTEXT-02; every page needs risk assessment. |
| Schema | JSON-LD syntax and semantic truth are separate; microdata/RDFa can still trigger schema review. |
| Video | Supporting embeds do not automatically claim watch-page eligibility. Check undeclared promises rather than trusting a flag blindly. |
| Hidden links | ANCHOR-003 excludes HTML-hidden link names only; href/fragment checks remain, and revealed states need actual review. |
| Draft | Final metadata and rendered/live conditions are not inferred. Contextual criteria still need explicit decisions or justified exceptions. |
| Staging | Metadata/rendered checks apply; respect intentional staging restrictions. Live access rules remain out of stage. |
| Live | Missing access observations mean `not_tested`, never an implicit pass. Availability does not establish indexing. |

An explicit supported rule failure survives inferred stage/feature exclusion in
the current engine. The evaluator exposes `scope_conflict`; it does not erase
the failure. A production criterion failure blocks owner readiness. Neither the
matrix nor evaluation labels can override mechanical failures or source gates.

## Using the Reference

1. Establish page purpose, stage, claims, feature presence and available evidence.
2. Read the entry and its actual linked source in context. Project voice remains
   relevant; do not apply developer-documentation conventions indiscriminately.
3. Decide applicable, evidenced exclusion or unresolved scope. Missing evidence
   for an in-scope obligation is not a reason to exclude it.
4. Assess the content separately. Record the reason, evidence and unresolved
   conditions in the current review receipt; no decision is generated here.
5. Use frozen expected labels only when evaluating reviewer agreement. See the
   [evaluation contract](CONTRACTS.md#applicability-aware-evaluation) and
   [calibration limits](CALIBRATION.md).

The resolved matrix is available to local Python callers through
`applicability_matrix()`; no new CLI, model call, network fetcher or integration
is added. The evaluator uses its IDs/classification for reporting, not to generate
gold labels. New evaluation reports bind the matrix hash and evaluation-code hash.
Production bundle/report/receipt schemas are unchanged. The matrix/evaluation code
does not enter native fingerprints, but v2.2.0 version/catalog metadata does change
them. Earlier receipts require fresh assessment; see [integration](INTEGRATION.md).

## Validation and Deferred Decisions

Synthetic tests reconcile all 66 IDs with the catalog/map, compare actual stage
gates, preserve contextual evidence and test exclusions, uncertainty, failure
precedence, leakage, stale receipts, paths and no-write behavior. They establish
software behavior only.

Selecting real cases, reviewing their rights/privacy, assigning reviewers,
adjudicating disagreements and accepting calibrated scope are deferred. Future
changes to production applicability or severity require a separate evidenced
decision; this reference does not quietly implement them.
