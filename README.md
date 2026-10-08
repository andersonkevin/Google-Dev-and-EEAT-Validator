# Google-Dev-and-EEAT-Validator

An unofficial, local-first Python CLI for evidence-led review of HTML articles
and landing pages, informed by Google Search Central, developer writing guidance
and the E-E-A-T framework.

**Independent project. Not affiliated with, endorsed by, or certified by Google.**
This is an editorial review tool, not Google's ranking algorithm or an E-E-A-T
score. It does not write content, authenticate experts or publish to a CMS.

Version **1.0.0**. MIT-licensed original software. Python **3.10+**, standard
library only. No install, API key, account, network connection or model required.

## Quick Start

From the repository directory:

```sh
python3 -B tools/validate_draft.py examples/bundle.json --references-only
```

The synthetic example returns JSON and **exit code 2: review_required**. This is
expected, not a crash. It has no fabricated human approvals. The command does
not write files, contact Google or read any external workspace.

`--references-only` uses linked rule references without a local source archive.
It explicitly reports `source_verification: references_only_not_verified` and
**cannot produce ready_for_owner_review**, even with completed editorial receipts.
Static failures still block. This mode does not bypass draft or evidence checks.

For provenance-bound operation with a separately prepared, lawful local source
archive, use `--snapshot PATH` instead. See [the input contract](docs/CONTRACTS.md).
No archive, private source IDs, raw guides or automatic downloader is bundled.

## What It Does

- Applies 46 checks: 17 mechanical checks and 29 contextual, rendered or live-evidence reviews.
- Distinguishes article/landing profiles and draft/staging/live stages.
- Checks HTML structure, links, naming markup, image alt presence and JSON syntax.
- Checks claim-ledger references and evidence provenance fields.
- Checks page metadata, canonical and declared indexing intent where applicable.
- Preserves explicit failures, records scope conflicts and rejects stale reviews.
- Imports local browser/HTTP observation receipts without collecting them itself.
- Offers independent-label evaluation and source-coverage inspection.
- Includes a research map of 20 contextual E-E-A-T criteria, not 20 extra automatic rules.

## What It Does Not Establish

The tool does not establish factual truth, real-world expertise, independent
reputation, originality, WCAG conformance, link reachability, rich-result eligibility
or Google ranking outcomes. Evidence attachment is not proof that a claim is true.
HTML parsing is not browser rendering. Human review is central, not optional.
The source/rule mapping has not completed independent real-content calibration.

## Typical Workflow

```text
Brief and evidence -> draft HTML -> static checks -> human source/content review
-> corrections -> rendered/live evidence where needed -> owner approval
```

See [WORKFLOW.md](docs/WORKFLOW.md) for responsibilities and
[EEAT.md](docs/EEAT.md) for the research mapping and its gaps.
The writing agent or author must not manufacture approval receipts for its own claims.

## Inputs And Results

Start with `examples/bundle.json`. Keep real work in a private directory outside
the repository. References to draft and evidence files are relative to that bundle.
The parser accepts HTML, not Markdown; use your existing renderer to prepare HTML.

| Exit | State | Meaning |
| --- | --- | --- |
| 0 | ready_for_owner_review | Applicable checks satisfied for the named stage; not permission to publish |
| 1 | invalid_input | Invalid input, path, schema or integrity |
| 2 | review_required | Outstanding review, missing verification or warning |
| 3 | blocked | Error or critical finding |

For a **new**, nonexistent output directory whose parent exists:

```sh
python3 -B tools/validate_draft.py examples/bundle.json --references-only --output review-output --execute
```

Use a private output location in real work. Exports contain `report.json`,
`report.txt` and `COMPLETE.json`. They may contain sensitive content. No overwrite
is permitted. An interrupted export without a valid completion receipt is incomplete.

## Tests

```sh
python3 -B -m unittest discover -s tests -v
```

Tests use temporary synthetic data. No source archive or external workspace is
required. No CI service, telemetry or background job is configured.

## Project Shape

- `tools/`: validator, rule catalog, independent-label evaluator and safe reader.
- `references/`: original rule interpretations and URL-linked E-E-A-T research map.
- `examples/`: clearly labeled synthetic input only.
- `tests/`: behavior, safety and public-distribution checks.
- `docs/`: workflow, contracts and E-E-A-T explanation.

Publish this repository as a **developer tool / CLI**. The workflow is documentation,
the reports are artifacts, and an optional agent skill could call the CLI later.
No skill installer or autonomous writing workflow is part of this release.

Suggested repository description:

> Unofficial, local-first HTML editorial review CLI with evidence-bound checks and human E-E-A-T review. No ranking scores or automatic publishing.

## License And References

See [LICENSE](LICENSE) for MIT terms covering original software and documentation,
and [NOTICE.md](NOTICE.md) for third-party attribution and boundaries. Google's
documents, PDFs, trademarks and logos are not relicensed under MIT or included.
Rules are local interpretations with official source links, not Google requirements
expressed as an official executable specification.
