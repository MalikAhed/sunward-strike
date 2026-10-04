import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import build


def sha(data):
    return hashlib.sha256(data).hexdigest()


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.source = self.root / 'native.blend'
        self.source.write_bytes(b'BLENDER native source fixture')
        self.output = self.root / 'exports'
        self.source_patch = patch.object(build, 'extract_source', return_value={'path': str(self.source)})
        self.source_patch.start()

    def tearDown(self):
        self.source_patch.stop()
        self.directory.cleanup()

    def write_exports(self):
        self.output.mkdir()
        payload = b'{"asset":{"version":"2.0"}}'
        payload += b' ' * (-len(payload) % 4)
        raw = struct.pack('<III', 0x46546c67, 2, 20 + len(payload)) + struct.pack('<II', len(payload), 0x4e4f534a) + payload
        files = {f'sunward-v{build.VERSION}.glb': raw, f'sunward-collision-v{build.VERSION}.glb': raw,
                 f'sunward-v{build.VERSION}.glb.gz': gzip.compress(raw, mtime=0)}
        for name, data in files.items():
            (self.output / name).write_bytes(data)
        self.report = {'source_sha256': sha(self.source.read_bytes()), 'source_bytes_unchanged': True,
                       'outputs': [{'file': name, 'bytes': len(data), 'sha256': sha(data)} for name, data in files.items()]}
        self.save_report()

    def save_report(self):
        (self.output / 'export-report.json').write_text(json.dumps(self.report))

    def run_build(self):
        build.main(['--export', '--output-dir', str(self.output)])

    def test_explicit_exporter_failure_propagates(self):
        with patch.object(build.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'blender')) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                self.run_build()
        command = run.call_args.args[0]
        self.assertLess(command.index('--python-exit-code'), command.index('-P'))
        self.assertEqual(command[command.index('--python-exit-code') + 1], '1')
        self.assertTrue(run.call_args.kwargs['check'])

    def test_zero_exit_without_report_is_rejected(self):
        with patch.object(build.subprocess, 'run'):
            with self.assertRaisesRegex(ValueError, 'export-report'):
                self.run_build()

    def test_zero_exit_with_invalid_report_is_rejected(self):
        def incomplete_export(*args, **kwargs):
            self.write_exports()
            self.report['outputs'][0]['sha256'] = '0' * 64
            self.save_report()
        with patch.object(build.subprocess, 'run', side_effect=incomplete_export):
            with self.assertRaisesRegex(ValueError, 'differs from the export report'):
                self.run_build()

    def test_exact_report_assets_and_gzip_are_accepted(self):
        with patch.object(build.subprocess, 'run', side_effect=lambda *a, **k: self.write_exports()):
            self.run_build()

    def test_old_report_is_not_reused_after_a_failed_request(self):
        self.write_exports()
        with patch.object(build.subprocess, 'run') as run:
            with self.assertRaises(FileExistsError):
                self.run_build()
        run.assert_not_called()

    def test_missing_asset_and_bad_decoded_gzip_are_rejected(self):
        self.write_exports()
        row = self.report['outputs'][-1]
        data = gzip.compress(b'not the raw map', mtime=0)
        (self.output / row['file']).write_bytes(data)
        row.update(bytes=len(data), sha256=sha(data))
        self.save_report()
        with self.assertRaisesRegex(ValueError, 'Gzip map'):
            build.verify_export(self.output, self.source)
        (self.output / row['file']).unlink()
        with self.assertRaisesRegex(ValueError, 'missing or is a link'):
            build.verify_export(self.output, self.source)


if __name__ == '__main__':
    unittest.main()
