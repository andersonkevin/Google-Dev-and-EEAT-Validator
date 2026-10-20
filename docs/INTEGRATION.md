# Integrating the Validator into Project Workflows

Use the validator as an independent local review boundary for an editorial
workflow, a design system or a marketing workspace. The project owns its content,
business context and evidence. This repository owns the neutral checks, criterion
map and receipt contracts. No specific CMS, brand or orchestration framework is
required, and this guide does not install an adapter or a background process.

## What the Tool Contributes

The CLI checks supported markup, evidence references, decision integrity and
readiness. The operating reviewer evaluates meaning and source support. The
owner decides whether the result is sufficient for publication.

The reference catalog contains interpretations and source links, not a complete,
automatically updated research library. The tool cannot establish product facts,
first-hand experience or reputation from those links. Research and supplied
project evidence remain necessary. The [review plan](CONTRACTS.md#review-plan)
groups the exact cited sections by document so a reviewer can read a source once
for several relevant questions while keeping the decisions separate.

The map is not independently calibrated against real editorial judgments.
Software tests verify the contract and regressions; they do not measure semantic
accuracy. See the [calibration protocol](CALIBRATION.md).

## Minimal Adapter Contract

Record the selected checkout's version, commit and local-change state. Version
alone does not identify an unreleased working tree. Retain the report fingerprint
and exact receipt/report hashes for the actual run. Verify the tool and its
contracts before invocation; do not silently substitute another version.

```sh
python3 -B tools/describe.py
```

This read-only discovery command needs no project input. For 2.1.0, the tool and
catalog versions are 2.1.0 and the unchanged criterion mapping is 2.0.0.
Compare the explicit schemas below rather than assuming all version strings
must match. An exact 2.0.0 consumer pin is not silently compatible with 2.1.0.
Consumers may use a complete, hash-verified distribution stored locally; keep it
unchanged and update it from a reviewed upstream release rather than forking rules.

| Boundary | Contract |
| --- | --- |
| Input | Bundle schema 1; HTML article or landing; explicit draft, staging or live stage |
| Private evidence | Project-owned bundle directory; relative nonsymlink file references |
| Contextual decisions | Review receipt schema 2; actor, current fingerprint and evidence IDs |
| Rendered/live evidence | Observation schema 1; actual captures and current content/context hashes |
| Full result | Report schema 2; separate rule, criterion and source findings |
| Optional work queue | `--review-plan`, schema 1, `kind: review_plan`; advisory, not a receipt |
| Exit handling | 0 owner review ready; 1 invalid input; 2 review required; 3 blocked |
| Export | Explicit new output directory plus `--execute`; verify `COMPLETE.json` hashes |

Treat exit codes 2 and 3 as review outcomes, not process crashes. Parse the JSON
and preserve its state. Invalid input is an operational failure; do not turn it
into a content verdict. Retain the full report for evidence: the plan is a focused
view and omits resolved findings and some provenance fields.

Adapters should invoke the CLI with an argument list, not a shell command built
from untrusted content. Keep bundles and receipts outside this public repository.
Do not import the rule catalog into each project or translate pending work into
a local "pass." No report or exit code grants publication permission.

## Operator Sequence

Commands run from the selected tool checkout. Paths below are placeholders for
the authorized private review directory. The CLI does not create these inputs.

1. Prepare the HTML, brief, material claims and available evidence.
2. Obtain the report and source plan. Both commands are read-only:

   ```sh
   python3 -B tools/validate_draft.py /private/review/bundle.json --references-only
   python3 -B tools/validate_draft.py /private/review/bundle.json --references-only --review-plan
   ```

3. Correct mechanical defects within the authorized scope. Review the source
   sections and collect missing evidence. A source with no pending rule IDs can
   still be a required source gate; the plan never waives it.
4. Add actual capture notes and observations to the bundle before generating
   the final fingerprint and unresolved receipt scaffold:

   ```sh
   python3 -B tools/validate_draft.py /private/review/bundle.json --references-only --review-template
   ```

5. Evaluate each applicable rule and all contextual criteria. Record specific
   reasons, evidence and actor provenance. Disclose `same_agent` where applicable.
6. Validate the receipt and inspect remaining work:

   ```sh
   python3 -B tools/validate_draft.py /private/review/bundle.json --references-only --reviews /private/review/receipt.json
   python3 -B tools/validate_draft.py /private/review/bundle.json --references-only --reviews /private/review/receipt.json --review-plan
   ```

7. Export only to an authorized, nonexistent directory with an existing parent:

   ```sh
   python3 -B tools/validate_draft.py /private/review/bundle.json --references-only --reviews /private/review/receipt.json --output /private/review/review-001 --execute
   ```

Pass the full report, original receipt, completion hashes and unresolved work to
the owner. Preserve earlier records after corrections. Changes to content,
evidence, rules, engine or other fingerprint inputs require fresh assessment;
never replace only an old receipt's fingerprint.

## Reusing Research Across Projects

Source capture notes may be reusable when the reviewer verifies their currency,
scope and relevance to the current rule. Keep the actual URL, access date, section,
observation and limitations. Include the supporting file in each authorized
private bundle and evaluate its use in a new receipt. A shared source does not
transfer a content decision between projects.

Keep product claims, authorship, demonstrations and reputation evidence specific
to the responsible project. Do not copy one client's evidence into another's
bundle. There is no automatic freshness window, remote fetcher, shared evidence
store or cross-project approval cache.

Use an existing lawful local source snapshot when appropriate; replace
`--references-only` with `--snapshot PATH`. Hash verification establishes file
integrity, not authenticity, currency or correct interpretation. Inaccessible
sources remain unresolved unless sufficient actual evidence is supplied and
reviewed under the [receipt contract](CONTRACTS.md).

## Interactive Pages

The static link-name check excludes links in markup with an HTML `hidden`
attribute on the link or an ancestor. It reports the excluded count. This avoids
treating an inactive product inspector as an exposed unnamed link.

Review the revealed state, keyboard behavior and CSS overrides with browser
evidence. An unnamed link exposed after activation still fails the static check
on that state. `aria-hidden` alone does not excuse a focusable unnamed link;
the existing explicitly decorative, `tabindex="-1"` exception remains narrow.
Link destination syntax and fragment checks still inspect HTML-hidden links.

These are static scope boundaries, not complete accessibility conformance.
The distinction follows the [HTML hidden attribute](https://html.spec.whatwg.org/multipage/interaction.html#the-hidden-attribute)
and [ARIA tree-exclusion guidance](https://www.w3.org/TR/wai-aria-1.2/#tree_exclusion).

## Deferred Work

- Independent, labeled calibration across real page types and projects.
- An explicitly selected and validated adapter in each consuming system.
- Broader interactive accessibility checks and source-freshness tooling.

No model calls, CMS integration, network behavior, source downloads or autonomous
workflow execution are introduced by this interface.
