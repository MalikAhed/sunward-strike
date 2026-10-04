import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import { applyReferencePalette, createClouds, createSky, ATMOSPHERE_CONFIG } from '../src/atmosphere.js';
import { MAP_CONFIG } from '../src/map-config.js';
import {decodeGlbBytes} from '../src/asset-loader.js';
import { shaderSources } from './helpers/shader-sources.js';

const bakedPrefixes = MAP_CONFIG.style.bakedMaterialPrefixes;
const textures=Object.fromEntries([ATMOSPHERE_CONFIG.cloudTexture,ATMOSPHERE_CONFIG.mountainTexture].map(name=>[name,new THREE.Texture()]));
const mapBytes = Buffer.from(await decodeGlbBytes(readFileSync(new URL(`../public/assets/${MAP_CONFIG.assets.map}`, import.meta.url))));
const sourceMap = JSON.parse(mapBytes.subarray(20, 20 + mapBytes.readUInt32LE(12)).toString());
const paintNames = sourceMap.materials.map(material=>material.name).filter(name=>bakedPrefixes.some(prefix=>name.startsWith(prefix)));
const turfName=MAP_CONFIG.style.lawnMaterial||'V4R5_Lawn_Blade_0';
const representativeNames = ['V3_Tone_Turquoise_Plaster_p1r5','V3_Tone_SunnyYellow_Plaster_p1r5','V3_Tone_Cream_Plaster_p1r5','V3_Tone_Honey_Timber_p1r5','V3_Tone_Warm_SandGround_p1r5','V4R5_Canopy_LeafAtlas',turfName,'D3_Rug_Pattern_0','D3_Fabric_Warm_Yellow',...sourceMap.materials.filter(material=>material.name.startsWith('V3_Tone_Surface_')).map(material=>material.name)];
// Use the actual glTF material classes/extensions, channels and alpha flags.
// Only texture pixels are placeholders because this is a shader-source/compiler
// gate, not image decoding or browser visual acceptance.
const loader=new GLTFLoader();
loader.register(()=>({name:'SUNWARD_SHADER_TEXTURE_PLACEHOLDERS',loadTexture(){return Promise.resolve(new THREE.Texture());}}));
const actualScene=(await loader.parseAsync(mapBytes.buffer.slice(mapBytes.byteOffset,mapBytes.byteOffset+mapBytes.byteLength),'')).scene;
const actualMaterials=new Map();
actualScene.traverse(object=>{if(object.isMesh)for(const material of Array.isArray(object.material)?object.material:[object.material])actualMaterials.set(material.name,material);});
function painted(name) {
  const source=actualMaterials.get(name);
  assert.ok(source, `Current map must contain material ${name}`);
  const material=source.clone();
  const root=new THREE.Group();root.add(new THREE.Mesh(new THREE.BoxGeometry(),material));
  applyReferencePalette(root);
  return material;
}

test('accepted short turf keeps real MASK flags and all four new house surfaces keep normal maps',()=>{
  assert.equal(turfName,'V6_ShortTurf_OriginalAtlas');
  const source=sourceMap.materials.find(material=>material.name===turfName),turf=painted(turfName);
  assert.equal(source.alphaMode,'MASK');assert.equal(source.alphaCutoff??.5,.5);
  assert.equal(turf.alphaTest,.5);assert.equal(turf.transparent,false);assert.equal(turf.side,THREE.FrontSide);
  assert.ok(turf.map);assert.equal(turf.map.colorSpace,THREE.SRGBColorSpace);
  assert.match(shaderSources(turf).fragment,/#define USE_ALPHATEST/);
  const surfaces=sourceMap.materials.filter(material=>material.name.startsWith('V3_Tone_Surface_'));
  assert.equal(surfaces.length,4);
  for(const source of surfaces){
    const material=painted(source.name);assert.ok(source.normalTexture);assert.ok(material.normalMap);
    assert.equal(material.normalMap.channel,source.normalTexture.texCoord??0);
    assert.ok(Math.abs(material.normalScale.x-(source.normalTexture.scale??1))<1e-6);
    assert.equal(material.alphaTest,0);assert.equal(material.transparent,false);
  }
});

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
  const turf=painted(turfName);
  if(turf.alphaTest>0){
    const depth=new THREE.MeshDepthMaterial({map:turf.map,alphaTest:turf.alphaTest,side:turf.side,depthPacking:THREE.RGBADepthPacking});
    const distance=new THREE.MeshDistanceMaterial({map:turf.map,alphaTest:turf.alphaTest,side:turf.side});
    programs.push({name:turfName+'-masked-depth',...shaderSources(depth,false)});
    programs.push({name:turfName+'-masked-point-distance',...shaderSources(distance,false)});
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
