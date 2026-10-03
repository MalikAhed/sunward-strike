// Generate exactly the GLSL that the pinned Three.js renderer sends to WebGL.
// The mock captures source only; the separate EGL helper does real compilation.
import * as THREE from 'three';
import { WebGLProgram } from 'three/src/renderers/webgl/WebGLProgram.js';
import { WebGLPrograms } from 'three/src/renderers/webgl/WebGLPrograms.js';

export function shaderSources(material, shadows = true) {
  const shaders = [];
  const gl = {
    VERTEX_SHADER: 0x8b31, FRAGMENT_SHADER: 0x8b30,
    createProgram: () => ({}),
    createShader: type => { const shader = { type }; shaders.push(shader); return shader; },
    shaderSource: (shader, source) => { shader.source = source; },
    compileShader() {}, attachShader() {}, linkProgram() {}, bindAttribLocation() {},
  };
  const renderer = {
    getContext: () => gl, getRenderTarget: () => null,
    state: { buffers: { depth: { getReversed: () => false } } },
    shadowMap: { enabled: shadows, type: THREE.PCFSoftShadowMap },
    outputColorSpace: THREE.SRGBColorSpace, toneMapping: THREE.ACESFilmicToneMapping,
  };
  const environment = new THREE.Texture();
  environment.mapping = THREE.CubeUVReflectionMapping;
  environment.image = { height: 256 };
  const scene = { fog: new THREE.FogExp2(0xb8d3d5, .0025), environment };
  const lights = {
    directional: [{}], point: [], spot: [], spotLightMap: [], rectArea: [], hemi: [{}],
    directionalShadowMap: shadows ? [{}] : [], pointShadowMap: [], spotShadowMap: [],
    numSpotLightShadowsWithMaps: 0, numLightProbes: 0,
  };
  const maps = { get: texture => texture };
  const extensions = { has: () => false };
  const capabilities = { precision: 'highp', vertexTextures: true, logarithmicDepthBuffer: false };
  const programs = WebGLPrograms(renderer, maps, maps, extensions, capabilities, {}, { numPlanes: 0, numIntersection: 0 });
  const object = new THREE.Mesh(new THREE.BoxGeometry(), material);
  const parameters = programs.getParameters(material, lights, shadows ? [{}] : [], scene, object);
  material.onBeforeCompile(parameters, renderer);
  new WebGLProgram(renderer, material.customProgramCacheKey(), parameters, {});
  object.geometry.dispose();
  return { vertex: shaders[0].source, fragment: shaders[1].source };
}
