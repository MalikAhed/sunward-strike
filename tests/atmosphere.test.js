import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import * as THREE from 'three';
import { applyReferencePalette, createClouds, createSky, ATMOSPHERE_CONFIG } from '../src/atmosphere.js';
import { MAP_CONFIG } from '../src/map-config.js';
import {decodeGlbBytes} from '../src/asset-loader.js';
import { shaderSources } from './helpers/shader-sources.js';

const bakedPrefixes = MAP_CONFIG.style.bakedMaterialPrefixes;
const textures=Object.fromEntries([ATMOSPHERE_CONFIG.cloudTexture,ATMOSPHERE_CONFIG.mountainTexture].map(name=>[name,new THREE.Texture()]));
const mapBytes = Buffer.from(await decodeGlbBytes(readFileSync(new URL(`../public/assets/${MAP_CONFIG.assets.map}`, import.meta.url))));
const sourceMap = JSON.parse(mapBytes.subarray(20, 20 + mapBytes.readUInt32LE(12)).toString());
const paintNames = sourceMap.materials.map(material=>material.name).filter(name=>bakedPrefixes.some(prefix=>name.startsWith(prefix)));
const representativeNames = ['V3_Tone_Turquoise_Plaster_p1r5','V3_Tone_SunnyYellow_Plaster_p1r5','V3_Tone_Cream_Plaster_p1r5','V3_Tone_Honey_Timber_p1r5','V3_Tone_Warm_SandGround_p1r5','V4R5_Canopy_LeafAtlas','V4R5_Lawn_Blade_0','D3_Rug_Pattern_0','D3_Fabric_Warm_Yellow'];
function painted(name) {
  const source = sourceMap.materials.find(material => material.name === name);
  assert.ok(source, `Current map must contain material ${name}`);
  const pbr = source.pbrMetallicRoughness;
  const material = new THREE.MeshStandardMaterial({
    side: source.doubleSided ? THREE.DoubleSide : THREE.FrontSide,
    metalness: pbr.metallicFactor,
    roughness: pbr.roughnessFactor,
    normalMapType: THREE.TangentSpaceNormalMap,
  });
  // Preserve actual GLB texture flags without decoding images: shader source
  // depends on their presence/channel, not on the texel values.
  if (pbr.baseColorTexture) {
    material.map = new THREE.Texture();
    material.map.channel = pbr.baseColorTexture.texCoord || 0;
    material.map.colorSpace = THREE.SRGBColorSpace;
  }
  if (source.normalTexture) {
    material.normalMap = new THREE.Texture();
    material.normalMap.channel = source.normalTexture.texCoord || 0;
    material.normalScale.setScalar(source.normalTexture.scale ?? 1);
  }
  material.name = name;
  const root = new THREE.Group();
  root.add(new THREE.Mesh(new THREE.BoxGeometry(), material));
  applyReferencePalette(root);
  return material;
}

test('all actual baked style surfaces remain untinted by legacy runtime layers', () => {
  assert.deepEqual(MAP_CONFIG.paintMaterials,[]);assert.equal(MAP_CONFIG.style.materialsBaked,true);assert.ok(paintNames.length>30);
  for(const name of paintNames){const material=painted(name),sources=shaderSources(material);assert.doesNotMatch(sources.fragment,/float artPaintVariation=artHash/);assert.doesNotMatch(sources.fragment,/\bfloat\s+patch\b/);assert.doesNotMatch(material.customProgramCacheKey(),/sunward-art-layer/);}
});

test('accepted n5 keeps distant azure sky and bounded cloud atlas cards', () => {
  const sky=createSky(),clouds=createClouds({textures});
  assert.equal(sky.material.toneMapped,false);assert.equal(sky.material.uniforms.zenith.value.getHexString(),'3287e2');
  assert.equal(clouds.children.length,12);
  for(const cloud of clouds.children){assert.equal(cloud.material.toneMapped,false);assert.ok(cloud.geometry.index.count/3<8000);assert.equal(cloud.frustumCulled,false);}
});

test('full renderer-generated GLSL ES shaders compile and link offline', (t) => {
  const programs = [];
  for (const name of representativeNames) {
    for (const shadows of [false, true]) {
      programs.push({ name: `${name}-${shadows ? 'shadowed' : 'low'}`, ...shaderSources(painted(name), shadows) });
    }
  }
  const clouds = createClouds({textures});
  programs.push({ name: 'OriginalCreamCloudLayer', ...shaderSources(clouds.children[0].material) });
  programs.push({ name: 'OriginalBlueSkyLayer', ...shaderSources(createSky().material) });
  // Prove that this compiler test catches the original missing-wall defect.
  const original = shaderSources(painted(representativeNames[0]));
  programs.push({ name: 'reserved-word-negative-control', vertex: original.vertex, fragment: original.fragment.replace('void main() {','void main() { float patch=0.;') });
  const result = spawnSync('python3', [new URL('./helpers/compile-egl.py', import.meta.url).pathname], {
    input: JSON.stringify(programs), encoding: 'utf8', maxBuffer: 1024 * 1024,
  });
  if (result.error?.code === 'ENOENT' || result.status === 77) {
    assert.notEqual(process.env.REQUIRE_SHADER_COMPILER, '1', `Required GLSL compiler unavailable: ${result.error?.message || result.stdout.trim()}`);
    t.skip(`Offline driver compiler unavailable: ${result.error?.message || result.stdout.trim()}`);
    return;
  }
  assert.equal(result.status, 0, result.stderr || result.error?.message);
  const report = JSON.parse(result.stdout);
  for (const item of report.results.slice(0, -1)) {
    assert.equal(item.compiled, true, `${item.name}: ${JSON.stringify(item.errors)}`);
    assert.equal(item.linked, true, item.name);
  }
  const negative = report.results.at(-1);
  assert.equal(negative.compiled, false, 'The original reserved-word bug must fail compilation');
  assert.match(JSON.stringify(negative.errors), /reserved word.*patch/);
  t.diagnostic(`${report.driver}; ${programs.length - 1} production programs compiled/linked; original defect rejected`);
});
