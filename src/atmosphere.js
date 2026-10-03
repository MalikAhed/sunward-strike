import * as THREE from 'three';
import {MAP_CONFIG} from './map-config.js';
import {ATMOSPHERE_CONFIG as CONFIG} from './atmosphere-config.js';
export {ATMOSPHERE_CONFIG} from './atmosphere-config.js';

// Authored images are original generated art, not supplied-reference pixels.
// The same spherical cards, UVs, source sRGB textures and placements are exported
// for native Blender QA. Map material paint code below is unchanged.
const vertexShader=`varying vec2 vAtlasUv; varying vec3 vSkyDirection;
  void main(){vAtlasUv=uv;vec4 relative=modelMatrix*vec4(position,1.0);
    vSkyDirection=relative.xyz; relative.xyz+=cameraPosition;
    gl_Position=projectionMatrix*viewMatrix*relative;
    gl_Position.z=gl_Position.w*${CONFIG.backgroundDepth.toFixed(5)};}`;

function assetTexture(name, options={}) {
  const baseUrl=options.baseUrl ?? import.meta.env?.BASE_URL ?? './';
  const url=`${baseUrl}${baseUrl.endsWith('/')?'':'/'}assets/${name}`;
  // A caller-provided texture supports deterministic non-browser compiler tests.
  if(options.textures?.[name])return options.textures[name];
  const texture=new THREE.TextureLoader(options.loadingManager).load(url,
    ()=>options.onLoad?.(name),undefined,
    error=>{options.onError?.(name,error);console.warn(`Distant scenery texture unavailable: ${name}`,error);});
  texture.name=name;texture.colorSpace=THREE.SRGBColorSpace;
  texture.wrapS=texture.wrapT=THREE.ClampToEdgeWrapping;
  texture.generateMipmaps=true;texture.minFilter=THREE.LinearMipmapLinearFilter;
  texture.magFilter=THREE.LinearFilter;texture.anisotropy=4;
  return texture;
}
export function createSky(){
  const c=CONFIG.colors;
  const material=new THREE.ShaderMaterial({
    name:'DistantAzureSky_n5', side:THREE.BackSide,depthWrite:false,fog:false,
    toneMapped:false,dithering:true,
    uniforms:{zenith:{value:new THREE.Color(c.zenith)},middle:{value:new THREE.Color(c.middle)},horizon:{value:new THREE.Color(c.horizon)},nadir:{value:new THREE.Color(c.nadir)}},
    vertexShader,
    fragmentShader:`#include <common>
      #include <dithering_pars_fragment>
      uniform vec3 zenith;uniform vec3 middle;uniform vec3 horizon;uniform vec3 nadir;
      varying vec3 vSkyDirection;
      void main(){float e=normalize(vSkyDirection).y;
        vec3 color=mix(horizon,middle,smoothstep(0.0,.35,e));
        color=mix(color,zenith,smoothstep(.2,.9,e));
        color=mix(nadir,color,smoothstep(-.15,.025,e));
        gl_FragColor=vec4(color,1.0);
        #include <colorspace_fragment>
        #include <dithering_fragment>
      }`
  });
  const sky=new THREE.Mesh(new THREE.SphereGeometry(CONFIG.skyRadius,48,32),material);
  sky.name='DistantAzureSkyLayer_n5';sky.frustumCulled=false;sky.renderOrder=-1000;
  sky.userData.cameraCentered=true;sky.userData.version=CONFIG.version;
  return sky;
}
function cardMaterial(texture,name){
  return new THREE.ShaderMaterial({name,uniforms:{atlas:{value:texture}},
    transparent:true,depthWrite:false,depthTest:true,side:THREE.DoubleSide,
    toneMapped:false,fog:false,dithering:true,
    vertexShader,
    fragmentShader:`#include <common>
      #include <dithering_pars_fragment>
      uniform sampler2D atlas;varying vec2 vAtlasUv;
      void main(){vec4 texel=texture2D(atlas,vAtlasUv);if(texel.a<.025)discard;
        gl_FragColor=texel;
        #include <colorspace_fragment>
        #include <dithering_fragment>
      }`
  });
}
// Spherical arc rather than view-facing rectangles: no billboard turning,
// perspective shear, changing elevation, equirectangular seam or polar squeeze.
export function sphericalCard({azimuth,elevation,width,height,rect,radius=CONFIG.radius}){
  const h=16,v=4,positions=[],uvs=[],indices=[],rad=Math.PI/180;
  for(let j=0;j<=v;j++)for(let i=0;i<=h;i++){
    const u=i/h,t=j/v,a=(azimuth+(u-.5)*width)*rad,e=(elevation+(t-.5)*height)*rad;
    positions.push(radius*Math.sin(a)*Math.cos(e),radius*Math.sin(e),radius*Math.cos(a)*Math.cos(e));
    uvs.push((rect[0]+u*(rect[2]-rect[0]))/CONFIG.textureSize[0],1-(rect[3]-t*(rect[3]-rect[1]))/CONFIG.textureSize[1]);
    if(i<h&&j<v){const k=j*(h+1)+i;indices.push(k,k+1,k+h+2,k,k+h+2,k+h+1);}
  }
  const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));geometry.setAttribute('uv',new THREE.Float32BufferAttribute(uvs,2));geometry.setIndex(indices);geometry.computeVertexNormals();geometry.computeBoundingSphere();
  return geometry;
}
export function createClouds(options={}){
  const group=new THREE.Group();group.name='DistantPaintedClouds_n5';
  const material=cardMaterial(assetTexture(CONFIG.cloudTexture,options),'CreamLavenderClouds_n5');
  for(let i=0;i<CONFIG.clouds.length;i++){
    const cloud=CONFIG.clouds[i],rect=CONFIG.cloudRects[cloud.sprite],height=cloud.width*(rect[3]-rect[1])/(rect[2]-rect[0]);
    const mesh=new THREE.Mesh(sphericalCard({...cloud,height,rect,radius:CONFIG.radius-i*.015}),material);
    mesh.name=`DistantCloudBank_${i.toString().padStart(2,'0')}`;mesh.frustumCulled=false;mesh.renderOrder=1;
    mesh.userData={profile:'distant-painterly-bank',...cloud,height};group.add(mesh);
  }
  group.userData={cameraCentered:true,version:CONFIG.version,textureBytesDecoded:1536*1024*4};return group;
}
export function createScenery(options={}){
  const group=new THREE.Group();group.name='DistantPeachMountainHorizon_n5';
  const material=cardMaterial(assetTexture(CONFIG.mountainTexture,options),'PeachLavenderHorizon_n5');
  for(let i=0;i<CONFIG.mountains.length;i++){
    const ridge=CONFIG.mountains[i],rect=CONFIG.mountainRects[ridge.sprite];
    const mesh=new THREE.Mesh(sphericalCard({...ridge,elevation:ridge.base+ridge.height/2,rect,radius:CONFIG.radius-2-i*2}),material);
    mesh.name=`DistantMountainRange_${i.toString().padStart(2,'0')}`;mesh.frustumCulled=false;mesh.renderOrder=2;
    mesh.userData={profile:'distant-mountain-range',...ridge};group.add(mesh);
  }
  group.userData={cameraCentered:true,version:CONFIG.version,textureBytesDecoded:1536*1024*4};return group;
}

export function applyReferencePalette(root){
  const materials=new Set();root.traverse(o=>{if(o.isMesh)for(const m of Array.isArray(o.material)?o.material:[o.material])materials.add(m);});
  for(const material of materials){
    if(material.name.startsWith('V2_Leaf_')){material.color.multiply(new THREE.Color().setRGB(1.16,1.07,.80));material.roughness=.96;}
    if(material.name==='V2_Ground_Moss'){installColorLayer(material,'foliage');}
    if(MAP_CONFIG.paintMaterials.includes(material.name)){installColorLayer(material,'paint');}
  }
}
function installColorLayer(material,kind){
  material.onBeforeCompile=(shader)=>{
    shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 vArtWorld;');
    shader.vertexShader=shader.vertexShader.replace('#include <worldpos_vertex>','#include <worldpos_vertex>\nvArtWorld=(modelMatrix*vec4(transformed,1.0)).xyz;');
    shader.fragmentShader=shader.fragmentShader.replace('#include <common>','#include <common>\nvarying vec3 vArtWorld;\nfloat artHash(vec3 p){return fract(sin(dot(p,vec3(127.1,311.7,74.7)))*43758.5453);}');
    // `patch` is reserved in GLSL ES 3.00; using it makes only plaster
    // programs fail to compile, leaving roofs and frames visibly floating.
    const layer=kind==='foliage'?'diffuseColor.rgb*=vec3(1.16,1.08,.76);':`vec3 artCell=floor(vArtWorld*1.2);float artDiagonal=step(fract(vArtWorld.x*1.2),fract(vArtWorld.y*1.2));float artPaintVariation=artHash(artCell+artDiagonal);diffuseColor.rgb*=.965+artPaintVariation*.07;`;
    shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>','#include <color_fragment>\n'+layer);
  };
  material.customProgramCacheKey=()=>`sunward-art-layer-${kind}-v2`;
  material.needsUpdate=true;
}
