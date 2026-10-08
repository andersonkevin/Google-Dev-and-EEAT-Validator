# Agent-Operated Review

## Tool, Skill and Artifacts

- **Tool:** Python CLI for mechanical findings and evidence/receipt integrity.
- **Skill:** `skills/google-dev-eeat-review/SKILL.md` guides the operating AI agent's contextual assessment.
- **Artifacts:** evidence notes, receipts and reports preserve inspected material and decisions.
- **Owner:** a person makes the publication decision. The agent's assessment is not that approval.

Use the skill from the complete checkout. Its relative links and CLI require the
adjacent repository; it is not a standalone folder installer. No global assistant
settings are changed. A file-capable assistant can read the skill directly.

Suggested invocation:

> Use the google-dev-eeat-review skill in this checkout to review my HTML and evidence.
> Act as the contextual evaluator, disclose whether you wrote the draft, record
> source-backed decisions, and return findings without publishing.

The CLI never calls a model. The agent uses existing tools and permissions. A cloud
agent may transmit loaded content under its provider settings; local CLI operation
does not guarantee local inference. Invoking a skill does not authorize private
uploads, credential access or additional external actions.

## Practical Sequence

1. Read the brief, whole draft and evidence; confirm the stage and reader.
2. Inspect sources with authorized tools. Save concise capture notes, not full guides,
   and register them as bundle evidence before obtaining the final fingerprint.
3. Run validation, then `--review-template` for an unresolved receipt scaffold.
4. Fill actor provenance and criterion-specific decisions with inspected evidence.
   Save the receipt with authorized file tools in the private workspace.
5. Rerun with `--reviews`. Correct supported defects when authorized, then reevaluate.
6. Hand off findings and unresolved items. Owner approval stays outside the receipt.

`--review-template` prints JSON and exits 0 for a successful scaffold; it writes
nothing and grants no passes. Blank identity/date/reason fields are intentionally
incomplete. Unavailable facts or sources may remain `needs_review`, with reasons.

References-only mode no longer needs the private archive to reach
`ready_for_owner_review`: all required rule, criterion and source reviews must be
resolved with current evidence. Source review remains an operator attestation,
not verified Google authenticity. The archive-verification field stays unverified.
Source conflicts block; inaccessible sources remain unresolved.

## Synthetic Correction Walkthrough

```sh
python3 -B examples/review_walkthrough.py
```

The script runs in an automatically cleaned temporary directory. It introduces
300 records against evidence of three, applies a synthetic failure receipt, corrects
the claim, rejects the stale receipt and reassesses the narrow correction. Other
criteria and source reviews remain unfinished, so the final state is
`review_required`. No model or research service is called.

This demonstrates the protocol, not agent accuracy. For a real agent review,
supply an authorized draft/evidence bundle and use the skill.
