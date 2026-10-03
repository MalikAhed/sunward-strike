import * as THREE from 'three';

// Original procedural atmosphere inspired by the supplied art-direction sheet.
// This is a separate sky layer; no source map geometry or transforms are edited.
export function createClouds(){
  const group=new THREE.Group();group.name='OriginalCreamCloudLayer';
  const geometry=new THREE.IcosahedronGeometry(1,2);
  const material=new THREE.ShaderMaterial({
    uniforms:{cream:{value:new THREE.Color('#fff6df')},shade:{value:new THREE.Color('#9cb9d8')},sunDirection:{value:new THREE.Vector3(-.6,.8,.25).normalize()}},
    vertexShader:`varying vec3 vNormal; void main(){vNormal=normalize((vec4(normalMatrix*normal,0.0)*viewMatrix).xyz);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`,
    fragmentShader:`uniform vec3 cream;uniform vec3 shade;uniform vec3 sunDirection;varying vec3 vNormal;
      void main(){vec3 n=normalize(vNormal);float sun=dot(n,sunDirection);float light=smoothstep(-.4,.85,sun)*.62+smoothstep(-.45,.75,n.y)*.38;gl_FragColor=vec4(mix(shade,cream,light),1.0);
      #include <tonemapping_fragment>
      #include <colorspace_fragment>
      }`
  });
  const placements=[[-120,62,-160,29],[-38,73,-205,36],[62,48,-168,24],[153,79,-101,35],[184,67,20,32],[115,60,133,26],[26,87,203,37],[-78,54,161,26],[-165,78,80,34],[-194,60,-23,24],[-84,113,-235,32],[108,127,192,28]];
  const puffs=[[-.62,-.14,0,.53],[-.19,.13,.07,.73],[.3,.18,.01,.8],[.7,-.09,-.02,.46],[.0,-.3,.15,.68]];
  for(let i=0;i<placements.length;i++){
    const [x,y,z,size]=placements[i];const cloud=new THREE.Group();cloud.position.set(x,y,z);cloud.rotation.y=i*.93;
    for(const [px,py,pz,r]of puffs){const mesh=new THREE.Mesh(geometry,material);mesh.position.set(px*size,py*size*.65,pz*size);mesh.scale.set(size*r,size*r*.47,size*r*.5);cloud.add(mesh);}
    group.add(cloud);
  }
  return group;
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
    const layer=kind==='foliage'?'diffuseColor.rgb*=vec3(1.16,1.08,.76);':`vec3 cell=floor(vArtWorld*1.2);float diagonal=step(fract(vArtWorld.x*1.2),fract(vArtWorld.y*1.2));float patch=artHash(cell+diagonal);diffuseColor.rgb*=.965+patch*.07;`;
    shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>','#include <color_fragment>\n'+layer);
  };
  material.customProgramCacheKey=()=>`sunward-art-layer-${kind}-v1`;
  material.needsUpdate=true;
}
