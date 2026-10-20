# Changelog

## Unreleased

- Add a read-only editorial trace audit with compatible per-source/claim and
  passage-level decision annotations, explicit assurance layers and role-based
  next actions. Preserve native reports, gates and exit codes; metadata coverage
  is not factual verification. Optional shared-capture checks reject changed bytes
  without inheriting source attestations or article judgments.
- Add a versioned applicability reference for all 46 rules and 20 contextual
  criteria, resolving sources, stage gates, evidence, exceptions, profile differences
  and automation limits without changing production validation policy.
- Add opt-in evaluation manifest 2/report 3: separate applicability, verdicts and
  uncertainty; expose wrong exclusions, check-level false blocks, critical escapes,
  unresolved failures, full status confusion and per-check/page-type counts.
- Bind new evaluation reports to matrix/code hashes and retain original bundle,
  receipt and fingerprint integrity; reject stale supplied receipts in manifest 2.
- Require declared source-family identity for manifest 2 and reject families or
  exact draft bytes crossing development/holdout; no semantic lineage detector.
- Preserve manifest 1/report 2, production bundle/report/receipt contracts, current
  gate severity and production validation fingerprints. Discovery advertises both
  evaluation pairs without replacing legacy scalar fields.
- Add temporary synthetic regressions and document uncertainty/proxy limitations.

No real corpus, reviewer roster, calibration result, release approval, dependencies,
network/model calls or project adapter is added. Tool/catalog version stays 2.1.0
until a separately approved release; this section describes local unreleased work.

Implementation checks: 179 synthetic tests, the synthetic correction walkthrough
and the 43-file distribution audit passed. These are software checks, not editorial
calibration or human acceptance.

Subsequent editorial-trace checkpoint: 195 synthetic tests, the correction
walkthrough and the 46-file source audit passed. Production engine/catalog/map
files remain unchanged. The trace audit adds no automatic semantic judgment.

## 2.1.0 - 2026-10-20

- Fix `ANCHOR-003` false positives for links in HTML-hidden interactive states;
  disclose excluded links and retain checks on exposed or ARIA-hidden focusable links.
- Add read-only `--review-plan` output with grouped source sections, pending rules,
  contextual evidence needs and unchanged readiness/receipt/source gates.
- Document project-neutral integration and evidence-reuse boundaries.
- Add `tools/describe.py` for machine-readable versions and integration contracts.
- Reject identical draft bytes across evaluation development/holdout splits and
  disclose dataset coverage, unspecified labelers and shared reviewer/model provenance.
- Add synthetic regressions for hidden/revealed states, planning, stale reviews,
  source conflicts, CLI exit codes and no-write/path-safety behavior.

No new dependencies, network calls, model integrations or automatic decisions.
Existing bundle/report/receipt versions remain unchanged; plan schema is 1.
Engine changes invalidate earlier review fingerprints and require reassessment.
The criterion mapping remains 2.0.0; the tool and rule catalog are 2.1.0.
Existing consumers with exact 2.0.0 pins must opt into 2.1.0 explicitly.
No independent calibration claim is made.

The initial optimization checkpoint on 2026-10-20 passed 136 tests, the synthetic
walkthrough and the 36-file source audit before the contract-discovery and
evaluation-design additions. A read-only private
interactive-page regression changed only `ANCHOR-003` among mechanical results,
preserved previous artifacts and rejected the earlier receipt as stale. No
private content is included in the distribution.

Final local release checks: 144 tests, the synthetic review walkthrough and the
38-file source audit passed. The consuming editorial checker also passed its
83-test suite with this engine selected explicitly; all inputs were synthetic.
These checks do not establish independent editorial calibration.

## 2.0.0 - 2026-10-08

Agent-operated editorial review, with human publication ownership.

- Repository-local skill for AI-led evidence inspection and contextual assessment.
- Review schema 2 with actor kind, model/run, author relationship and purpose.
- Separate, evidence-referenced decisions for all 20 contextual E-E-A-T criteria.
- Source-review attestations allow references-only owner-readiness without a private archive.
- Unresolved receipt scaffolds via --review-template; no automatic approvals.
- Report schema 2 preserves criterion findings, actor provenance and receipt digest.
- Evaluations distinguish mechanical outcomes from AI/human review agreement,
  preserve unresolved coverage, and require hashes for imported review receipts.
- Synthetic correction walkthrough, migration notes and calibration protocol.
- CI and release packaging validate software behavior, not model judgment.

Breaking: v1 review receipts require fresh assessment; report consumers must handle
schema 2 and the editorial method label (formerly human). Bundle/observation schema
remains 1. The tool still performs no model calls, live collection or publishing.
Independent agent forward-testing and real-content calibration are not claimed.

## 1.0.0 - 2026-10-08

Initial standalone assisted-review release.

- 46 local-policy checks and article/landing review profiles.
- Evidence-bound human decisions and local observation import.
- Explicit references-only mode with no source-verified readiness claim.
- Optional local snapshot integrity verification and coverage triage.
- Independent-label evaluation tooling and 20-criterion E-E-A-T research map.
- Gated report exports, completion receipts and synthetic safety tests.
- No source archives, private workspace records, model calls or publication actions.

Independent semantic calibration, specialized schema/cross-page checks and
criterion-level E-E-A-T decisions remain future work. This release is not a
Google certification, autonomous content approval or ranking predictor.
