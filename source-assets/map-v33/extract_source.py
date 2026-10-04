"""Extract exact editable Blender bytes from verified, losslessly split XZ parts."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import lzma
import os
import uuid

HERE = Path(__file__).resolve().parent
CHUNK_BYTES = 1024 * 1024


def safe_name(value):
    if not isinstance(value, str) or value in ('', '.', '..') or '/' in value or '\\' in value:
        raise ValueError('Archive and native file names must be simple local names')
    return value


def verified_parts(manifest):
    parts = manifest.get('native_archive_parts')
    if not isinstance(parts, list) or not parts:
        raise ValueError('The manifest must list its ordered native archive parts')
    paths, total, archive_digest = [], 0, hashlib.sha256()
    for part in parts:
        path = HERE / safe_name(part['name'])
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Archive part is not a regular local file: {path.name}')
        digest, count = hashlib.sha256(), 0
        with path.open('rb') as source:
            while chunk := source.read(CHUNK_BYTES):
                digest.update(chunk)
                archive_digest.update(chunk)
                count += len(chunk)
        if count != part['bytes'] or digest.hexdigest() != part['sha256']:
            raise ValueError(f'Archive part differs from the manifest: {path.name}')
        total += count
        paths.append(path)
    if total != manifest['archive_bytes'] or archive_digest.hexdigest() != manifest['archive_sha256']:
        raise ValueError('The ordered archive parts do not reconstruct the exact XZ archive')
    return paths


class JoinedParts(io.RawIOBase):
    """Read verified parts in order without a second joined archive on disk."""
    def __init__(self, paths):
        super().__init__()
        self.paths = iter(paths)
        self.current = None

    def readable(self):
        return True

    def readinto(self, buffer):
        view, count = memoryview(buffer), 0
        while count < len(view):
            if self.current is None:
                path = next(self.paths, None)
                if path is None:
                    break
                self.current = path.open('rb')
            size = self.current.readinto(view[count:])
            if size:
                count += size
            else:
                self.current.close()
                self.current = None
        return count

    def close(self):
        if self.current is not None:
            self.current.close()
            self.current = None
        super().close()


def extract_source(destination=None):
    manifest = json.loads((HERE / 'MANIFEST.json').read_text())
    paths = verified_parts(manifest)
    native_name = safe_name(manifest['native_extracted_name'])
    expected_size = manifest['uncompressed_blend_bytes']
    if not isinstance(expected_size, int) or expected_size <= 0:
        raise ValueError('The manifest must declare a positive native source byte count')
    target = Path(destination) if destination else HERE / 'build' / native_name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if (target.is_file() and not target.is_symlink()
                and target.stat().st_size == expected_size
                and hashlib.sha256(target.read_bytes()).hexdigest() == manifest['uncompressed_blend_sha256']):
            return {'path': str(target), 'status': 'verified-existing'}
        raise FileExistsError(f'Refusing to overwrite an existing file or link: {target}')
    temporary = target.with_name(target.name + '.extracting-' + uuid.uuid4().hex)
    digest, count = hashlib.sha256(), 0
    try:
        with JoinedParts(paths) as raw, io.BufferedReader(raw) as joined, lzma.open(joined, 'rb') as source, temporary.open('xb') as output:
            while chunk := source.read(CHUNK_BYTES):
                count += len(chunk)
                if count > expected_size:
                    raise ValueError('Decoded native source exceeds the exact accepted byte count')
                digest.update(chunk)
                output.write(chunk)
        if count != expected_size or digest.hexdigest() != manifest['uncompressed_blend_sha256']:
            raise ValueError('Decoded native source does not match its exact accepted bytes')
        # Atomic no-replace installation also protects against another writer
        # creating the destination after the initial existence check.
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return {'path': str(target), 'status': 'created', 'bytes': count, 'sha256': digest.hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print(json.dumps(extract_source(args.output), indent=2))
