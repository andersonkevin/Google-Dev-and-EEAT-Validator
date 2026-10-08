# Agent-Operated, Human-Supervised Editorial Workflow

## 1. Brief

Identify the reader, market, purpose, intent, responsible entity and next action.
An intentional absence of a commercial CTA is valid. Declare topic risk, update
intent and video-search claims without treating those declarations as proof.

## 2. Evidence Before Copy

Collect relevant references, original work and appropriate creator information.
Distinguish your own experience from third-party research. Record evidence origin,
capture date and applicable conditions. Do not invent missing proof.

## 3. Draft And Claim Ledger

Produce HTML and a bundle using the synthetic example's structure. Match material
claims to evidence IDs. Empty claims are allowed but still require a reviewer to
confirm that no material assertion was omitted.

## 4. Mechanical Review

Run the validator in explicit references-only or local-snapshot mode. Fix mechanical
failures before asking an editor to repeat basic checks. A reference ID does not
establish that its source substantiates the claim.

## 5. Editorial Review

The operating AI agent evaluates accuracy, experience, credentials, reputation,
relationships, usefulness and context using the supplied evidence and authorized
research tools. A human reviewer can use the same protocol. Record actor kind,
model/run for AI, relationship to the author, reasons and local evidence references.
An agent that wrote the draft must disclose that, not impersonate an independent
reviewer. Decisions assess content; they are never publication approvals.

Evaluate all 20 contextual criteria separately and review the source documents in
context. Broad-rule passes do not fill criteria automatically. Generate an unresolved
receipt with --review-template, then fill only decisions supported by inspected
evidence. Unsupported claims or inaccessible sources remain unresolved.

## 6. Rendered And Live Evidence

Draft checks do not establish browser behavior or live accessibility/indexing.
For later stages, supply separately captured observations with source hashes.
No collection or publishing tool is invoked by this CLI.

## 7. Approval

Changed draft, evidence, brief, rules or engine invalidate earlier review receipts.
Correct, rerun and review the current version. Owner approval remains separate.
References-only mode supports explicit source-review attestations without bundling
Google's documents. It does not claim archive verification or source authenticity.

## Extension Points

Use the [review skill](../skills/google-dev-eeat-review/SKILL.md) to operate the tool
from an existing assistant. It does not install an agent runtime or call a model.
See [AGENT-REVIEW.md](AGENT-REVIEW.md) for operation and the synthetic example.
The owner remains the publication gate; no autonomous publishing is implemented.
