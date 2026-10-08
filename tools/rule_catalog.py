"""Versioned local review policy. Severity is ours, not a Google ranking claim."""
import json
from pathlib import Path

VERSION = "1.0.0"
SEARCH = "https://developers.google.com/search/docs/"
STYLE = "https://developers.google.com/style/"

PROFILES = {
    "article": {
        "QUALITY-001": "Identify the answer, original analysis or demonstrated experience that serves the article's reader task.",
        "TRUST-001": "Verify the creator and credentials where readers would expect attribution; do not invent expertise or require an author box universally.",
        "INTENT-001": "Confirm the reader can complete the informational task. A commercial CTA is optional; document intentional absence of a next action.",
    },
    "landing": {
        "QUALITY-001": "Verify the offer, intended audience, scope and supporting proof. Do not require article length, a FAQ or a named individual byline.",
        "TRUST-001": "Verify organizational responsibility and any capability, testimonial or outcome claims against evidence.",
        "INTENT-001": "Verify that the intended action follows from the offer and audience. An educational landing may intentionally have no contact CTA.",
    },
}


def profile_prompt(rule, page_type):
    return PROFILES[page_type].get(rule["id"], rule.get("evidence", rule["title"]))

FIXES = {
    "INPUT-001": "Complete the named brief fields; use explicit booleans for scope declarations.",
    "HTML-001": "Include the intended main title as a nonempty h1 in the review HTML.",
    "HTML-002": "Remove the empty heading or give it a descriptive label.",
    "HTML-003": "Restore the logical heading sequence; control visual size through CSS.",
    "HTML-004": "Supply the actual readable draft, not scripts or an empty template.",
    "IMAGE-001": "Add alt text appropriate to context, or alt=\"\" for decorative media.",
    "ANCHOR-001": "Use a valid href for navigation; use a button for actions instead of fake links.",
    "ANCHOR-002": "Correct the fragment reference or add the intended target ID.",
    "ANCHOR-003": "Provide descriptive link text or an appropriate accessible label.",
    "JSONLD-001": "Repair JSON syntax, duplicate keys, or root type; semantic review remains separate.",
    "META-001": "Provide one descriptive, nonempty title element in the page output.",
    "META-002": "Provide one accurate, nonempty meta description when preparing the page.",
    "META-003": "Confirm canonical intent in the brief and make the page canonical agree.",
    "ROBOTS-001": "Align meta directives with the explicitly declared stage intent; do not expose staging.",
    "CLAIM-001": "Match each ledger quote to the draft and attach existing evidence IDs.",
    "EVIDENCE-001": "Provide evidence title, origin, capture date, and a local evidence file.",
    "LANG-001": "Declare the document language on the html element in the page output.",
}

# id, title, source, method, applicability, severity
EXTRA = [
    ("INPUT-001", "Complete review brief", SEARCH + "fundamentals/creating-helpful-content#people-first", "auto", "always", "error"),
    ("HTML-001", "Nonempty main heading", STYLE + "headings#hierarchy-and-structure", "auto", "always", "error"),
    ("HTML-002", "Nonempty headings", STYLE + "headings#hierarchy-and-structure", "auto", "always", "error"),
    ("HTML-003", "Logical heading levels", STYLE + "headings#hierarchy-and-structure", "auto", "always", "warning"),
    ("HTML-004", "Readable text exists", SEARCH + "essentials/technical#indexable-content", "auto", "always", "error"),
    ("IMAGE-001", "Image alt attributes exist", STYLE + "images#alt-text", "auto", "images", "error"),
    ("ANCHOR-001", "Navigation anchors have usable hrefs", SEARCH + "crawling-indexing/links-crawlable#crawlable-links", "auto", "links", "error"),
    ("ANCHOR-002", "Local fragment targets exist", SEARCH + "crawling-indexing/links-crawlable#crawlable-links", "auto", "links", "error"),
    ("ANCHOR-003", "Links have accessible labels", STYLE + "accessibility#links", "auto", "links", "error"),
    ("JSONLD-001", "JSON-LD is valid JSON with object roots", SEARCH + "appearance/structured-data/sd-policies#format", "auto", "jsonld", "error"),
    ("META-001", "One nonempty page title", SEARCH + "appearance/title-link#page-titles", "auto", "page", "error"),
    ("META-002", "Nonempty meta description", SEARCH + "appearance/snippet#meta-descriptions", "auto", "page", "warning"),
    ("META-003", "Canonical matches declared intent", SEARCH + "crawling-indexing/canonicalization-troubleshooting#incorrect-canonical-elements", "auto", "page", "error"),
    ("ROBOTS-001", "Meta directives match indexing intent", SEARCH + "essentials/technical#indexable-content", "auto", "page", "error"),
    ("CLAIM-001", "Claim ledger references present text and evidence", SEARCH + "fundamentals/creating-helpful-content#expertise-questions", "auto", "always", "error"),
    ("EVIDENCE-001", "Evidence records have provenance", SEARCH + "fundamentals/creating-helpful-content#expertise-questions", "auto", "always", "error"),
    ("LANG-001", "Document language declared", STYLE + "accessibility#general-dos-and-donts", "auto", "page", "warning"),
    ("CLAIM-002", "Sources substantiate the claims in context", SEARCH + "fundamentals/creating-helpful-content#expertise-questions", "human", "always", "critical"),
    ("CLAIM-003", "Ledger covers material claims and numeric outcomes", SEARCH + "fundamentals/creating-helpful-content#expertise-questions", "human", "always", "error"),
    ("MEDIA-002", "Media rights and attribution verified", SEARCH + "essentials/spam-policies#copyright-removal-requests", "human", "media", "error"),
    ("MEDIA-003", "Diagrams and multimedia are accurate and useful", STYLE + "accessibility#images", "human", "media", "error"),
    ("META-004", "Title and description accurately represent the page", SEARCH + "appearance/title-link#inaccurate-title-elements", "human", "page", "error"),
    ("A11Y-001", "Rendered keyboard and visual review", STYLE + "accessibility#general-dos-and-donts", "rendered", "page", "error"),
    ("INTENT-001", "Next action serves the reader and brand brief", SEARCH + "fundamentals/creating-helpful-content#people-first", "human", "always", "error"),
]


def catalog():
    base = json.loads((Path(__file__).parents[1] / "references/validator-rules.json").read_text())
    rules = []
    for row in base:
        method = "live" if row["id"].startswith("ACCESS-") else "human"
        if row["id"] == "RATER-004":
            method = "rendered"
        applies = {"SCHEMA-001": "schema", "MEDIA-001": "video_claim", "STYLE-002": "images",
                   "RATER-003": "ymyl", "FRESHNESS-001": "updated"}.get(row["id"], "always")
        rules.append(row | {"title": row["id"] + ": " + row["evidence"], "method": method,
                            "applies": applies, "severity": "critical" if row["id"] == "TRUST-001" else "error",
                            "policy": "Local editorial gate informed by cited guidance"})
    for rid, title, source, method, applies, severity in EXTRA:
        rules.append({"id": rid, "title": title, "source": source, "method": method,
                      "applies": applies, "severity": severity,
                      "policy": "Local implementation policy; source does not prescribe this exact algorithm",
                      "remediation": FIXES.get(rid, "Complete the named contextual review with referenced evidence; correct unsupported content and rerun.")})
    for rule in rules:
        rule.update({
            "version": VERSION,
            "family": rule["id"].split("-")[0].lower(),
            "source_class": rule.get("class", "local_implementation_policy"),
            "reviewer_role": "qualified editor" if rule["id"] == "RATER-003" else "operator",
            "pass_condition": "No finding within the named static check" if rule["method"] == "auto" else "Current, evidenced reviewer decision for this rule and page context",
            "fail_condition": "A supported defect within the rule's scope; unsupported certainty requires review",
            "exceptions": rule.get("do_not_infer", "No inference beyond the named check; semantic and runtime evidence remain separate"),
        })
    return rules
