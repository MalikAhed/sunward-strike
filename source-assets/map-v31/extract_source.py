"""Extract the exact editable Blender source without replacing local edits."""
from pathlib import Path
import argparse
import hashlib
import json
import lzma
import os
import uuid

HERE = Path(__file__).resolve().parent

def extract_source(destination=None):
    manifest = json.loads((HERE / 'MANIFEST.json').read_text())
    archive = HERE / manifest['native_archive']
    target = Path(destination) if destination else HERE / 'build' / manifest['native_extracted_name']
    if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest['archive_sha256']:
        raise ValueError('The native-source archive hash does not match its manifest')
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if target.is_file() and not target.is_symlink() and hashlib.sha256(target.read_bytes()).hexdigest() == manifest['uncompressed_blend_sha256']:
            return {'path': str(target), 'status': 'verified-existing'}
        raise FileExistsError(f'Refusing to overwrite an existing file or link: {target}')
    temporary = target.with_name(target.name + '.extracting-' + uuid.uuid4().hex)
    digest = hashlib.sha256()
    count = 0
    try:
        with lzma.open(archive, 'rb') as source, temporary.open('xb') as output:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
                count += len(chunk)
        if count != manifest['uncompressed_blend_bytes'] or digest.hexdigest() != manifest['uncompressed_blend_sha256']:
            raise ValueError('Decoded native source does not match its exact accepted bytes')
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return {'path': str(target), 'status': 'created', 'bytes': count, 'sha256': digest.hexdigest()}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print(json.dumps(extract_source(args.output), indent=2))
