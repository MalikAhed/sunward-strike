"""Extract verified native source, optionally exporting fresh runtime assets."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import os
import struct
import subprocess
from extract_source import extract_source

HERE = Path(__file__).resolve().parent
VERSION = '3.3'


def verify_export(directory, source):
    report_path = directory / 'export-report.json'
    if report_path.is_symlink() or not report_path.is_file():
        raise ValueError('Blender did not produce a regular export-report.json')
    report = json.loads(report_path.read_text())
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if report.get('source_sha256') != source_hash or report.get('source_bytes_unchanged') is not True:
        raise ValueError('Export report does not verify the exact unchanged native source')
    names = [f'sunward-v{VERSION}.glb', f'sunward-collision-v{VERSION}.glb', f'sunward-v{VERSION}.glb.gz']
    rows = report.get('outputs', [])
    if len(rows) != 3 or sorted(row.get('file', '') for row in rows) != sorted(names):
        raise ValueError('Export report does not contain the three expected output files')
    payloads = {}
    for row in rows:
        path = directory / row['file']
        if path.is_symlink() or not path.is_file():
            raise ValueError('An expected exported asset is missing or is a link')
        data = path.read_bytes()
        if len(data) != row.get('bytes') or hashlib.sha256(data).hexdigest() != row.get('sha256'):
            raise ValueError('An exported asset differs from the export report: ' + row['file'])
        if path.suffix == '.glb' and (len(data) < 20 or struct.unpack('<III', data[:12]) != (0x46546c67, 2, len(data))):
            raise ValueError('An exported asset is not a declared-length GLB2 file')
        payloads[row['file']] = data
    if gzip.decompress(payloads[names[2]]) != payloads[names[0]]:
        raise ValueError('Gzip map does not decode to the exact exported raw map')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', default='blender')
    parser.add_argument('--export', action='store_true')
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args(argv)
    if args.output_dir and not args.export:
        parser.error('--output-dir requires --export')
    native = extract_source()
    if args.export:
        directory = (args.output_dir or HERE / 'build' / 'exports').resolve()
        report_path = directory / 'export-report.json'
        if report_path.exists() or report_path.is_symlink():
            raise FileExistsError('Refusing to reuse a previous export report: ' + str(report_path))
        command = [args.blender, '-b', native['path'], '-t', '2', '--python-exit-code', '1',
                   '-P', str(HERE / 'export_map.py'), '--', '--output-dir', str(directory), '--version', VERSION]
        environment = dict(os.environ, LP_NUM_THREADS='2', OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2')
        subprocess.run(command, check=True, env=environment)
        verify_export(directory, Path(native['path']))
        print('Verified runtime exports:', directory)
    print('Verified editable source:', native['path'])


if __name__ == '__main__':
    main()
