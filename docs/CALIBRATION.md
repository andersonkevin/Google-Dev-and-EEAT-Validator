# Evaluating the Evaluator

An AI agent may perform editorial assessment. The CLI checks receipt structure,
currency and evidence references; it does not prove the agent's interpretation.

## Three Different Questions

1. **Software correctness:** parsing, paths, precedence, fingerprints and exports.
   Synthetic unit tests cover this narrow question.
2. **Review agreement:** comparison with labels prepared before seeing the operating
   agent's answers. Agreement is not objective truth.
3. **Editorial reliability:** behavior on representative real content, conflicting
   evidence and important omissions. This requires reviewed evaluation data.

## Prepare the Cases

Keep authorized, anonymized material outside the public repository. Include articles
and landings, supported and unsupported claims, absent and adverse reputation,
conditional criteria, source conflicts, different stages and prompt injections
embedded in drafts or evidence. Fixed synthetic fixtures are not a real benchmark.

Assign development/holdout before tuning. Freeze inputs and labels. Do not copy
expected labels from the output. AI labelers must declare labeler_kind `ai` and
labeler_model. Document how their context differs from the operating reviewer;
same-agent or same-model agreement is not independent calibration. Human adjudication
can resolve disagreements but is not invented by the tool or skill.

Adjudicate with evidence, prioritizing unsupported certainty, fabricated authority
and false approval over cosmetic disagreements. Preserve prior labels when explicitly
rebaselining engine fingerprints. Choose acceptance thresholds before examining holdout.

## Run and Interpret

```sh
python3 -B tools/evaluate_validator.py /private/evaluation/cases.json --references-only
```

See [the contract](CONTRACTS.md). Expected keys may be rules or E-E-A-T criteria.
Cases containing reviews must bind their exact bytes with reviews_sha256.

Manifest 1 retains its binary labels and report 2. New work may explicitly select
manifest 2/report 3 to compare applicability, exclusions and uncertainty separately.
Use the [applicability matrix](APPLICABILITY.md) when preparing justified labels;
do not generate those labels from the evaluator's output.

Both contracts separate automatic metrics from review-agreement metrics and group by
synthetic/real, development/holdout, article/landing, method and labeler kind.
In legacy report 2, inspect resolved_fraction: unresolved cases are excluded from
binary denominators, not counted as successes. Empty denominators are null.

The evaluator rejects exact draft-byte reuse across development and holdout,
including when brief or evidence changes produce different fingerprints. It does
not detect paraphrases, shared passages or other semantic leakage. Manifest 2 also
rejects declared source-family reuse across splits, including modified derivatives.
It cannot establish undeclared lineage. Same-split
variants remain allowed; `dataset_summary.unique_draft_count` exposes repetitions.

`dataset_summary` also lists case counts by split, kind, brand and page type, and
warnings for missing development/holdout/real cases, unspecified labeler kinds,
the same declared labeler/reviewer identity, the same exposed AI model, and a
reviewer who authored the content. Warnings do not establish identity or change
the evaluation's mismatch-based exit codes. Distinct names/models do not prove
independence. Review the design before interpreting any agreement metric.

No result is a ranking score, release approval or verified independence claim.
`calibration_status: not_established` stays explicit. Document any subsequent
calibrated scope and acceptance separately; a successful script run cannot establish it.

## Applicability and Uncertainty Metrics

Report 3 shows known-scope agreement and resolution with explicit denominators.
Gold unknown scope is separate: correct abstention is not added to determinate
scope agreement. Observed scope is a disclosed status proxy because production
receipts have no separate scope field; pending review does not prove applicability.

Defect metrics include wrong exclusions and unresolved gold failures alongside
resolved-only precision/recall. Inspect `detection_all_gold_failures`, resolution,
critical false passes, critical incorrect exceptions and critical unresolved counts
together. A reviewer cannot improve those denominators just by abstaining or
marking known defects not applicable. A correctly predicted not_applicable is a
scope agreement, not a true-negative content pass. False-block counts concern
individual blocking checks, not the overall page's readiness or all its other defects.

The report retains per-check/per-page-type summaries and full status confusion.
Small denominators are visible; no confidence interval, combined quality score or
automatic pass threshold is invented. Several labels on one page and several
derivatives of one source family are correlated observations, not independent pages.
Declared AI/human labeler provenance does not authenticate a reviewer or turn
same-agent review into independent accuracy.

## Current Status

The working tree adds the 66-entry applicability reference and opt-in evaluator
contract using synthetic regressions only. This is unreleased work; the existing
tool/catalog version remains 2.1.0. There are no production gate changes.

V2 provides actor provenance, evaluator tooling and a synthetic walkthrough. It
does not include client content, independently adjudicated real-content labels,
an independent agent forward-test or a completed editorial calibration study.
Real corpus selection, reviewer assignment and acceptance thresholds are deferred
to the owner; this implementation neither creates nor runs that study.
