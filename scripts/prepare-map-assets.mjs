#!/usr/bin/env node
// Only gzip is committed. Vite copies this exact generated raw compatibility
// asset into dist; never overwrite a local export that differs from the gzip.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createHash, randomUUID} from 'node:crypto';
import {MAP_CONFIG} from '../src/map-config.js';
import {decodeGlbBytes} from '../src/asset-loader.js';

const projectRoot = fileURLToPath(new URL('../', import.meta.url));
export async function prepareMapAssets({
  assetsDirectory = path.join(projectRoot, 'public/assets'),
  mapFilename = MAP_CONFIG.assets.map,
  expectedDecodedSha256 = MAP_CONFIG.decodedMapSha256,
} = {}) {
  if (!/^[\w.-]+\.glb\.gz$/.test(mapFilename)) throw new Error('Expected a gzip GLB filename without directory components.');
  const gzipPath = path.join(assetsDirectory, mapFilename);
  const rawPath = gzipPath.slice(0, -3);
  const compressed = await fs.readFile(gzipPath);
  if (compressed[0] !== 0x1f || compressed[1] !== 0x8b) throw new Error(`Expected gzip bytes in ${gzipPath}`);
  const decoded = Buffer.from(await decodeGlbBytes(compressed));
  const decodedSha256 = createHash('sha256').update(decoded).digest('hex');
  if (!expectedDecodedSha256 || decodedSha256 !== expectedDecodedSha256) {
    throw new Error(`Decoded map SHA-256 differs from map-config.js (${decodedSha256}). No raw asset was written.`);
  }
  async function verifyExisting() {
    const stat = await fs.lstat(rawPath);
    if (!stat.isFile()) throw new Error(`Refusing to replace non-regular raw asset: ${rawPath}`);
    if (stat.size !== decoded.length || !(await fs.readFile(rawPath)).equals(decoded)) {
      throw new Error(`Existing raw map differs from the committed gzip: ${rawPath}. Preserve those local edits and reconcile the export explicitly; it was not overwritten.`);
    }
  }
  let action;
  try {
    await verifyExisting();
    action = 'verified-existing';
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    // Publish a complete file atomically without replacing anything. A second
    // build can then verify the winner; it can never observe a partial write.
    const temporaryPath = `${rawPath}.preparing-${randomUUID()}`;
    try {
      await fs.writeFile(temporaryPath, decoded, {flag: 'wx'});
      try {
        await fs.link(temporaryPath, rawPath);
        action = 'created';
      } catch (linkError) {
        if (linkError.code !== 'EEXIST') throw linkError;
        await verifyExisting();
        action = 'verified-existing';
      }
    } finally {
      await fs.rm(temporaryPath, {force: true});
    }
  }
  return {action, gzipPath, rawPath, gzipBytes: compressed.length, decodedBytes: decoded.length, decodedSha256};
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  try {
    console.log(JSON.stringify(await prepareMapAssets(), null, 2));
  } catch (error) {
    console.error(`Map asset preparation failed: ${error.message}`);
    process.exitCode = 1;
  }
}
