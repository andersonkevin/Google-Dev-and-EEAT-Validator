"""Release audit and no-overwrite packaging use temporary directories only."""
from pathlib import Path
import tempfile
import unittest
import zipfile

import test_validator
from release import archive, audit, FILES


class ReleaseTests(unittest.TestCase):
    def test_public_audit(self):
        self.assertEqual(set(audit()), set(FILES))

    def test_archive_requires_approval_and_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve() / 'release.zip'
            with self.assertRaises(ValueError):
                archive(target, {'README.md': b'fixture'})
            self.assertFalse(target.exists())
            archive(target, {'README.md': b'fixture'}, True)
            before = target.read_bytes()
            with self.assertRaises(ValueError):
                archive(target, {'README.md': b'changed'}, True)
            self.assertEqual(before, target.read_bytes())

    def test_archive_bytes_are_allowlisted_and_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            data = audit()
            first, second = root / 'one.zip', root / 'two.zip'
            self.assertEqual(archive(first, data, True), archive(second, data, True))
            with zipfile.ZipFile(first) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(len(z.namelist()), len(FILES))
                for name, raw in data.items():
                    self.assertEqual(z.read('Google-Dev-and-EEAT-Validator/' + name), raw)
                self.assertFalse(any('/.git/' in name for name in z.namelist()))

    def test_archive_rejects_symlink_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'link').symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                archive(root / 'link' / 'release.zip', {'a': b'b'}, True)

    def test_archive_rejects_unlisted_or_traversing_entries_before_write(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve() / 'release.zip'
            for name in ('../outside.txt', '/absolute.txt', 'private.txt'):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        archive(target, {name: b'fixture'}, True)
                    self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
