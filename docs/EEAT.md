# E-E-A-T Research Mapping

The structured map is `references/eeat-map.json`. It links 20 local review criteria
to official source URLs, current rule IDs, evidence, exceptions and implementation
gaps. It contains no retained source text or private snapshot identifiers.

| Area | Criteria | Main question |
| --- | --- | --- |
| Context | 2 | What is the reader task and the consequence of an error? |
| Experience | 3 | Is claimed involvement authentic, method explained and scope honest? |
| Expertise | 3 | Is knowledge relevant, explanation useful and factual support accurate? |
| Authority | 3 | Is recognition relevant and independent, and is missing reputation distinguished from adverse evidence? |
| Trust | 6 | Are identity, claims, numbers, relationships, updates, representations and accountability dependable? |
| Supporting quality | 3 | Does the page add useful content, describe relevant production context and work for its reader? |

Context and supporting quality are not additional Google E-E-A-T dimensions.
The map is a research artifact, not a new runtime score or 20 extra enforced rules.
In v1, eight criteria had existing broad manual coverage, ten were partial and two
lacked dedicated coverage. The map's coverage/gap fields preserve that baseline.
V2 requires an explicit, evidenced AI or human decision for every criterion;
it does not turn their interpretation into an automatic check. Broad-rule passes
cannot fill those decisions. Missing decisions remain needs_review.

Google identifies trust as central and describes context-dependent contributions
from experience, expertise and authority. It does not define a single E-E-A-T
ranking score. [Google's explanation](https://developers.google.com/search/docs/fundamentals/creating-helpful-content#eat)

## Evidence, Not Surface Signals

- Original project/test records can support actual experience, not independent reputation.
- A relevant source can support a claim without proving the author's own experience.
- A biography is an identity claim, not automatic verification of expertise.
- A link, citation count or domain score is not proof of independent authority.
- Valid JSON-LD does not make the represented identity or outcome true.
- Missing recognition for a new creator is different from credible adverse evidence.

Reviews require contextual interpretation by the operating agent or human. Unknown support for a material claim should
remain unresolved or lead to narrower wording, not a fabricated pass. Unknown
public reputation should not automatically block a useful, substantiated contribution.

## Profile Differences

Articles are assessed against their informational task and appropriate attribution.
Landings are assessed against the offer, organization, scope and intended action.
A landing does not universally need an individual byline, sales CTA or minimum length.
Review/testing criteria apply when the content actually makes review or test claims.

## Remaining Work

TRUST-06 (accountability/user protection) and QUALITY-02 (production transparency)
now have explicit criterion-level review gates, as do the other 18 entries.
Their applicability remains contextual: no universal contact form, individual byline
or AI disclosure is imposed. This is local review policy, not a Google algorithm.

Actor provenance, evidence IDs and current fingerprints make decisions auditable;
they do not verify the evidence's meaning or the reviewer identity. Independent
labeling, real-content calibration and richer semantic evidence relationships remain
open. See [CALIBRATION.md](CALIBRATION.md).

This mapping does not establish Google's assessment of any page. Read the linked
source in context and check its current guidance before changing policy.
