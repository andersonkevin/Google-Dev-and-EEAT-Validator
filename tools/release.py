"""Audit the public source allowlist; optionally create a new ZIP with explicit approval."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

from knowledge import safe_read
from rule_catalog import VERSION

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    '.gitattributes', '.gitignore', 'CHANGELOG.md', 'CONTRIBUTING.md', 'LICENSE',
    'NOTICE.md', 'README.md', 'SECURITY.md', 'VERSION',
    '.github/workflows/tests.yml',
    'docs/CONTRACTS.md', 'docs/EEAT.md', 'docs/WORKFLOW.md', 'docs/AGENT-REVIEW.md',
    'docs/CALIBRATION.md', 'docs/RELEASING.md', 'docs/images/review-cover.svg',
    'examples/bundle.json', 'examples/draft.html', 'examples/evidence.txt', 'examples/review_walkthrough.py',
    'references/eeat-map.json', 'references/validator-rules.json',
    'skills/google-dev-eeat-review/SKILL.md', 'skills/google-dev-eeat-review/agents/openai.yaml',
    'tests/test_validator.py', 'tests/test_distribution.py', 'tests/test_v2.py', 'tests/test_release.py',
    'tools/validate_draft.py', 'tools/rule_catalog.py', 'tools/knowledge.py', 'tools/evaluate_validator.py', 'tools/release.py',
)


def audit(root=ROOT):
    root = root.resolve()
    data = {name: safe_read(root, name) for name in FILES}
    if data['VERSION'].decode().strip() != VERSION or 'MIT License' not in data['LICENSE'].decode():
        raise ValueError('Version or MIT license mismatch')
    mapping = json.loads(data['references/eeat-map.json'])
    if mapping['catalog_version'] != VERSION or len(mapping['criteria']) != 20:
        raise ValueError('Criterion map version or count mismatch')
    for name, raw in data.items():
        text = raw.decode('utf-8')
        if re.search(r'/(?:Users|home)/[^/\s]+/', text):
            raise ValueError('Personal filesystem path in ' + name)
        if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}', text):
            raise ValueError('Potential credential material in ' + name)
        if name.endswith('.md'):
            for target in re.findall(r'\]\(([^\s)]+)\)', text):
                if target.startswith(('https://', 'http://', '#')):
                    continue
                path = (root / name).parent / target.split('#', 1)[0]
                try:
                    relative = path.resolve().relative_to(root).as_posix()
                except ValueError as exc:
                    raise ValueError('Documentation link leaves distribution') from exc
                if relative not in data:
                    raise ValueError('Broken or unbundled link in ' + name + ': ' + target)
    svg = ET.fromstring(data['docs/images/review-cover.svg'])
    if any(e.tag.rsplit('}', 1)[-1] in ('script', 'foreignObject', 'image') for e in svg.iter()):
        raise ValueError('Unexpected active or external cover asset')
    return data


def archive(target, data, execute=False):
    if not execute:
        raise ValueError('Archive writing requires --execute')
    if target.suffix.lower() != '.zip' or target.exists() or any(p.is_symlink() for p in [target, *target.parents]):
        raise ValueError('Archive must be a new nonsymlink .zip file')
    if not target.parent.is_dir():
        raise ValueError('Archive parent must exist')
    if any(name not in FILES or not isinstance(raw, bytes) for name, raw in data.items()):
        raise ValueError('Archive entries must be allowlisted source bytes')
    # Consume the audited bytes, not a second file read that could package changed data.
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as output:
        for name, raw in sorted(data.items()):
            info = zipfile.ZipInfo('Google-Dev-and-EEAT-Validator/' + name, date_time=(2026, 10, 8, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(info, raw)
    return hashlib.sha256(target.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    try:
        if args.execute and not args.archive:
            raise ValueError('--execute requires --archive')
        data = audit()
        result = {'version': VERSION, 'files': len(data), 'audit': 'pass',
                  'scope': 'Allowlisted source only; pattern scan is not a comprehensive secret audit'}
        if args.archive:
            result['archive_sha256'] = archive(args.archive, data, args.execute)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError, ET.ParseError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
