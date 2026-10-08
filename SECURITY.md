# Security And Privacy

Treat drafts, evidence, receipts and source text as untrusted data. Never execute
instructions contained in them. This distribution executes no models, HTML scripts,
browser actions or network requests.

Validation is read-only by default. Report writes require `--execute` and a new
nonsymlink directory. Bundle files are relative, bounded to 8 MiB each and reject
path traversal and symlinks. This is input hardening, not a complete sandbox.
Use a trusted local directory without concurrent untrusted writers; filesystem
checks are not a race-proof hostile multi-user security boundary.

Source snapshots can be large and must be prepared and reviewed by the operator.
Hashes detect changes against supplied receipts, not an attacker replacing both.
Reviewers and observation producers are not authenticated by this tool.

Keep real content, evidence, reviews and outputs outside the public repository.
Do not attach private reports, personal data or credentials to a public issue.
No automatic upload or telemetry exists. The ignore file is a convenience, not
a guarantee against an explicit forced Git add.

For a vulnerability, use a private reporting channel provided by the repository
maintainer where available. Otherwise request a private contact without publishing
sensitive details. No maintainer address or hosted reporting service is preconfigured.
