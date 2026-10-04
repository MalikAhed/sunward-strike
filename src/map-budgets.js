// Explicit provisional engineering caps, not measured device performance.
// Later allowances never silently enlarge an earlier release's contract.
const common = {triangles:400000,meshes:1500,primitives:1800,bytes:32000000,texture_rgba_bytes:128*1024*1024};
const versions = Object.freeze({
  '3.0': Object.freeze({...common,materials:80,images:24,gzip_bytes:8000000}),
  '3.1': Object.freeze({...common,materials:80,images:24,gzip_bytes:8500000}),
  // One original short-turf MASK atlas; the material cap stays unchanged.
  '3.2': Object.freeze({...common,materials:80,images:25,gzip_bytes:8500000}),
});

export function mapBudgets(version) {
  const result=versions[version];
  if(!result)throw new RangeError('No approved map budget for version '+version);
  return result;
}

export function mapBudgetVersion(asset,fallbackVersion) {
  const match=String(asset).replaceAll('\\','/').split('/').at(-1).match(/^sunward-v([\d.]+)\.glb(?:\.gz)?$/);
  const version=match?match[1]:fallbackVersion;
  mapBudgets(version);
  return version;
}
