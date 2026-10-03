import * as THREE from 'three';
import { MarchingCubes } from 'three/addons/objects/MarchingCubes.js';

// Original procedural atmosphere inspired by the supplied art-direction sheet.
// This is a separate sky layer; no source map geometry or transforms are edited.
export function createSky(){
  const material=new THREE.ShaderMaterial({
    name:'OriginalBlueSkyMaterial',
    side:THREE.BackSide,
    depthWrite:false,
    dithering:true,
    // Authored sky/cloud colors are display-referred. Exposure/tone mapping
    // belongs to the lit map and otherwise washes this blue horizon to grey.
    toneMapped:false,
    uniforms:{topColor:{value:new THREE.Color('#478ed8')},bottomColor:{value:new THREE.Color('#94c6ec')}},
    vertexShader:`varying vec3 vSkyWorld;
      void main(){vec4 world=modelMatrix*vec4(position,1.0);vSkyWorld=world.xyz;gl_Position=projectionMatrix*viewMatrix*world;}`,
    fragmentShader:`#include <common>
      #include <dithering_pars_fragment>
      uniform vec3 topColor;uniform vec3 bottomColor;varying vec3 vSkyWorld;
      void main(){float elevation=normalize(vSkyWorld).y;float gradient=smoothstep(-.08,.72,elevation);gl_FragColor=vec4(mix(bottomColor,topColor,gradient),1.0);
      #include <colorspace_fragment>
      #include <dithering_fragment>
      }`
  });
  const sky=new THREE.Mesh(new THREE.SphereGeometry(400,24,16),material);
  sky.name='OriginalBlueSkyLayer';sky.frustumCulled=false;
  return sky;
}

export function createClouds(){
  const group=new THREE.Group();group.name='OriginalCreamCloudLayer';
  const geometry=createJoinedCloudGeometry();
  const material=new THREE.ShaderMaterial({
    name:'OriginalCreamCloudMaterial',
    toneMapped:false,
    dithering:true,
    uniforms:{cream:{value:new THREE.Color('#fffdf5')},shade:{value:new THREE.Color('#c5d9ed')},sunDirection:{value:new THREE.Vector3(-.6,.8,.25).normalize()}},
    vertexShader:`varying vec3 vCloudNormal;
      void main(){vCloudNormal=normalize(transpose(mat3(viewMatrix))*(normalMatrix*normal));gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader:`#include <common>
      #include <dithering_pars_fragment>
      uniform vec3 cream;uniform vec3 shade;uniform vec3 sunDirection;varying vec3 vCloudNormal;
      void main(){vec3 n=normalize(vCloudNormal);float daylight=smoothstep(-.55,.35,n.y);float sunlight=smoothstep(-.2,.9,dot(n,sunDirection));float light=daylight*.8+sunlight*.2;gl_FragColor=vec4(mix(shade,cream,light),1.0);
      #include <colorspace_fragment>
      #include <dithering_fragment>
      }`
  });
  const placements=[[-120,62,-160,29],[-38,73,-205,36],[62,48,-168,24],[153,79,-101,35],[184,67,20,32],[115,60,133,26],[26,87,203,37],[-78,54,161,26],[-165,78,80,34],[-194,60,-23,24],[-84,113,-235,32],[108,127,192,28]];
  for(let i=0;i<placements.length;i++){
    const [x,y,z,size]=placements[i];const cloud=new THREE.Group();cloud.position.set(x,y,z);cloud.rotation.y=i*.93;
    const mesh=new THREE.Mesh(geometry,material);mesh.scale.setScalar(size);cloud.add(mesh);
    group.add(cloud);
  }
  return group;
}

// A smooth implicit union keeps cumulus lobes without intersecting separate
// ellipsoids, which produced hard oval undersides and triangular shelves.
// Generate one bounded, shared mesh once; each sky cluster uses that geometry.
let joinedCloudGeometry;
function createJoinedCloudGeometry(){
  if(joinedCloudGeometry)return joinedCloudGeometry;
  const resolution=40,extent=1.6;
  const surface=new MarchingCubes(resolution,new THREE.MeshBasicMaterial(),false,false,8000);
  surface.isolation=0;
  const puffs=[[-.62,-.14,0,.53],[-.19,.13,.07,.73],[.3,.18,.01,.8],[.7,-.09,-.02,.46],[.0,-.3,.15,.68]];
  for(let z=0;z<resolution;z++)for(let y=0;y<resolution;y++)for(let x=0;x<resolution;x++){
    const px=(x/resolution*2-1)*extent,py=(y/resolution*2-1)*extent,pz=(z/resolution*2-1)*extent;
    let distance=Infinity;
    for(const [cx,cy,cz,r]of puffs){
      const next=(Math.hypot((px-cx)/r,(py-cy*.82)/(r*.74),(pz-cz)/(r*.67))-1)*r*.67;
      const blend=Math.max(.23-Math.abs(distance-next),0)/.23;
      distance=Math.min(distance,next)-blend*blend*.23*.25;
    }
    surface.field[x+y*resolution+z*resolution*resolution]=-distance;
  }
  surface.update();
  const positions=surface.geometry.attributes.position.array.slice(0,surface.count*3);
  for(let i=0;i<positions.length;i++)positions[i]*=extent;
  joinedCloudGeometry=new THREE.BufferGeometry();
  joinedCloudGeometry.setAttribute('position',new THREE.BufferAttribute(positions,3));
  joinedCloudGeometry.setAttribute('normal',new THREE.BufferAttribute(surface.geometry.attributes.normal.array.slice(0,surface.count*3),3));
  joinedCloudGeometry.computeBoundingBox();joinedCloudGeometry.computeBoundingSphere();
  joinedCloudGeometry.userData.triangleCount=surface.count/3;
  surface.geometry.dispose();surface.material.dispose();
  return joinedCloudGeometry;
}

export function applyReferencePalette(root){
  const materials=new Set();root.traverse(o=>{if(o.isMesh)for(const m of Array.isArray(o.material)?o.material:[o.material])materials.add(m);});
  for(const material of materials){
    if(material.name.startsWith('V2_Leaf_')){material.color.multiply(new THREE.Color().setRGB(1.16,1.07,.80));material.roughness=.96;}
    if(material.name==='V2_Ground_Moss'){installColorLayer(material,'foliage');}
    if(['V2_Warm_Plaster','V2_Sage_Plaster','V2_Saffron_Plaster'].includes(material.name)){installColorLayer(material,'paint');}
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
