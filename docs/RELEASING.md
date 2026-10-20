# Release Procedure

## Validate

```sh
python3 -B -m unittest discover -s tests -v
python3 -B examples/review_walkthrough.py
python3 -B tools/release.py
git diff --check
```

The source audit checks a fixed allowlist, license/version alignment, local doc
links, simple credential/path patterns and the local SVG structure. It is not a
comprehensive secret scanner or a semantic correctness certification. Review the
staged diff manually. No private drafts, evidence, archives or generated reports
belong in the release.

CI runs the same test/demo/audit commands on Ubuntu Python 3.10/3.13 and macOS
Python 3.13. Actions are commit-pinned, permissions are read-only, checkout does
not persist credentials, and no project dependencies are installed. CI downloads
its action/runtime infrastructure. Do not infer Windows qualification from this matrix.

CI pins [checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1)
and [setup-python v7.0.0](https://github.com/actions/setup-python/releases/tag/v7.0.0)
to full commit SHAs. Both use Node 24 and require Actions Runner 2.327.1 or later;
the workflow uses GitHub-hosted runners. Verify release tags and runtime/input
compatibility in the upstream repositories before updating these pins. Keep the
read-only permissions, disabled credential persistence and existing checks intact.

## Package

```sh
python3 -B tools/release.py --archive /private/output/Google-Dev-and-EEAT-Validator-v2.1.0.zip --execute
```

The output parent must already exist. Existing files and symlinks are rejected;
the tool never overwrites or uploads. It packages the exact audited bytes, excludes
Git history and emits the ZIP hash. An interrupted ZIP is not a release: inspect
it and use a new destination when retrying. Extract and test the package in a
temporary directory before distribution. Explicitly extend the source allowlist
when adding intended release files.

## Publish with Owner Authorization

Commit only the reviewed distribution changes. Run CI before tagging/releasing.
Create a new version tag, never move an existing release tag. Attach the verified
ZIP and its checksum to the corresponding GitHub Release. Publication is an
operator action; the release tool and CI do not push, tag or create releases.

For v2.1.0, explain the hidden-state correction, review plan, contract discovery
and evaluation-design safeguards. Bundle/receipt/report schemas remain 1/2/2;
the criterion mapping remains 2.0.0 while the tool/catalog are 2.1.0. Exact-version
consumer pins require explicit updates and engine changes require fresh receipts.
Do not describe synthetic success as completed real-content calibration.
