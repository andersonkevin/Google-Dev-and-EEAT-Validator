"""Minimal local evidence reader. No network, index builder or source archive."""
import hashlib
from pathlib import Path


def safe_read(root, relative, expected=None):
    root = root.resolve()
    if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("Unsafe evidence path")
    candidate = root / relative
    if any(p.is_symlink() for p in [candidate, *candidate.parents]):
        raise ValueError("Symlink evidence is not supported")
    if not candidate.resolve().is_relative_to(root):
        raise ValueError("Evidence escapes snapshot")
    data = candidate.read_bytes()
    if expected and hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Evidence hash mismatch: " + relative)
    return data
