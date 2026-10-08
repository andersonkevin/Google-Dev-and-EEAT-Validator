# Changelog

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
