"""Read-only, local HTML draft review. Optional explicit, no-overwrite report export."""
import argparse
from collections import Counter
from datetime import date, datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urldefrag, urlsplit

from knowledge import safe_read
from rule_catalog import VERSION, catalog, criteria_map, profile_prompt

MAX_BYTES = 8 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(data):
    def reject(value):
        raise ValueError("Nonfinite JSON number: " + value)
    return json.loads(data, object_pairs_hook=unique, parse_constant=reject)


def read_input(root, relative):
    if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("Input path must remain relative to its bundle")
    candidate = root.resolve() / relative
    if any(p.is_symlink() for p in [candidate, *candidate.parents]) or not candidate.is_file():
        raise ValueError("Input must be a nonsymlink file")
    if candidate.stat().st_size > MAX_BYTES:
        raise ValueError("Input exceeds 8 MiB limit")
    data = safe_read(root, relative)
    if len(data) > MAX_BYTES:
        raise ValueError("Input exceeds 8 MiB limit")
    return data


class Page(HTMLParser):
    """Inventory markup only; never execute scripts or follow URLs."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.nodes, self.stack, self.parts = [], [], []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": {key: value or "" for key, value in attrs}, "text": "", "line": self.getpos()[0], "children": []}
        node["inert"] = tag == "template" or any(p.get("inert") for p in self.stack)
        node["hidden"] = "hidden" in node["attrs"] or node["attrs"].get("aria-hidden", "").lower() == "true" or any(p["hidden"] for p in self.stack)
        if self.stack:
            self.stack[-1]["children"].append(node)
        if not node["inert"]:
            self.nodes.append(node)
        if tag == "img":
            for parent in self.stack:
                if parent["tag"] == "a":
                    parent["text"] += " " + node["attrs"].get("alt", "")
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                break

    def handle_data(self, text):
        if self.stack:
            self.stack[-1]["children"].append(text)
        for parent in self.stack:
            if parent["tag"] in {"script", "style"} or not any(p["tag"] in {"script", "style", "template"} for p in self.stack):
                parent["text"] += text
        if not any(p["tag"] in {"script", "style", "head", "template"} or p["hidden"] for p in self.stack):
            self.parts.append(text)

    def label(self, node, seen=None, include_hidden=False):
        """Static naming subset, not the complete browser accessible-name algorithm."""
        seen = set() if seen is None else seen
        if id(node) in seen or node["inert"] or node["tag"] in {"script", "style"}:
            return ""
        if node["hidden"] and not include_hidden:
            return ""
        seen = seen | {id(node)}
        attrs = node["attrs"]
        ids = {n["attrs"].get("id"): n for n in self.nodes if n["attrs"].get("id")}
        targets = [ids[k] for k in attrs.get("aria-labelledby", "").split() if k in ids]
        if targets:
            return " ".join(self.label(n, seen, n["hidden"]) for n in targets).strip()
        if attrs.get("aria-label", "").strip():
            return attrs["aria-label"].strip()
        if node["tag"] == "img":
            return attrs.get("alt", "").strip()
        value = " ".join(child if isinstance(child, str) else self.label(child, seen, include_hidden)
                         for child in node["children"]).strip()
        return value or attrs.get("title", "").strip()

    def static_text(self, node):
        if node["hidden"] or node["inert"] or node["tag"] in {"script", "style"}:
            return ""
        return " ".join(c if isinstance(c, str) else self.static_text(c) for c in node["children"]).strip()

    def tags(self, tag):
        return [n for n in self.nodes if n["tag"] == tag]

    @property
    def text(self):
        return " ".join(" ".join(self.parts).split())


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def valid_date(value):
    if not isinstance(value, str):
        return False
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            date.fromisoformat(value)
        elif re.match(r"^\d{4}-\d{2}-\d{2}T", value):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return False
        else:
            return False
        return True
    except ValueError:
        return False


def applicable(rule, bundle, page):
    kind = rule["applies"]
    checks = {"always": True, "page": bundle["stage"] != "draft", "images": bool(page.tags("img")),
              "links": bool(page.tags("a")), "jsonld": bool(jsonld(page)),
              "schema": bool(jsonld(page)) or any(set(n["attrs"]) & {"itemscope", "itemtype", "typeof", "vocab"} for n in page.nodes),
              "media": any(page.tags(t) for t in ("img", "video", "audio", "iframe")),
              "video_claim": bundle["brief"].get("video_search_claim", False),
              "ymyl": True, "updated": bundle["brief"].get("updated", False)}
    if rule["method"] == "live":
        return bundle["stage"] == "live"
    if rule["method"] == "rendered":
        return bundle["stage"] != "draft"
    return checks[kind]


def jsonld(page):
    return [n for n in page.tags("script") if n["attrs"].get("type", "").lower() == "application/ld+json"]


def usable_url(value, absolute=False):
    """Conservative navigation syntax policy; no fetching or reachability inference."""
    if not nonempty(value) or any(ord(c) < 32 or ord(c) == 127 for c in value):
        return False
    value = value.strip()
    try:
        parsed = urlsplit(value)
        scheme = parsed.scheme.lower()
        if absolute and scheme not in ("http", "https"):
            return False
        if scheme not in ("", "http", "https", "mailto", "tel"):
            return False
        if scheme in ("http", "https") or value.startswith("//"):
            return bool(parsed.hostname) and not any(c.isspace() for c in parsed.netloc) and parsed.port != 0
        if scheme in ("mailto", "tel"):
            return bool(parsed.path.strip())
        return True
    except ValueError:
        return False


def automatic(rid, bundle, page):
    """Return exact failing locations; success is limited to the named static check."""
    bad = []
    heads = [n for n in page.nodes if re.fullmatch(r"h[1-6]", n["tag"])]
    brief = bundle["brief"]
    if rid == "INPUT-001":
        bad = ["brief." + k for k in ("audience", "market", "purpose", "intent", "next_action", "responsible_party") if not nonempty(brief.get(k))]
        bad += ["brief." + k for k in ("ymyl", "updated", "video_search_claim") if type(brief.get(k)) is not bool]
    elif rid == "HTML-001":
        bad = [] if any(n["tag"] == "h1" and page.static_text(n) for n in heads) else ["document: missing nonhidden main h1 in markup"]
    elif rid == "HTML-002":
        bad = [n for n in heads if not n["text"].strip()]
    elif rid == "HTML-003":
        prior = 0
        for n in heads:
            level = int(n["tag"][1])
            if level > prior + 1:
                bad.append(n)
            prior = level
    elif rid == "HTML-004":
        bad = [] if page.text else ["document: no textual content"]
    elif rid == "IMAGE-001":
        bad = [n for n in page.tags("img") if "alt" not in n["attrs"]]
    elif rid == "ANCHOR-001":
        for n in page.tags("a"):
            href = n["attrs"].get("href", "").strip()
            if not href and (n["attrs"].get("id") or n["attrs"].get("name")):
                continue
            if not usable_url(n["attrs"].get("href", "")):
                bad.append(n)
    elif rid == "ANCHOR-002":
        ids = {n["attrs"].get("id") for n in page.nodes} | {n["attrs"].get("name") for n in page.tags("a")}
        bad = [n for n in page.tags("a") if n["attrs"].get("href", "").startswith("#") and len(n["attrs"]["href"]) > 1 and unquote(n["attrs"]["href"][1:]) not in ids]
    elif rid == "ANCHOR-003":
        # Decorative duplicate links may be explicitly removed from both access paths.
        bad = [n for n in page.tags("a") if "href" in n["attrs"]
               and not (n["attrs"].get("aria-hidden", "").lower() == "true" and n["attrs"].get("tabindex") == "-1")
               and not page.label(n)]
    elif rid == "JSONLD-001":
        for n in jsonld(page):
            try:
                value = read_json(n["text"])
                if not isinstance(value, dict) and not (isinstance(value, list) and value and all(isinstance(v, dict) for v in value)):
                    bad.append(n)
            except ValueError:
                bad.append(n)
    elif rid == "META-001":
        titles = page.tags("title")
        bad = [] if len(titles) == 1 and titles[0]["text"].strip() else ["document: expected one nonempty title"]
    elif rid == "META-002":
        descriptions = [n for n in page.tags("meta") if n["attrs"].get("name", "").lower() == "description"]
        bad = [] if len(descriptions) == 1 and descriptions[0]["attrs"].get("content", "").strip() else ["document: description missing, empty or duplicated"]
    elif rid == "META-003":
        expected = brief.get("canonical_url")
        nodes = [n for n in page.tags("link") if "canonical" in n["attrs"].get("rel", "").lower().split()]
        bad = [] if usable_url(expected, absolute=True) and len(nodes) == 1 and nodes[0]["attrs"].get("href") == expected else ["document: canonical differs from declared canonical_url or valid absolute intent is missing"]
    elif rid == "ROBOTS-001":
        intent = brief.get("indexing")
        directives = [n["attrs"].get("content", "").lower() for n in page.tags("meta") if n["attrs"].get("name", "").lower() in ("robots", "googlebot")]
        excluded = any(set(re.split(r"[\s,]+", v)) & {"noindex", "none"} for v in directives)
        bad = [] if (intent == "index" and not excluded) or (intent == "noindex" and excluded) else ["document: meta indexing directives differ from declared intent"]
    elif rid == "CLAIM-001":
        evidence = {e["id"] for e in bundle["evidence"]}
        for claim in bundle["claims"]:
            quote = " ".join(claim.get("quote", "").split())
            if not quote or quote not in page.text or not claim.get("evidence_ids") or not set(claim["evidence_ids"]) <= evidence:
                bad.append("claim:" + claim["id"])
    elif rid == "EVIDENCE-001":
        for e in bundle["evidence"]:
            if any(not nonempty(e.get(k)) for k in ("title", "origin", "captured_at", "file")) or not valid_date(e.get("captured_at")):
                bad.append("evidence:" + e["id"])
    elif rid == "LANG-001":
        bad = [] if any(n["attrs"].get("lang", "").strip() for n in page.tags("html")) else ["document: missing language"]
    else:
        raise ValueError("Unimplemented automatic rule: " + rid)
    return ["line:" + str(n["line"]) if isinstance(n, dict) else n for n in bad]


def load_bundle(path):
    if path.is_symlink():
        raise ValueError("Bundle must not be a symlink")
    root = path.parent.resolve()
    bundle = read_json(read_input(root, path.name))
    if not isinstance(bundle, dict) or type(bundle.get("schema_version")) is not int or bundle.get("schema_version") != 1:
        raise ValueError("Expected bundle schema_version 1")
    if bundle.get("stage") not in ("draft", "staging", "live") or bundle.get("page_type") not in ("article", "landing"):
        raise ValueError("Unsupported stage or page_type")
    if not isinstance(bundle.get("brief"), dict):
        raise ValueError("brief must be an object")
    if not isinstance(bundle.get("content"), str) or Path(bundle["content"]).suffix.lower() not in (".html", ".htm"):
        raise ValueError("Provide an HTML draft; Markdown conversion is not implemented")
    content = read_input(root, bundle["content"])
    evidence_hashes = {}
    for key in ("claims", "evidence"):
        if not isinstance(bundle.get(key), list):
            raise ValueError(key + " must be an explicit list, even when empty")
        ids = set()
        for item in bundle[key]:
            if not isinstance(item, dict) or not nonempty(item.get("id")) or item["id"] in ids:
                raise ValueError("Invalid or duplicate " + key + " ID")
            ids.add(item["id"])
            if key == "evidence":
                evidence_hashes[item["id"]] = sha(read_input(root, item["file"]))
            elif not isinstance(item.get("evidence_ids"), list) or not all(isinstance(i, str) for i in item["evidence_ids"]) or not isinstance(item.get("quote"), str):
                raise ValueError("Claim requires quote and evidence_ids")
    return bundle, content, evidence_hashes


def source_index(snapshot, rules):
    audit = read_json(safe_read(snapshot, "knowledge/audit.json"))
    safe_read(snapshot, "manifest.json", audit["manifest_sha256"])
    chunks = [read_json(line) for line in safe_read(snapshot, "knowledge/chunks.jsonl", audit["chunks_sha256"]).splitlines()]
    by_source = {}
    verified = set()
    for chunk in chunks:
        by_source.setdefault(chunk["citation"], []).append(chunk["id"])
        if chunk["source_file"] not in verified:
            safe_read(snapshot, chunk["source_file"], chunk["source_sha256"])
            verified.add(chunk["source_file"])
    for rule in rules:
        if rule["source"] not in by_source:
            raise ValueError("Unresolved rule citation: " + rule["id"])
    return audit, chunks, by_source


def load_observations(root, bundle, content, evidence_hashes, rules):
    """Import operator-supplied observations; never collect live or rendered data."""
    files = bundle.get("observations", [])
    if not isinstance(files, list) or not all(isinstance(name, str) for name in files) or len(files) != len(set(files)):
        raise ValueError("observations must be a list of distinct relative receipt paths")
    records, hashes = {}, {}
    context = sha(canonical({"brief": bundle["brief"], "stage": bundle["stage"], "page_type": bundle["page_type"]}))
    supported = {r["id"] for r in rules if r["method"] in ("live", "rendered")}
    for name in files:
        raw = read_input(root, name)
        hashes[name] = sha(raw)
        receipt = read_json(raw)
        if not isinstance(receipt, dict) or type(receipt.get("schema_version")) is not int or receipt["schema_version"] != 1:
            raise ValueError("Invalid observation receipt schema")
        if receipt.get("content_sha256") != sha(content) or receipt.get("context_sha256") != context:
            raise ValueError("Observation receipt is stale or belongs to different content/context")
        if not usable_url(receipt.get("url"), absolute=True) or receipt["url"] != bundle["brief"].get("canonical_url"):
            raise ValueError("Observation URL must match the declared canonical URL")
        if not valid_date(receipt.get("captured_at")) or not nonempty(receipt.get("reviewer")):
            raise ValueError("Observation requires capture date and responsible reviewer")
        if not isinstance(receipt.get("checks"), list) or not receipt["checks"]:
            raise ValueError("Observation receipt requires checks")
        for check in receipt["checks"]:
            if not isinstance(check, dict):
                raise ValueError("Observation check must be an object")
            rid = check.get("rule_id")
            if rid not in supported or rid in records:
                raise ValueError("Unknown, duplicate or unsupported observation rule")
            refs = check.get("evidence_sha256")
            if not isinstance(refs, dict) or not refs or any(key not in evidence_hashes or evidence_hashes[key] != value for key, value in refs.items()):
                raise ValueError("Observation evidence hashes do not match the bundle")
            if check.get("status") not in ("pass", "fail", "not_tested") or not nonempty(check.get("reason")):
                raise ValueError("Observation needs explicit status and reason")
            records[rid] = check | {"receipt": name, "captured_at": receipt["captured_at"], "reviewer": receipt["reviewer"]}
    return records, hashes, context


def review_actor(receipt):
    actor = receipt.get("actor")
    if not isinstance(actor, dict) or actor.get("kind") not in ("ai", "human") or not nonempty(actor.get("identity")):
        raise ValueError("Review requires an identified AI or human actor")
    relationships = {"ai": {"same_agent", "separate_context", "unknown"},
                     "human": {"human_review", "unknown"}}
    if actor.get("relationship_to_author") not in relationships[actor["kind"]]:
        raise ValueError("Declare the reviewer's relationship to the author")
    if actor["kind"] == "ai" and any(not nonempty(actor.get(k)) for k in ("model", "run_id")):
        raise ValueError("AI review requires model and run_id; use not_exposed for an unavailable model name")
    if receipt.get("purpose") not in ("content_review", "illustration"):
        raise ValueError("Review requires content_review or illustration purpose")
    return actor


def review_records(items, key, known, evidence_hashes, allow_na=True):
    if not isinstance(items, list):
        raise ValueError(key + " decisions must be a list")
    records = {}
    allowed = {"pass", "fail", "needs_review"} | ({"not_applicable"} if allow_na else set())
    for decision in items:
        if not isinstance(decision, dict):
            raise ValueError("Review decisions must be objects")
        identifier = decision.get(key)
        if not isinstance(identifier, str) or identifier not in known or identifier in records:
            raise ValueError("Unknown, duplicate or non-reviewable " + key)
        if decision.get("status") not in allowed or any(not nonempty(decision.get(k)) for k in ("reviewer", "reason")):
            raise ValueError("Decision requires status, reviewer and reason")
        if not valid_date(decision.get("reviewed_at")):
            raise ValueError("Review date must be ISO date or timezone-qualified datetime")
        refs = decision.get("evidence_ids")
        if (not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs)
                or len(refs) != len(set(refs)) or not set(refs) <= set(evidence_hashes)
                or (not refs and decision["status"] != "needs_review")):
            raise ValueError("Resolved decisions require distinct, known local evidence references")
        records[identifier] = decision
    return records


def validate(path, snapshot=None, review_path=None, references_only=False):
    if (snapshot is None) != references_only:
        raise ValueError("Choose exactly one: a local snapshot or explicit references-only mode")
    bundle, content, evidence_hashes = load_bundle(path)
    rules = catalog()
    mapping = criteria_map()
    required_sources = sorted({urldefrag(r["source"])[0] for r in rules}
                              | {urldefrag(url)[0] for source in mapping["sources"].values() for url in source["urls"]})
    observations, observation_hashes, context_hash = load_observations(path.parent, bundle, content, evidence_hashes, rules)
    if references_only:
        audit = {"complete_within_scope": False, "chunks_sha256": None}
        sources = {r["source"]: [] for r in rules}
    else:
        audit, chunks, sources = source_index(snapshot, rules)
    engine = sha(Path(__file__).read_bytes() + Path(__file__).with_name("rule_catalog.py").read_bytes()
                 + Path(__file__).with_name("knowledge.py").read_bytes())
    fingerprint = sha(canonical({"bundle": bundle, "content": sha(content), "evidence": evidence_hashes,
                                 "rules": rules, "engine": engine, "source_index": audit["chunks_sha256"],
                                 "observations": observation_hashes, "references_only": references_only,
                                 "criteria_map": mapping}))
    page = Page(content.decode("utf-8"))
    decisions = {}
    criterion_decisions, source_decisions = {}, {}
    actor, review_hash, review_purpose = None, None, None
    review_error = None
    if review_path:
        raw_review = read_input(review_path.parent, review_path.name)
        review_hash = sha(raw_review)
        receipt = read_json(raw_review)
        if not isinstance(receipt, dict) or type(receipt.get("schema_version")) is not int or receipt["schema_version"] != 2:
            raise ValueError("Expected review schema_version 2; v1 receipts require fresh review")
        if receipt.get("fingerprint") != fingerprint:
            review_error = "Review is stale or belongs to different inputs; no decisions applied."
        else:
            actor = review_actor(receipt)
            review_purpose = receipt["purpose"]
            decisions = review_records(receipt.get("decisions"), "rule_id",
                {r["id"] for r in rules if r["method"] in ("editorial", "rendered")}, evidence_hashes)
            criterion_decisions = review_records(receipt.get("criteria", []), "criterion_id",
                {c["id"] for c in mapping["criteria"]}, evidence_hashes)
            source_decisions = review_records(receipt.get("sources", []), "source",
                set(required_sources), evidence_hashes, allow_na=False)
            if any(d["reviewer"] != actor["identity"] for group in (decisions, criterion_decisions, source_decisions) for d in group.values()):
                raise ValueError("Decision reviewer must match the receipt actor")
    findings = []
    for rule in rules:
        locations = []
        in_scope = applicable(rule, bundle, page)
        decision = decisions.get(rule["id"])
        observation = observations.get(rule["id"])
        conflict = bool(not in_scope and any(d and d["status"] == "fail" for d in (decision, observation)))
        if observation and observation["status"] == "fail":
            status, observed = "fail", observation["reason"]
        elif decision and decision["status"] == "fail":
            status, observed = "fail", decision["reason"]
        elif not in_scope:
            status, observed = "not_applicable", "Outside declared stage or absent feature: " + rule["applies"]
        elif rule["method"] == "auto":
            locations = automatic(rule["id"], bundle, page)
            status = "fail" if locations else "pass"
            observed = "Static check only; no rendered or live behavior inferred."
        elif observation:
            status, observed = observation["status"], observation["reason"]
        elif rule["method"] == "live":
            status, observed = "not_tested", "No imported live observation; automatic collection is not implemented."
        elif rule["id"] in decisions:
            status, observed = decisions[rule["id"]]["status"], decisions[rule["id"]]["reason"]
        else:
            status, observed = "needs_review", profile_prompt(rule, bundle["page_type"])
        findings.append({"rule_id": rule["id"], "title": rule["title"], "method": rule["method"],
                         "severity": rule["severity"], "status": status, "locations": locations,
                         "observed_evidence": observed, "source": rule["source"], "source_chunk_ids": sources[rule["source"]],
                         "remediation": rule["remediation"], "policy": rule["policy"],
                         "scope_conflict": conflict,
                         "profile_prompt": profile_prompt(rule, bundle["page_type"]),
                         "family": rule["family"], "source_class": rule["source_class"],
                         "observation": observation,
                         "decision": decisions.get(rule["id"])})
    eeat = [{"criterion_id": c["id"], "dimension": c["dimension"], "title": c["title"],
             "status": criterion_decisions.get(c["id"], {}).get("status", "needs_review"),
             "prompt": c["review"], "profile_prompt": c[bundle["page_type"]],
             "applies_when": c["applies_when"], "exception": c["exception"],
             "pass_condition": c["pass"], "fail_condition": c["fail"], "unknown_condition": c["unknown"],
             "evidence_needed": c["evidence"], "automation_limit": c["automation_limit"],
             "sources": sorted({url for sid in c["sources"] for url in mapping["sources"][sid]["urls"]}),
             "related_rule_ids": c["direct_rules"] + c["supporting_rules"],
             "decision": criterion_decisions.get(c["id"])} for c in mapping["criteria"]]
    source_findings = [{"source": url, "status": source_decisions.get(url, {}).get("status", "needs_review"),
                        "decision": source_decisions.get(url)} for url in required_sources]
    source_review_required = any(f["status"] != "pass" for f in source_findings)
    blocked = (any(f["status"] == "fail" and f["severity"] != "warning" for f in findings)
               or any(f["status"] == "fail" for f in eeat + source_findings))
    unresolved = (source_review_required or review_error or review_purpose == "illustration"
                  or any(f["status"] in ("needs_review", "not_tested", "fail") for f in findings + eeat))
    readiness = "blocked" if blocked else "review_required" if unresolved else "ready_for_owner_review"
    return {"schema_version": 2, "validator_version": VERSION, "fingerprint": fingerprint,
            "content_sha256": sha(content), "context_sha256": context_hash,
            "stage": bundle["stage"], "page_type": bundle["page_type"], "readiness": readiness,
            "review_error": review_error, "counts": dict(Counter(f["status"] for f in findings)),
            "findings": findings, "source_coverage_complete": audit["complete_within_scope"],
            "source_verification": "references_only_not_verified" if references_only else "local_snapshot_hashes_verified",
            "source_review_required": source_review_required,
            "source_review_assurance": "operator_attestation_only" if not source_review_required else "incomplete",
            "review_actor": actor, "review_purpose": review_purpose, "review_receipt_sha256": review_hash,
            "reviewer_identity_verified": False, "publication_approved": False,
            "eeat_criteria": eeat, "eeat_counts": dict(Counter(f["status"] for f in eeat)),
            "source_reviews": source_findings,
            "review_queue": [{"family": family, "rule_ids": [f["rule_id"] for f in findings
                              if f["family"] == family and f["status"] in ("fail", "needs_review", "not_tested")]}
                             for family in sorted({f["family"] for f in findings
                             if f["status"] in ("fail", "needs_review", "not_tested")})],
            "limits": ["No publication approval or ranking score", "HTML inventory is not browser rendering",
                       "Static labels are a limited subset, not accessible-name conformance; CSS and JavaScript visibility require rendered review",
                       "AI and human decisions are operator attestations, not authenticated signatures or independent calibration",
                       "No live fetching, link reachability testing or complete schema-feature validation"]}


def review_template(report):
    """Return an unresolved receipt scaffold; never generate approvals."""
    def pending(key, identifier, prompt):
        return {key: identifier, "status": "needs_review", "reviewer": "", "reviewed_at": "",
                "reason": "", "evidence_ids": [], "review_prompt": prompt}
    return {"schema_version": 2, "purpose": "content_review", "fingerprint": report["fingerprint"],
            "actor": {"kind": "ai", "identity": "", "model": "not_exposed", "run_id": "",
                      "relationship_to_author": "unknown"},
            "decisions": [pending("rule_id", f["rule_id"], f["profile_prompt"])
                          for f in report["findings"] if f["method"] in ("editorial", "rendered")
                          and f["status"] == "needs_review"],
            "criteria": [pending("criterion_id", f["criterion_id"], f["profile_prompt"])
                         for f in report["eeat_criteria"]],
            "sources": [pending("source", f["source"],
                        "Read the cited sections in context. Attach capture notes and explain support or conflict; inaccessible sources remain unresolved.")
                        for f in report["source_reviews"]]}


def coverage(snapshot, triage_path=None):
    rules = catalog()
    audit, chunks, sources = source_index(snapshot, rules)
    adjudications = {}
    if triage_path:
        receipt = read_json(read_input(triage_path.parent, triage_path.name))
        if not isinstance(receipt, dict) or receipt.get("chunks_sha256") != audit["chunks_sha256"]:
            raise ValueError("Triage receipt must bind the current chunk index")
        if not isinstance(receipt.get("decisions"), list):
            raise ValueError("Triage receipt requires decisions")
        known = {c["id"] for c in chunks}
        allowed = {"active_evidence", "context", "example", "duplicate", "retired", "out_of_scope", "unresolved"}
        rule_ids = {r["id"] for r in rules}
        for decision in receipt["decisions"]:
            if not isinstance(decision, dict):
                raise ValueError("Triage decision must be an object")
            cid = decision.get("chunk_id")
            if cid not in known or cid in adjudications:
                raise ValueError("Unknown or duplicate triage chunk")
            if decision.get("disposition") not in allowed or not valid_date(decision.get("reviewed_at")) or any(not nonempty(decision.get(k)) for k in ("reviewer", "reason")):
                raise ValueError("Triage requires disposition, reviewer, date and rationale")
            refs = decision.get("rule_ids", [])
            if not isinstance(refs, list) or not all(isinstance(r, str) for r in refs) or not set(refs) <= rule_ids:
                raise ValueError("Triage references unknown rules")
            if decision["disposition"] == "active_evidence" and not refs:
                raise ValueError("Active evidence requires rule references")
            if decision["disposition"] == "duplicate" and (decision.get("duplicate_of") not in known or decision["duplicate_of"] == cid):
                raise ValueError("Duplicate disposition needs a different known chunk")
            adjudications[cid] = decision
    rows = []
    for chunk in chunks:
        linked = [r["id"] for r in rules if r["source"] == chunk["citation"]]
        url = chunk["citation"]
        family = next((name for term, name in (("/style/", "editorial"), ("spam-policies", "spam"),
                      ("structured-data", "schema"), ("/crawling", "technical"), (".pdf", "rater_framework"),
                      ("/fundamentals/", "content_quality"), ("/appearance/", "search_features"),
                      ("/search/updates", "historical_updates")) if term in url), "other")
        rows.append({"chunk_id": chunk["id"], "source": chunk["citation"], "rule_ids": linked,
                     "suggested_family": family, "classification_method": "URL heuristic, not editorial adjudication",
                     "disposition": "linked_rule_evidence" if linked else "pending_editorial_triage"})
        if chunk["id"] in adjudications:
            rows[-1]["adjudication"] = adjudications[chunk["id"]]
            rows[-1]["disposition"] = adjudications[chunk["id"]]["disposition"]
    return {"rules": len(rules), "chunks": len(chunks), "dispositions": dict(Counter(r["disposition"] for r in rows)),
            "chunks_sha256": audit["chunks_sha256"], "adjudicated_chunks": len(adjudications),
            "unresolved_chunks": len(chunks) - sum(d["disposition"] != "unresolved" for d in adjudications.values()),
            "complete": False, "source_exceptions": audit["source_exceptions"], "rows": rows}


def write_report(target, report, execute):
    if not execute:
        raise ValueError("Report export requires --execute")
    if target.exists() or any(p.is_symlink() for p in [target, *target.parents]):
        raise ValueError("Output must be a new nonsymlink directory")
    if not target.parent.is_dir():
        raise ValueError("Output parent must already exist")
    target.mkdir()
    (target / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = ["Google-Dev-and-EEAT-Validator review", "Readiness: " + report["readiness"],
             "Source verification: " + report["source_verification"], "Fingerprint: " + report["fingerprint"], ""]
    for f in report["findings"]:
        lines.extend([f["rule_id"] + " | " + f["status"] + " | " + f["title"],
                      "Locations: " + ", ".join(f["locations"]), "Evidence: " + f["observed_evidence"],
                      "Action: " + f["remediation"], "Source: " + f["source"], ""])
    lines.extend(["Review actor: " + json.dumps(report["review_actor"]),
                  "Source review assurance: " + report["source_review_assurance"],
                  "Publication approved: false", "", "E-E-A-T criteria"])
    for f in report["eeat_criteria"]:
        lines.extend([f["criterion_id"] + " | " + f["status"] + " | " + f["title"],
                      "Decision: " + (f["decision"]["reason"] if f["decision"] else "Not assessed"), ""])
    lines.append("Source reviews")
    for f in report["source_reviews"]:
        lines.append(f["status"] + " | " + f["source"])
    (target / "report.txt").write_text("\n".join(lines))
    receipt = {"schema_version": 1, "fingerprint": report["fingerprint"],
               "files": {name: sha((target / name).read_bytes()) for name in ("report.json", "report.txt")}}
    (target / "COMPLETE.json").write_text(json.dumps(receipt, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, nargs="?")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snapshot", type=Path)
    mode.add_argument("--references-only", action="store_true", help="Run without a source archive; requires evidenced source-review attestations")
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--review-template", action="store_true", help="Print an unresolved v2 receipt scaffold; never writes or approves")
    parser.add_argument("--coverage", action="store_true")
    parser.add_argument("--triage", type=Path, help="Optional operator adjudications for read-only coverage")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        if args.coverage:
            if args.references_only:
                raise ValueError("Coverage requires a local snapshot")
            if args.output or args.execute or args.bundle or args.reviews or args.review_template:
                raise ValueError("Coverage is read-only; use only --coverage and --snapshot")
            print(json.dumps(coverage(args.snapshot, args.triage), indent=2))
            return 0
        if args.triage:
            raise ValueError("--triage requires --coverage")
        if not args.bundle or (args.execute and not args.output):
            raise ValueError("Provide a bundle; --execute requires --output")
        if args.review_template and (args.reviews or args.output or args.execute):
            raise ValueError("Review templates are read-only scaffolds; do not combine with reviews or exports")
        result = validate(args.bundle, args.snapshot, args.reviews, args.references_only)
        if args.review_template:
            print(json.dumps(review_template(result), indent=2))
            return 0
        if args.output:
            write_report(args.output, result, args.execute)
        print(json.dumps(result, indent=2))
        return {"ready_for_owner_review": 0, "review_required": 2, "blocked": 3}[result["readiness"]]
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as exc:
        print(json.dumps({"error": str(exc), "readiness": "invalid_input"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
