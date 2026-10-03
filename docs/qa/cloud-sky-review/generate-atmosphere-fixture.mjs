import fs from 'node:fs';
import * as THREE from 'three';
import {createClouds, createSky} from '../../../src/atmosphere.js';
import {shaderSources} from '../../../tests/helpers/shader-sources.js';

const scene = new THREE.Scene();
scene.add(createSky(), createClouds());
scene.updateMatrixWorld(true);
const camera = new THREE.PerspectiveCamera(58, 1365/768, .05, 500);
camera.position.set(0,3,0);camera.lookAt(-30,12,-100);camera.updateMatrixWorld(true);
const fixture={width:1365,height:768,projection:camera.projectionMatrix.elements,view:camera.matrixWorldInverse.elements,geometries:[],programs:[],meshes:[]};
const geometryIds=new Map(), materialIds=new Map();
scene.traverse(object=>{
  if(!object.isMesh)return;
  let geometryId=geometryIds.get(object.geometry);
  if(geometryId===undefined){geometryId=fixture.geometries.length;geometryIds.set(object.geometry,geometryId);fixture.geometries.push({position:Array.from(object.geometry.attributes.position.array),normal:Array.from(object.geometry.attributes.normal.array),index:object.geometry.index?Array.from(object.geometry.index.array):null});}
  let materialId=materialIds.get(object.material);
  if(materialId===undefined){materialId=fixture.programs.length;materialIds.set(object.material,materialId);const uniforms={};for(const [name,uniform] of Object.entries(object.material.uniforms))uniforms[name]=uniform.value.isColor?[uniform.value.r,uniform.value.g,uniform.value.b]:uniform.value.toArray();fixture.programs.push({name:object.material.name,...shaderSources(object.material),uniforms});}
  const modelView=new THREE.Matrix4().multiplyMatrices(camera.matrixWorldInverse,object.matrixWorld);
  const normal=new THREE.Matrix3().getNormalMatrix(modelView);
  fixture.meshes.push({geometry:geometryId,program:materialId,model:object.matrixWorld.elements,modelView:modelView.elements,normal:normal.elements});
});
fs.writeFileSync(new URL('./fixture.json',import.meta.url),JSON.stringify(fixture));
console.log(`Captured ${fixture.programs.length} authored programs, ${fixture.meshes.length} atmosphere meshes`);
