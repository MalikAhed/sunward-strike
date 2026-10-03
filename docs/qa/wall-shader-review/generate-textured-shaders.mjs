import fs from 'node:fs';
import * as THREE from 'three';
import { applyReferencePalette } from '../../../src/atmosphere.js';
import { shaderSources } from '../../../tests/helpers/shader-sources.js';
const bytes=fs.readFileSync(new URL('../../../public/assets/sunward-v2.5.glb',import.meta.url));
const jsonLength=bytes.readUInt32LE(12); const gltf=JSON.parse(bytes.subarray(20,20+jsonLength));
const programs=[];
for(const source of gltf.materials.filter(m=>['V2_Warm_Plaster','V2_Sage_Plaster','V2_Saffron_Plaster'].includes(m.name))){
 const material=new THREE.MeshStandardMaterial({side:source.doubleSided?THREE.DoubleSide:THREE.FrontSide,metalness:source.pbrMetallicRoughness?.metallicFactor??1,roughness:source.pbrMetallicRoughness?.roughnessFactor??1});
 material.name=source.name;
 if(source.pbrMetallicRoughness?.baseColorTexture){ material.map=new THREE.Texture(); material.map.colorSpace=THREE.SRGBColorSpace; material.map.channel=source.pbrMetallicRoughness.baseColorTexture.texCoord??0; }
 if(source.normalTexture){ material.normalMap=new THREE.Texture();material.normalMap.channel=source.normalTexture.texCoord??0; material.normalMapType=THREE.TangentSpaceNormalMap;material.normalScale.setScalar(source.normalTexture.scale??1); }
 const group=new THREE.Group();group.add(new THREE.Mesh(new THREE.BoxGeometry(),material));applyReferencePalette(group);
 for(const shadows of [false,true]){const generated=shaderSources(material,shadows);if(!generated.fragment.includes('#define USE_MAP')||!generated.fragment.includes('#define USE_NORMALMAP'))throw new Error('Expected textured material macros absent');programs.push({name:material.name+(shadows?'-textured-shadowed':'-textured-low'),...generated});}
}
const negative=structuredClone(programs[1]);negative.name='textured-reserved-word-negative-control';negative.fragment=negative.fragment.replaceAll('artPaintVariation','patch');programs.push(negative);
process.stdout.write(JSON.stringify(programs));
