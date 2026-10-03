// Shared browser/CPU transport: servers may HTTP-decode .gz, so trust bytes.
export class GlbAssetError extends Error {
  constructor(message, code, cause) {
    super(message, {cause});
    this.name = 'GlbAssetError';
    this.code = code;
  }
}

function bytesOf(input) {
  if (input instanceof ArrayBuffer) return new Uint8Array(input);
  if (ArrayBuffer.isView(input)) return new Uint8Array(input.buffer, input.byteOffset, input.byteLength);
  throw new TypeError('GLB payload must be an ArrayBuffer or typed byte view');
}

function isGlb(bytes) {
  return bytes.length >= 4 && bytes[0] === 0x67 && bytes[1] === 0x6c && bytes[2] === 0x54 && bytes[3] === 0x46;
}

function validatedBuffer(bytes) {
  const invalid = () => new GlbAssetError('The map GLB is invalid or the download is incomplete.', 'INVALID_GLB');
  if (!isGlb(bytes) || bytes.length < 20 || bytes.length % 4 !== 0) throw invalid();
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (view.getUint32(4, true) !== 2 || view.getUint32(8, true) !== bytes.length) throw invalid();
  let offset = 12;
  let hasJson = false;
  let hasBinary = false;
  while (offset < bytes.length) {
    if (offset + 8 > bytes.length) throw invalid();
    const length = view.getUint32(offset, true);
    const type = view.getUint32(offset + 4, true);
    if (length % 4 !== 0 || offset + 8 + length > bytes.length) throw invalid();
    if (offset === 12 && (type !== 0x4e4f534a || length < 4)) throw invalid();
    if (type === 0x4e4f534a) {
      if (hasJson) throw invalid();
      hasJson = true;
    }
    if (type === 0x004e4942) {
      if (hasBinary) throw invalid();
      hasBinary = true;
    }
    offset += 8 + length;
  }
  return bytes.byteOffset === 0 && bytes.byteLength === bytes.buffer.byteLength
    ? bytes.buffer
    : bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

export async function decodeGlbBytes(input, {decompressionStream = globalThis.DecompressionStream} = {}) {
  const bytes = bytesOf(input);
  if (isGlb(bytes)) return validatedBuffer(bytes);
  if (bytes.length < 2 || bytes[0] !== 0x1f || bytes[1] !== 0x8b) {
    throw new GlbAssetError('The downloaded map is neither GLB nor gzip data.', 'INVALID_PAYLOAD');
  }
  if (typeof decompressionStream !== 'function') {
    throw new GlbAssetError('This browser cannot unpack the compressed map.', 'GZIP_UNAVAILABLE');
  }
  let decoded;
  try {
    const stream = new globalThis.Blob([bytes]).stream().pipeThrough(new decompressionStream('gzip'));
    decoded = new Uint8Array(await new globalThis.Response(stream).arrayBuffer());
  } catch (cause) {
    throw new GlbAssetError('The compressed map is invalid or incomplete. Please retry the download.', 'INVALID_GZIP', cause);
  }
  return validatedBuffer(decoded);
}

export function rawGlbFallbackUrl(url) {
  const value = String(url);
  const suffixAt = value.search(/[?#]/);
  const pathname = suffixAt < 0 ? value : value.slice(0, suffixAt);
  const suffix = suffixAt < 0 ? '' : value.slice(suffixAt);
  return pathname.replace(/\.gz$/i, '') + suffix;
}

async function responseBytes(response, onProgress) {
  if (!onProgress || !response.body?.getReader) {
    const buffer = await response.arrayBuffer();
    onProgress?.({loaded: buffer.byteLength, total: buffer.byteLength, lengthComputable: true});
    return buffer;
  }
  // HTTP content-length can describe compressed bytes while fetch yields decoded
  // bytes. In that case report an indeterminate count, never a bogus percentage.
  const encoding = response.headers?.get('content-encoding');
  const length = Number(response.headers?.get('content-length'));
  const total = (!encoding || encoding === 'identity') && Number.isSafeInteger(length) && length > 0 ? length : 0;
  const reader = response.body.getReader();
  const chunks = [];
  let loaded = 0;
  try {
    for (;;) {
      const {done, value} = await reader.read();
      if (done) break;
      chunks.push(value);
      loaded += value.byteLength;
      onProgress({loaded, total, lengthComputable: total > 0 && loaded <= total});
    }
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(loaded);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return bytes.buffer;
}

export async function loadGlbBytes(url, {
  fetcher = globalThis.fetch,
  decompressionStream = globalThis.DecompressionStream,
  signal,
  onProgress,
  onStage,
  rawFallbackUrl = rawGlbFallbackUrl(url),
} = {}) {
  if (typeof fetcher !== 'function') throw new GlbAssetError('This browser cannot download the map.', 'FETCH_UNAVAILABLE');
  // Select the generated fallback before fetching so older clients only download
  // one asset. Corrupt gzip and HTTP errors must surface rather than hide damage.
  const requestUrl = typeof decompressionStream !== 'function' && rawFallbackUrl ? String(rawFallbackUrl) : String(url);
  onStage?.('download');
  const response = await fetcher(requestUrl, {signal});
  if (!response.ok) {
    const detail = [response.status, response.statusText].filter(Boolean).join(' ');
    throw new GlbAssetError(`Could not download the map (${detail}).`, 'HTTP_ERROR');
  }
  const bytes = await responseBytes(response, onProgress);
  onStage?.('decode');
  return decodeGlbBytes(bytes, {decompressionStream});
}

// Unlike GLTFLoader.loadAsync, parseAsync does not track the top-level model.
// Keep it pending through parsing and embedded resources, including failed retries.
export async function loadGlbAsset(loader, url, {
  manager = loader.manager,
  resourcePath = String(url).split(/[?#]/)[0].replace(/[^/]*$/, ''),
  onStage,
  ...options
} = {}) {
  manager?.itemStart(url);
  try {
    const bytes = await loadGlbBytes(url, {...options, onStage});
    onStage?.('parse');
    return await loader.parseAsync(bytes, resourcePath);
  } catch (error) {
    manager?.itemError(url);
    throw error;
  } finally {
    manager?.itemEnd(url);
  }
}
