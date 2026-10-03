#!/usr/bin/env node
// Runs the live application's ThreeOctree and WalkController on exported V3 GLBs.
// No browser/DOM, GPU-frame, or pointer-lock claims are made by this tool.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
import os from 'node:os';
import {performance} from 'node:perf_hooks';
import {createHash} from 'node:crypto';

const projectRoot=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const opts={project:projectRoot,routes:path.join(projectRoot,'tests/fixtures/map-v3-routes.json'),out:path.join(os.tmpdir(),'sunward-runtime-audit-'+process.pid+'.json')};
for(let i=2;i<process.argv.length;i+=2){const k=process.argv[i].replace(/^--/,'');opts[k]=process.argv[i+1];}
const {MAP_CONFIG}=await import(pathToFileURL(path.join(opts.project,'src/map-config.js')));
opts.collision ||= path.join(opts.project,'public/assets',MAP_CONFIG.assets.collision);
opts.visual ||= path.join(opts.project,'public/assets',MAP_CONFIG.assets.map);
const mod=f=>import(pathToFileURL(f));
const THREE=await mod(path.join(opts.project,'node_modules/three/build/three.module.js'));
const {GLTFLoader}=await mod(path.join(opts.project,'node_modules/three/examples/jsm/loaders/GLTFLoader.js'));
const {Capsule}=await mod(path.join(opts.project,'node_modules/three/examples/jsm/math/Capsule.js'));
const {buildCollisionOctree}=await mod(path.join(opts.project,'src/collision.js'));
const {WalkController}=await mod(path.join(opts.project,'src/physics.js'));
const {decodeGlbBytes}=await mod(path.join(opts.project,'src/asset-loader.js'));
const {Vector3,Ray,Triangle,Group,Box3,PerspectiveCamera}=THREE;
const contract=JSON.parse(fs.readFileSync(opts.routes,'utf8'));
const report={schema_version:1,scope:'Actual application WalkController and bounded ThreeOctree in Node, GLB metadata/budgets; no browser input/GPU frame tests',created_utc:new Date().toISOString(),tests:[],routes:[],perimeter:[],budgets:{status:'provisional engineering caps, baseline visual 207294 triangles /133 meshes /57 materials /11 images /12155684 bytes',visual:{triangles:400000,meshes:1500,primitives:1800,materials:80,images:24,bytes:32000000,texture_rgba_bytes:128*1024*1024},collision:{triangles:20000,bytes:3000000,nodes:40000,references:200000,build_ms:5000,heap_growth_bytes:256*1024*1024}},unverified:['Browser rendering, input, pointer lock, resize and touch controls','Browser WebGL2 shader linking and frame rate for integrated v3','Independent visible-reference acceptance'],scale_assumption:contract.scale_assumption};
if(contract.frame_version)test('route fixture frame matches application config',()=>ok(contract.frame_version===MAP_CONFIG.frameVersion,'stale route fixture '+contract.frame_version+' vs app '+MAP_CONFIG.frameVersion));
const sha=b=>createHash('sha256').update(b).digest('hex');
function test(name,fn){try{const detail=fn();report.tests.push({name,passed:true,...(detail||{})});}catch(e){report.tests.push({name,passed:false,error:String(e.message||e)});}}
function ok(v,msg){if(!v)throw new Error(msg);}
function near(a,b,tol,msg){ok(Math.abs(a-b)<=tol,`${msg}: ${a} vs ${b}, tolerance ${tol}`);}
const v3=p=>new Vector3(p[0],p[2],-p[1]);
const arr=v=>v.toArray().map(n=>Math.round(n*1e5)/1e5);
async function readGlb(file){
 const delivery=fs.readFileSync(file),b=Buffer.from(await decodeGlbBytes(delivery));ok(b.readUInt32LE(0)===0x46546c67,'invalid GLB magic');ok(b.readUInt32LE(4)===2,'GLB version must be 2');ok(b.readUInt32LE(8)===b.length,'GLB declared length mismatch');let offset=12,j,bin;
 while(offset<b.length){const n=b.readUInt32LE(offset),type=b.readUInt32LE(offset+4);const block=b.subarray(offset+8,offset+8+n);if(type===0x4e4f534a)j=JSON.parse(block.toString());else if(type===0x004e4942)bin=block;offset+=n+8;}
 ok(j,'missing JSON chunk');return {bytes:b,json:j,bin,delivery};
}
function imageSize(b){
 if(b.length>=24&&b.toString('ascii',1,4)==='PNG')return [b.readUInt32BE(16),b.readUInt32BE(20)];
 if(b.length>=30&&b.toString('ascii',0,4)==='RIFF'&&b.toString('ascii',8,12)==='WEBP'){
  const type=b.toString('ascii',12,16);if(type==='VP8X')return [1+b.readUIntLE(24,3),1+b.readUIntLE(27,3)];
  if(type==='VP8L'){const v=b.readUInt32LE(21);return [(v&0x3fff)+1,((v>>14)&0x3fff)+1];}
  if(type==='VP8 '&&b.length>=30)return [b.readUInt16LE(26)&0x3fff,b.readUInt16LE(28)&0x3fff];
 }
 if(b[0]===255&&b[1]===216){let p=2;while(p+8<b.length){if(b[p]!==255){p++;continue;}const marker=b[p+1];p+=2;if(marker===216||marker===217)continue;const n=b.readUInt16BE(p);if([0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf].includes(marker))return [b.readUInt16BE(p+5),b.readUInt16BE(p+3)];if(n<2)break;p+=n;}}
 return null;
}
function metadata(file,g,kind){
 const j=g.json;const primitiveList=(j.meshes||[]).flatMap(m=>m.primitives);let triangles=0;
 for(const p of primitiveList){ok(p.mode===undefined||p.mode===4,'nontriangle primitive');const accessor=j.accessors[p.indices??p.attributes.POSITION];triangles+=accessor.count/3;}
 const images=(j.images||[]).map((im,i)=>{ok(!im.uri,'external texture URI in self-contained GLB');const bv=j.bufferViews[im.bufferView];const b=g.bin.subarray(bv.byteOffset||0,(bv.byteOffset||0)+bv.byteLength);const dimensions=imageSize(b);return {index:i,name:im.name,mimeType:im.mimeType,bytes:b.length,dimensions,rgba_bytes:dimensions?dimensions[0]*dimensions[1]*4:null};});
 const metadata={file,sha256:sha(g.bytes),bytes:g.bytes.length,delivery_bytes:g.delivery.length,delivery_sha256:sha(g.delivery),nodes:(j.nodes||[]).length,meshes:(j.meshes||[]).length,primitives:primitiveList.length,triangles,materials:(j.materials||[]).length,images:images.length,textures:images,texture_rgba_bytes:images.reduce((sum,x)=>sum+(x.rgba_bytes||0),0),asset:j.asset,scene_extras:(j.scenes||[]).map(s=>s.extras)};
 report[kind]=metadata;const caps=report.budgets[kind];
 for(const key of ['bytes','meshes','primitives','triangles','materials','images','texture_rgba_bytes'])if(caps[key])test(`${kind} ${key} budget`,()=>ok(metadata[key]<=caps[key],`${metadata[key]} exceeds cap ${caps[key]}`));
 test(`${kind} embedded texture dimensions known`,()=>ok(images.every(im=>im.dimensions),'unsupported embedded image header, unable to establish texture budget'));
 test(`${kind} contains no legacy collider`,()=>ok(!(j.nodes||[]).some(n=>n.name?.includes('COL_Sunward_Static')),'legacy collider exported'));
 if(kind==='visual')test('visual GLB excludes collision geometry',()=>ok(!(j.nodes||[]).some(n=>n.name?.startsWith('COL_')),'COL_ geometry in visual export'));
 if(kind==='collision')test('collision GLB only contains V3 proxy meshes',()=>{for(const n of j.nodes||[])if(n.mesh!==undefined)ok(n.name?.startsWith('COL_V3_'),`non-V3 mesh ${n.name}`);ok(images.length===0,'collision has texture images');});
 return metadata;
}
const visual=await readGlb(opts.visual),collision=await readGlb(opts.collision);metadata(opts.visual,visual,'visual');metadata(opts.collision,collision,'collision');
if(path.resolve(opts.visual)===path.resolve(opts.project,'public/assets',MAP_CONFIG.assets.map))test('delivered map decodes to the pinned accepted SHA-256',()=>ok(sha(visual.bytes)===MAP_CONFIG.decodedMapSha256,'decoded visual differs from accepted map-config hash'));
test('visual delivery byte budget',()=>ok(visual.delivery.length<=8000000||!String(opts.visual).endsWith('.gz'),'compressed map exceeds8MB transfer budget'));

const gltf=await new GLTFLoader().parseAsync(collision.bytes.buffer.slice(collision.bytes.byteOffset,collision.bytes.byteOffset+collision.bytes.byteLength),'');
gltf.scene.updateWorldMatrix(true,true);
// Freeze collision geometry independently of GLB metadata, buffers and node order.
// Cyclic normalization preserves effective winding; coordinates use 1µm precision.
const collisionShapes=[];
gltf.scene.traverse(object=>{
 if(!object.isMesh)return;
 const pos=object.geometry.attributes.position,index=object.geometry.index,count=index?index.count:pos.count,mirrored=object.matrixWorld.determinant()<0,triangles=[];
 for(let i=0;i<count;i+=3){
  let points=[0,1,2].map(k=>new Vector3().fromBufferAttribute(pos,index?index.getX(i+k):i+k).applyMatrix4(object.matrixWorld).toArray().map(v=>Number(v.toFixed(6))));
  if(mirrored)points=[points[0],points[2],points[1]];
  const cyclic=[points,[points[1],points[2],points[0]],[points[2],points[0],points[1]]].map(v=>JSON.stringify(v)).sort();triangles.push(cyclic[0]);
 }
 collisionShapes.push({name:object.userData.name||object.name,triangles:triangles.sort()});
});
collisionShapes.sort((a,b)=>a.name.localeCompare(b.name));
report.collision_geometry_sha256=sha(JSON.stringify(collisionShapes));
if(contract.expected_collision_geometry_sha256)test('collision geometry matches the approved structural snapshot',()=>ok(report.collision_geometry_sha256===contract.expected_collision_geometry_sha256,'collision geometry changed from approved baseline; update only after a separately verified structural change'));

if(opts['source-audit']){
 const sourceAudit=JSON.parse(fs.readFileSync(opts['source-audit'],'utf8'));report.source_audit={file:opts['source-audit'],sha256:sha(fs.readFileSync(opts['source-audit'])),source_sha256:sourceAudit.source_sha256,source_hash_preserved:sourceAudit.source_hash_preserved};
 test('source export audit passed',()=>ok(sourceAudit.passed,'source/export audit has recorded defects'));
 const actual=new Map();gltf.scene.traverse(o=>{if(o.isMesh)actual.set(o.userData.name||o.name,o);});
 test('all exported collision bounds match source proxies in runtime axes',()=>{for(const expected of sourceAudit.collision.objects){const mesh=actual.get(expected.name);ok(mesh,`missing source proxy ${expected.name}`);const bounds=new Box3().setFromObject(mesh);const [lo,hi]=expected.bounds_blender;const wantLo=[lo[0],lo[2],-hi[1]],wantHi=[hi[0],hi[2],-lo[1]];for(let a=0;a<3;a++){near(bounds.min.getComponent(a),wantLo[a],.003,expected.name+' minimum axis '+a);near(bounds.max.getComponent(a),wantHi[a],.003,expected.name+' maximum axis '+a);}}return {source_proxies:sourceAudit.collision.objects.length};});
 test('GLB provenance scene metadata retains v3 build identity',()=>{const extras=visual.json.scenes?.[visual.json.scene||0]?.extras;ok(extras,'visual GLB scene extras missing');ok(String(extras.build_version||extras.map_version||'').startsWith('3'),'GLB metadata still has old/non-v3 build version');});
 test('both rear stair side connectors have required supported route width',()=>{const connectors=sourceAudit.collision.objects.filter(o=>o.name.includes('RearStairSideConnector'));ok(connectors.length===2,'both side connector proxies required');for(const o of connectors){ok(o.dimensions_local,'source audit must include local dimensions');const width=Math.min(o.dimensions_local[0],o.dimensions_local[1]);ok(width>=contract.player.minimum_route_clear_width_m-.002,`${o.name} support depth ${width} below1.1m route target`);}return {scope:'local geometric support width, separately from whether a capsule can balance on a narrower ledge'};});
}
const heap0=process.memoryUsage().heapUsed,start=performance.now(),tree=buildCollisionOctree(gltf.scene);report.octree={...tree.stats,build_ms:performance.now()-start,heap_growth_bytes:process.memoryUsage().heapUsed-heap0};
for(const key of ['nodes','references','build_ms','heap_growth_bytes'])test(`bounded octree ${key}`,()=>ok(report.octree[key]<report.budgets.collision[key],`${report.octree[key]} exceeds ${report.budgets.collision[key]}`));
test('octree triangle count matches GLB accessors',()=>near(tree.stats.triangleCount,report.collision.triangles,0,'triangle count'));
const floorMeshes=[];const outlineMeshes=[];gltf.scene.traverse(o=>{if(o.isMesh&&['COL_V3_LAYOUT_PlayableFloor','COL_V3_LAYOUT_OutlineClips'].includes(o.name)){outlineMeshes.push(o);if(o.name==='COL_V3_LAYOUT_PlayableFloor')floorMeshes.push(o);}});
test('authored meter scale and capsule dimensions',()=>{near(contract.player.height_m,1.8,1e-9,'player height');near(new WalkController().collider.radius,contract.player.capsule_radius_m,1e-9,'capsule radius');near(new WalkController().collider.end.distanceTo(new WalkController().collider.start)+2*.35,1.8,1e-9,'capsule total height');});
test('exported floor verifies Blender-to-Three axes and winding',()=>{
 ok(floorMeshes.length===1,'expected one canonical floor mesh');const floor=floorMeshes[0],b=new Box3().setFromObject(floor);const expected=new Box3().setFromPoints(contract.outline_blender.map(v3));near(b.min.x,expected.min.x,.002,'floor minimum X');near(b.max.x,expected.max.x,.002,'floor maximum X');near(b.min.z,expected.min.z,.002,'floor minimum Z');near(b.max.z,expected.max.z,.002,'floor maximum Z');near(b.min.y,.014,.002,'floor support Y');near(b.max.y,.014,.002,'floor support Y');
 const geo=floor.geometry,pos=geo.attributes.position,index=geo.index,count=index?index.count:pos.count;let tris=0;for(let i=0;i<count;i+=3){const vs=[0,1,2].map(k=>new Vector3().fromBufferAttribute(pos,index?index.getX(i+k):i+k).applyMatrix4(floor.matrixWorld));const n=new Triangle(...vs).getNormal(new Vector3());ok(n.y>.99,'floor triangle does not face +Three Y');tris++;}return {floor_triangles:tris};
});
let degenerate=0,nonfinite=0,mirrored=0;gltf.scene.traverse(o=>{if(!o.isMesh)return;if(o.matrixWorld.determinant()<0)mirrored++;const p=o.geometry.attributes.position,idx=o.geometry.index,n=idx?idx.count:p.count;for(let i=0;i<n;i+=3){const vs=[0,1,2].map(k=>new Vector3().fromBufferAttribute(p,idx?idx.getX(i+k):i+k).applyMatrix4(o.matrixWorld));if(vs.some(v=>v.toArray().some(x=>!Number.isFinite(x))))nonfinite++;if(new Triangle(...vs).getArea()<1e-8)degenerate++;}});
test('collision GLB triangles finite and nondegenerate',()=>{ok(!nonfinite,`${nonfinite} nonfinite triangles`);ok(!degenerate,`${degenerate} degenerate triangles`);return {mirrored_meshes:mirrored};});
const floorRay=new Ray(new Vector3(),new Vector3(0,-1,0));
function support(point,rayTop=point.y+1){floorRay.origin.copy(point);floorRay.origin.y=rayTop;const hit=tree.rayIntersect(floorRay);if(!hit)return null;const normal=hit.triangle.getNormal(new Vector3());return normal.y>.45?{height:rayTop-hit.distance,normal}:null;}
for(const anchor of contract.support_points||[])test(`authored support height ${anchor.name}`,()=>{const point=v3(anchor.feet_blender),surface=support(point);ok(surface,'support ray misses upward-facing surface');near(surface.height,point.y,.004,'author support height');return {height_m:surface.height,normal:arr(surface.normal)};});
function spawnFeet(feet,selectedTree=tree){const player=new WalkController(selectedTree);player.spawn(feet.clone().add(new Vector3(0,1.64,0)));for(let i=0;i<90;i++)player.update(1/60);return player;}
function feet(player){return player.collider.start.clone().add(new Vector3(0,-player.collider.radius,0));}
function drive(player,target,maxSeconds,settleFrames=90){let stalled=0,lastDist=Infinity,frames=0,peakY=feet(player).y,groundedFrames=0,unsupportedRun=0,maxUnsupportedRun=0;for(;frames<Math.ceil(maxSeconds*60);frames++){
 const current=feet(player),dx=target.x-current.x,dz=target.z-current.z,dist=Math.hypot(dx,dz);peakY=Math.max(peakY,current.y);
 if(dist<.025)break;const norm=Math.max(1,dist),input={x:dx/norm,z:-dz/norm,yaw:0};player.update(1/60,input);
 if(player.onFloor){groundedFrames++;unsupportedRun=0;}else{unsupportedRun++;maxUnsupportedRun=Math.max(maxUnsupportedRun,unsupportedRun);}const nextDist=Math.hypot(target.x-feet(player).x,target.z-feet(player).z);if(nextDist>lastDist-.001)stalled++;else stalled=0;lastDist=nextDist;if(stalled>100)break;
 }
 for(let i=0;i<settleFrames;i++)player.update(1/60);const final=feet(player);return {arrived:Math.hypot(final.x-target.x,final.z-target.z)<.16,frames,feet:arr(final),peak_y:peakY,on_floor:player.onFloor,grounded_frames:groundedFrames,max_unsupported_frames:maxUnsupportedRun,settled_frames:settleFrames,horizontal_error_m:Math.hypot(final.x-target.x,final.z-target.z),vertical_error_m:final.y-target.y};}
for(const spawn of contract.spawns)test(`spawn ${spawn.name} settles onto upward floor`,()=>{const eye=v3(spawn.eye_blender),player=new WalkController(tree);player.spawn(eye);for(let i=0;i<120;i++)player.update(1/60);const foot=feet(player);ok(player.onFloor,'spawn remains airborne');near(foot.y,.014,.025,'spawn floor contact');near(foot.x,eye.x,.1,'spawn x');near(foot.z,eye.z,.1,'spawn z');const hit=tree.capsuleIntersect(new Capsule(new Vector3(foot.x,.004+.35,foot.z),new Vector3(foot.x,.004+1.45,foot.z),.35));ok(hit&&hit.normal.y>.9,'capsule overlap does not resolve upward');return {feet:arr(foot)};});
for(const portal of contract.portals)test(`portal ${portal.name} clearance contract`,()=>{ok(portal.clear_width>=contract.player.minimum_route_clear_width_m,'clear width below 1.1m');ok(portal.clear_height>=contract.player.height_m+.1,'portal too short for player');});

const poly=contract.outline_blender.map(v3);
function inside(x,z){let c=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const a=poly[i],b=poly[j];if(((a.z>z)!==(b.z>z))&&(x<(b.x-a.x)*(z-a.z)/(b.z-a.z)+a.x))c=!c;}return c;}
function distSegment(x,z,a,b){const dx=b.x-a.x,dz=b.z-a.z,t=Math.max(0,Math.min(1,((x-a.x)*dx+(z-a.z)*dz)/(dx*dx+dz*dz)));return Math.hypot(x-a.x-t*dx,z-a.z-t*dz);}
function navPlan(points,corridor){const a=points[0],b=points.at(-1),step=.55,minX=Math.min(a.x,b.x)-corridor,maxX=Math.max(a.x,b.x)+corridor,minZ=Math.min(a.z,b.z)-corridor,maxZ=Math.max(a.z,b.z)+corridor;const nx=Math.ceil((maxX-minX)/step)+1,nz=Math.ceil((maxZ-minZ)/step)+1,cache=new Map();
 function node(i,j){const x=minX+i*step,z=minZ+j*step;if(i<0||j<0||i>=nx||j>=nz||!inside(x,z)||distSegment(x,z,a,b)>corridor)return null;const key=i+','+j;if(cache.has(key))return cache.get(key);const s=support(new Vector3(x,.014,z),2.7);let value=null;if(s&&s.height>=-.05&&s.height<=.45){const cap=new Capsule(new Vector3(x,s.height+.375,z),new Vector3(x,s.height+1.475,z),.35);const h=tree.capsuleIntersect(cap);if(!h||h.depth<.015)value=new Vector3(x,s.height,z);}cache.set(key,value);return value;}
 const exact=p=>{const s=support(p,2.7);if(!s||s.height>.45||!inside(p.x,p.z))return false;const cap=new Capsule(new Vector3(p.x,s.height+.375,p.z),new Vector3(p.x,s.height+1.475,p.z),.35);const h=tree.capsuleIntersect(cap);return !h||h.depth<.015;};
 if(!exact(a)||!exact(b))throw new Error('canonical lane/spawn endpoint overlaps an obstacle or lacks floor');
 const grid=p=>[Math.round((p.x-minX)/step),Math.round((p.z-minZ)/step)];let [si,sj]=grid(a),[ei,ej]=grid(b);if(!node(si,sj)||!node(ei,ej))throw new Error('navigation grid endpoint blocked');const key=(i,j)=>i+','+j,startKey=key(si,sj),endKey=key(ei,ej),open=[{i:si,j:sj,g:0,f:Math.hypot(ei-si,ej-sj)}],best=new Map([[startKey,0]]),parent=new Map();let visited=0,found=false;
 while(open.length&&visited<25000){open.sort((a,b)=>b.f-a.f);const n=open.pop(),k=key(n.i,n.j);if(n.g>best.get(k))continue;if(k===endKey){found=true;break;}visited++;for(const [di,dj] of [[1,0],[-1,0],[0,1],[0,-1]]){const ni=n.i+di,nj=n.j+dj,p=node(ni,nj);if(!p)continue;const nk=key(ni,nj),g=n.g+1;if(g>=(best.get(nk)??Infinity))continue;best.set(nk,g);parent.set(nk,k);open.push({i:ni,j:nj,g,f:g+Math.hypot(ei-ni,ej-nj)});}}
 if(!found)throw new Error(`no capsule-clear ground route within authored ${corridor}m corridor; ${visited} nodes visited`);let k=endKey,keys=[k];while(k!==startKey){k=parent.get(k);keys.push(k);}keys.reverse();const raw=[a,...keys.map(k=>{const[i,j]=k.split(',').map(Number);return node(i,j);}),b];const compressed=[raw[0]];for(let i=1;i<raw.length-1;i++){const ab=raw[i].clone().sub(compressed.at(-1)).normalize(),bc=raw[i+1].clone().sub(raw[i]).normalize();if(ab.dot(bc)<.999)compressed.push(raw[i]);}compressed.push(b);return {points:compressed,visited_nodes:visited,step_m:step};}

for(const route of contract.routes){let record={name:route.name,category:route.category,source_report:route.source_report};try{
 let points=route.feet_blender.map(v3);if(route.planner){const plan=navPlan(points,route.corridor_half_width_m);points=plan.points;record.planner={visited_nodes:plan.visited_nodes,step_m:plan.step_m,waypoints:points.map(arr)};}
 const player=spawnFeet(points[0]);const initial=feet(player).y;ok(player.onFloor,'route start lacks capsule floor contact');record.start=arr(feet(player));record.segments=[];
 for(let i=1;i<points.length;i++){const distance=Math.hypot(points[i].x-feet(player).x,points[i].z-feet(player).z),terminal=i===points.length-1,result=drive(player,points[i],distance/2.5+3,terminal?90:0);record.segments.push(result);ok(result.arrived,`segment ${i} blocked at ${result.feet}; target ${arr(points[i])}`);ok(Number.isFinite(result.feet[1])&&result.feet[1]>-1,'fell through floor');if(terminal)ok(result.on_floor,'route terminal endpoint remains airborne after1.5s settling');ok(Math.abs(result.vertical_error_m)<.27,`segment ${i} wrong floor ${result.feet[1]} vs target ${points[i].y}`);}
 record.end=arr(feet(player));record.rise_m=feet(player).y-initial;if(route.minimum_rise_m!==undefined)ok(record.rise_m>=route.minimum_rise_m,`route rise ${record.rise_m} below ${route.minimum_rise_m}`);record.passed=true;
 }catch(e){record.passed=false;record.error=String(e.message||e);}report.routes.push(record);}
for(const category of contract.required_categories)test(`authored ${category} routes present and pass`,()=>{const r=report.routes.filter(r=>r.category===category);ok(r.length>0,'no authored routes in required category');const failed=r.filter(r=>!r.passed);ok(!failed.length,failed.map(r=>`${r.name}: ${r.error}`).join('; '));return {routes:r.length};});

const isolated=new Group();for(const mesh of outlineMeshes){const clone=mesh.clone();clone.matrixAutoUpdate=false;clone.matrix.copy(mesh.matrixWorld);isolated.add(clone);}const boundaryTree=buildCollisionOctree(isolated);
for(let i=0;i<poly.length;i++)for(const t of [.15,.5,.85]){const a=poly[i],b=poly[(i+1)%poly.length],mid=a.clone().lerp(b,t),delta=b.clone().sub(a),normal=new Vector3(-delta.z,0,delta.x).normalize();let inward=normal;if(!inside(mid.x+normal.x*.8,mid.z+normal.z*.8))inward=normal.clone().negate();const origin=mid.clone().addScaledVector(inward,.9);origin.y=.014;const goal=mid.clone().addScaledVector(inward,-4);goal.y=.014;const rec={edge:i,fraction:t,start:arr(origin)};try{
 ok(inside(origin.x,origin.z),'perimeter test start cannot be placed within local outline');const player=spawnFeet(origin,boundaryTree);drive(player,goal,2.3);const final=feet(player);rec.end=arr(final);rec.signed_inward_distance_m=final.clone().sub(mid).dot(inward);ok(inside(final.x,final.z),'capsule escaped the outline');ok(rec.signed_inward_distance_m>=.30,'capsule center crossed collision-wall safe margin');ok(player.onFloor,'boundary lost floor contact');rec.passed=true;
 }catch(e){rec.passed=false;rec.error=String(e.message||e);}report.perimeter.push(rec);}
test('every irregular perimeter edge blocks actual walk controller',()=>{const failed=report.perimeter.filter(r=>!r.passed);ok(!failed.length,failed.map(r=>`edge ${r.edge}@${r.fraction}: ${r.error}`).join('; '));return {samples:report.perimeter.length,scope:'isolated authored floor/outline prevents unrelated props masking a missing boundary'};});
report.perimeter_jumps=[];
for(let i=0;i<poly.length;i++){const a=poly[i],b=poly[(i+1)%poly.length],mid=a.clone().lerp(b,.5),delta=b.clone().sub(a),inward=new Vector3(-delta.z,0,delta.x).normalize();if(!inside(mid.x+inward.x*.9,mid.z+inward.z*.9))inward.negate();const origin=mid.clone().addScaledVector(inward,.9);origin.y=.014;const rec={edge:i};try{const player=spawnFeet(origin,boundaryTree);let peak=.014;for(let frame=0;frame<150;frame++){player.update(1/60,{x:-inward.x,z:inward.z,yaw:0,jump:frame%50===0});const f=feet(player);peak=Math.max(peak,f.y);ok(inside(f.x,f.z),'ground jump escaped outline');}rec.peak_feet_y_m=peak;rec.end=arr(feet(player));rec.passed=true;}catch(e){rec.passed=false;rec.error=e.message;}report.perimeter_jumps.push(rec);}
test('ground-level jumps cannot escape any irregular perimeter edge',()=>{const failed=report.perimeter_jumps.filter(r=>!r.passed);ok(!failed.length,failed.map(r=>`edge${r.edge}: ${r.error}`).join('; '));return {samples:report.perimeter_jumps.length,scope:'actual jump controller from base ground, not a claim about arbitrary elevated spawns'};});
test('far overview and freefly matrices remain finite',()=>{const camera=new PerspectiveCamera(58,16/9,.05,500);for(const view of contract.viewpoints){camera.position.copy(v3(view.position_blender));camera.lookAt(v3(view.look_at_blender));camera.updateMatrixWorld();camera.updateProjectionMatrix();ok(camera.matrixWorld.elements.every(Number.isFinite),'nonfinite world matrix');ok(camera.projectionMatrix.elements.every(Number.isFinite),'nonfinite projection matrix');ok(camera.position.length()<500,'authored camera outside far-plane engineering range');}for(const pos of [[140,90,-140],[-140,90,140],[0,160,0]]){camera.position.fromArray(pos);camera.lookAt(0,0,0);camera.updateMatrixWorld();ok(camera.matrixWorld.elements.every(Number.isFinite),'nonfinite far camera');}return {scope:'finite authored/far camera math; no freefly UI input or GPU clipping test'};});
report.warnings=report.routes.flatMap(r=>(r.segments||[]).filter(s=>s.max_unsupported_frames>=30).map(s=>({route:r.name,warning:'controller onFloor flag false for at least0.5s during traversal; final arrival alone does not prove continuous floor contact',max_unsupported_frames:s.max_unsupported_frames,grounded_frames:s.grounded_frames,frames:s.frames})));report.passed=report.tests.every(t=>t.passed)&&report.routes.every(r=>r.passed)&&report.perimeter.every(r=>r.passed)&&report.perimeter_jumps.every(r=>r.passed)&&report.warnings.length===0;report.runtime_modules={collision:sha(fs.readFileSync(path.join(opts.project,'src/collision.js'))),physics:sha(fs.readFileSync(path.join(opts.project,'src/physics.js')))};fs.mkdirSync(path.dirname(opts.out),{recursive:true});fs.writeFileSync(opts.out,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({out:opts.out,passed:report.passed,tests:report.tests.length,failed_tests:report.tests.filter(t=>!t.passed),routes:report.routes.length,failed_routes:report.routes.filter(r=>!r.passed).map(r=>({name:r.name,error:r.error})),perimeter_samples:report.perimeter.length,perimeter_jump_samples:report.perimeter_jumps.length,warnings:report.warnings,visual_delivery_bytes:report.visual.delivery_bytes,visual_decoded_bytes:report.visual.bytes,visual_decoded_sha256:report.visual.sha256,failed_perimeter:report.perimeter.filter(r=>!r.passed),octree:report.octree},null,2));
process.exitCode=report.passed?0:1;
