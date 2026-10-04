"""Portable checks for exact reconstruction and no-overwrite source extraction."""
import hashlib
import json
import lzma
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import extract_source as extractor


def sha(value):
    return hashlib.sha256(value).hexdigest()


class ExtractSourceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.original_here = extractor.HERE
        extractor.HERE = self.root
        self.payload = b'BLENDER-v430' + bytes(range(256)) * 9000
        self.archive = lzma.compress(self.payload)
        chunks = [self.archive[:41], self.archive[41:97], self.archive[97:]]
        self.parts = []
        for index, chunk in enumerate(chunks):
            name = f'Sunward.blend.xz.part{index + 1:02d}'
            (self.root / name).write_bytes(chunk)
            self.parts.append({'name': name, 'bytes': len(chunk), 'sha256': sha(chunk)})
        self.manifest = {
            'native_archive_parts': self.parts, 'archive_bytes': len(self.archive),
            'archive_sha256': sha(self.archive), 'native_extracted_name': 'Sunward.blend',
            'uncompressed_blend_bytes': len(self.payload), 'uncompressed_blend_sha256': sha(self.payload),
        }
        self.save_manifest()
        self.target = self.root / 'build' / 'Sunward.blend'

    def tearDown(self):
        extractor.HERE = self.original_here
        self.directory.cleanup()

    def save_manifest(self):
        (self.root / 'MANIFEST.json').write_text(json.dumps(self.manifest))

    def assert_clean_failure(self):
        self.assertFalse(self.target.exists())
        self.assertEqual(list(self.root.rglob('*.extracting-*')), [])

    def test_exact_multichunk_extraction_and_repeat(self):
        self.assertEqual(extractor.extract_source()['status'], 'created')
        self.assertEqual(self.target.read_bytes(), self.payload)
        self.assertEqual(extractor.extract_source()['status'], 'verified-existing')

    def test_different_existing_file_is_never_replaced(self):
        self.target.parent.mkdir()
        self.target.write_bytes(b'local edits')
        with self.assertRaises(FileExistsError):
            extractor.extract_source()
        self.assertEqual(self.target.read_bytes(), b'local edits')

    def test_output_symlink_is_never_replaced(self):
        original = self.root / 'original.blend'
        original.write_bytes(self.payload)
        self.target.parent.mkdir()
        self.target.symlink_to(original)
        with self.assertRaises(FileExistsError):
            extractor.extract_source()
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(original.read_bytes(), self.payload)

    def test_input_symlink_is_rejected(self):
        part = self.root / self.parts[0]['name']
        original = self.root / 'original.part'
        part.rename(original)
        part.symlink_to(original)
        with self.assertRaisesRegex(ValueError, 'regular local file'):
            extractor.extract_source()
        self.assert_clean_failure()

    def test_tampered_part_is_rejected(self):
        (self.root / self.parts[0]['name']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'differs from the manifest'):
            extractor.extract_source()
        self.assert_clean_failure()

    def test_reordered_parts_are_rejected(self):
        self.manifest['native_archive_parts'] = list(reversed(self.parts))
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'ordered archive parts'):
            extractor.extract_source()
        self.assert_clean_failure()

    def test_parent_path_in_part_name_is_rejected(self):
        self.parts[0]['name'] = '../outside.part'
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'simple local names'):
            extractor.extract_source()
        self.assert_clean_failure()

    def test_native_path_cannot_escape_the_default_build_directory(self):
        self.manifest['native_extracted_name'] = '../outside.blend'
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'simple local names'):
            extractor.extract_source()
        self.assert_clean_failure()

    def test_wrong_decoded_hash_cleans_temporary_output(self):
        self.manifest['uncompressed_blend_sha256'] = '0' * 64
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'exact accepted bytes'):
            extractor.extract_source()
        self.assert_clean_failure()

    def test_decoded_output_is_bounded(self):
        self.manifest['uncompressed_blend_bytes'] = 1
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            extractor.extract_source()
        self.assert_clean_failure()

    def test_truncated_xz_cleans_temporary_output(self):
        part = self.root / self.parts[-1]['name']
        data = part.read_bytes()[:-5]
        part.write_bytes(data)
        self.parts[-1].update(bytes=len(data), sha256=sha(data))
        self.manifest.update(archive_bytes=len(self.archive) - 5, archive_sha256=sha(self.archive[:-5]))
        self.save_manifest()
        with self.assertRaises((EOFError, lzma.LZMAError)):
            extractor.extract_source()
        self.assert_clean_failure()

    def test_concurrent_output_creation_is_not_overwritten(self):
        def competing_writer(source, destination):
            Path(destination).write_bytes(b'concurrent local edits')
            raise FileExistsError('another writer created the target')
        with patch.object(extractor.os, 'link', side_effect=competing_writer):
            with self.assertRaises(FileExistsError):
                extractor.extract_source()
        self.assertEqual(self.target.read_bytes(), b'concurrent local edits')
        self.assertEqual(list(self.root.rglob('*.extracting-*')), [])


if __name__ == '__main__':
    unittest.main()
