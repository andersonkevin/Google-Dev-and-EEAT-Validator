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

Results separate automatic metrics from review-agreement metrics and group by
synthetic/real, development/holdout, article/landing, method and labeler kind.
Inspect resolved_fraction: unresolved cases are excluded from binary denominators,
not counted as successes. Empty denominators are null.

No result is a ranking score, release approval or verified independence claim.
`calibration_status: not_established` stays explicit. Document any subsequent
calibrated scope and acceptance separately; a successful script run cannot establish it.

## Current Status

V2 provides actor provenance, evaluator tooling and a synthetic walkthrough. It
does not include client content, independently adjudicated real-content labels,
an independent agent forward-test or a completed editorial calibration study.
