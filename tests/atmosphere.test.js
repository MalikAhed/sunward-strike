import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import * as THREE from 'three';
import { applyReferencePalette, createClouds, createSky } from '../src/atmosphere.js';
import { MAP_CONFIG } from '../src/map-config.js';
import {decodeGlbBytes} from '../src/asset-loader.js';
import { shaderSources } from './helpers/shader-sources.js';

const paintNames = MAP_CONFIG.paintMaterials;
const mapBytes = Buffer.from(await decodeGlbBytes(readFileSync(new URL(`../public/assets/${MAP_CONFIG.assets.map}`, import.meta.url))));
const sourceMap = JSON.parse(mapBytes.subarray(20, 20 + mapBytes.readUInt32LE(12)).toString());
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

test('all plaster shaders use a valid, versioned paint-layer program', () => {
  for (const name of paintNames) {
    const material = painted(name);
    const sources = shaderSources(material);
    assert.match(sources.vertex, /vArtWorld=/);
    assert.match(sources.fragment, /float artPaintVariation=artHash/);
    assert.doesNotMatch(sources.fragment, /\bfloat\s+patch\b/);
    assert.equal(material.customProgramCacheKey(), 'sunward-art-layer-paint-v2');
  }
});

test('atmosphere keeps authored blue/cream colors and fuller cloud silhouettes', () => {
  const sky = createSky();
  assert.equal(sky.material.toneMapped, false);
  assert.equal(sky.material.uniforms.topColor.value.getHexString(), '478ed8');
  assert.equal(sky.material.uniforms.bottomColor.value.getHexString(), '94c6ec');
  const clouds = createClouds();
  assert.equal(clouds.children.length, 12);
  clouds.traverse(object => {
    if (!object.isMesh) return;
    assert.equal(object.material.toneMapped, false);
    assert.equal(object.parent.children.length, 1, 'Each cluster is one smoothly joined surface');
    assert.ok(object.geometry.userData.triangleCount < 8000, 'Cloud topology stays bounded');
    const size = object.geometry.boundingBox.getSize(new THREE.Vector3());
    assert.ok(size.y / size.x > .55, 'Cumulus mass retains vertical volume');
    assert.equal(object.material.uniforms.cream.value.getHexString(), 'fffdf5');
  });
});

test('full renderer-generated GLSL ES shaders compile and link offline', (t) => {
  const programs = [];
  for (const name of [...paintNames, 'V2_Ground_Moss']) {
    for (const shadows of [false, true]) {
      programs.push({ name: `${name}-${shadows ? 'shadowed' : 'low'}`, ...shaderSources(painted(name), shadows) });
    }
  }
  const clouds = createClouds();
  programs.push({ name: 'OriginalCreamCloudLayer', ...shaderSources(clouds.children[0].children[0].material) });
  programs.push({ name: 'OriginalBlueSkyLayer', ...shaderSources(createSky().material) });
  // Prove that this compiler test catches the original missing-wall defect.
  const original = shaderSources(painted(paintNames[0]));
  programs.push({ name: 'reserved-word-negative-control', vertex: original.vertex, fragment: original.fragment.replaceAll('artPaintVariation', 'patch') });
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
