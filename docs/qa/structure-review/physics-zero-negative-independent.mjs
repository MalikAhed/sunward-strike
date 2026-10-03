// Disposable controller investigation only; does not write live physics.js.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
const project='/workspace/shared/sunward-strike';
const T=await import(pathToFileURL(project+'/node_modules/three/build/three.module.js'));
const {WalkController:Original}=await import(pathToFileURL(project+'/src/physics.js'));
const {WalkController:Proposed}=await import('/workspace/shared/sunward-structure-build/runtime/proposed-test-fixture/src/physics-zero-grounded.js');
const {buildCollisionOctree}=await import(pathToFileURL(project+'/src/collision.js'));
const {Vector3,Group,Mesh,BufferGeometry,Float32BufferAttribute,PlaneGeometry,BoxGeometry,MeshBasicMaterial}=T;
const report={scope:'Disposable eight-centimeter prior-grounded, nonascending surface snap; live physics unchanged',cases:[],traces:[]};
const foot=p=>p.collider.start.clone().add(new Vector3(0,-.35,0));
function test(name,fn){try{const detail=fn();report.cases.push({name,passed:true,...detail});}catch(e){report.cases.push({name,passed:false,error:e.message});}}
function plane(root,width,depth,x,y){const mesh=new Mesh(new PlaneGeometry(width,depth),new MeshBasicMaterial());mesh.rotation.x=-Math.PI/2;mesh.position.set(x,y,0);root.add(mesh);}
function rampTree(yaw=0){const root=new Group();plane(root,12,8,-6,.18);plane(root,12,8,12,3.18);const geometry=new BufferGeometry();geometry.setAttribute('position',new Float32BufferAttribute([0,.18,-2,0,.18,2,6,3.18,2,6,3.18,-2],3));geometry.setIndex([0,1,2,0,2,3]);root.add(new Mesh(geometry,new MeshBasicMaterial()));root.rotation.y=yaw;return {tree:buildCollisionOctree(root),yaw};}
function orient(x,y,yaw){return new Vector3(Math.cos(yaw)*x,y,-Math.sin(yaw)*x);}
function spawn(C,tree,feet){const p=new C(tree);p.spawn(feet.clone().add(new Vector3(0,1.64,0)));for(let i=0;i<120;i++)p.update(1/60);return p;}
function rampTrace(C,yaw,sprint,dt){const {tree}=rampTree(yaw),p=spawn(C,tree,orient(7,3.18,yaw)),goal=orient(-1,.18,yaw),trace=[];const speed=sprint?7.1:4.4;let maxRun=0,run=0,coreSamples=0,coreUngrounded=0;for(let i=0;i<Math.ceil(10/dt);i++){
 const before=foot(p),dx=goal.x-before.x,dz=goal.z-before.z;if(Math.hypot(dx,dz)<.10)break;const length=Math.hypot(dx,dz);p.update(dt,{x:dx/length,z:-dz/length,sprint});const f=foot(p),localX=f.x*Math.cos(yaw)-f.z*Math.sin(yaw);if(!p.onFloor){run++;maxRun=Math.max(maxRun,run);}else run=0;
 if(localX>.6&&localX<5.4){coreSamples++;if(!p.onFloor)coreUngrounded++;}trace.push({frame:i,feet:f.toArray(),on_floor:p.onFloor,velocity:p.velocity.toArray(),local_x:localX});
 }
 for(let i=0;i<90;i++)p.update(1/60);return {controller:C===Proposed?'proposed':'original',yaw,sprint,dt,frames:trace.length,max_unsupported_frames:maxRun,core_samples:coreSamples,core_ungrounded_frames:coreUngrounded,terminal_on_floor:p.onFloor,terminal_feet:foot(p).toArray(),terminal_error:foot(p).distanceTo(goal),trace};}
for(const yaw of [0,Math.PI/2])for(const sprint of [false,true])for(const dt of [1/60,1/30])test(`continuous ${sprint?'sprint':'walk'} down ${yaw?'interior-axis':'exterior-axis'} ramp at${Math.round(1/dt)}Hz`,()=>{
 const baseline=rampTrace(Original,yaw,sprint,dt),proposed=rampTrace(Proposed,yaw,sprint,dt);report.traces.push(baseline,proposed);assert.ok(proposed.terminal_error<.16);assert.equal(proposed.terminal_on_floor,true);assert.ok(proposed.core_samples>0);assert.equal(proposed.core_ungrounded_frames,0);return {baseline_ungrounded_core_frames:baseline.core_ungrounded_frames,proposed_ungrounded_core_frames:proposed.core_ungrounded_frames,baseline_max_unsupported_frames:baseline.max_unsupported_frames,proposed_max_unsupported_frames:proposed.max_unsupported_frames};
});
test('one-meter ledge remains a real fall, without teleporting or retaining contact',()=>{
 const root=new Group();plane(root,10,8,5,1);plane(root,12,8,-6,0);const p=spawn(Proposed,buildCollisionOctree(root),new Vector3(1.5,1,0));let firstBeyond=null,largestDrop=0,prev=foot(p).y,airborne=0;for(let i=0;i<150;i++){p.update(1/60,{x:-1});const f=foot(p);largestDrop=Math.max(largestDrop,prev-f.y);prev=f.y;if(f.x<-.4&&!firstBeyond)firstBeyond={feet:f.toArray(),on_floor:p.onFloor};if(!p.onFloor)airborne++;}assert.ok(firstBeyond&&firstBeyond.feet[1]>.5);assert.equal(firstBeyond.on_floor,false);assert.ok(airborne>5);assert.ok(largestDrop<.22);assert.equal(p.onFloor,true);assert.ok(Math.abs(foot(p).y)<.03);return {first_beyond:firstBeyond,airborne_frames:airborne,largest_frame_drop_m:largestDrop};
});
test('flat-floor jump keeps upward velocity, then lands normally',()=>{
 const root=new Group();plane(root,20,20,0,0);const p=spawn(Proposed,buildCollisionOctree(root),new Vector3(0,0,0));const initial=foot(p).y;let peak=initial;for(let i=0;i<120;i++){p.update(1/60,{jump:i===0});peak=Math.max(peak,foot(p).y);if(i<8){assert.ok(p.velocity.y>0);assert.equal(p.onFloor,false);}}assert.ok(peak>initial+.5);assert.equal(p.onFloor,true);assert.ok(Math.abs(foot(p).y)<.03);return {jump_peak_m:peak-initial};
});
test('wall/floor corner jump remains available and cannot pass through wall',()=>{
 const root=new Group();plane(root,20,20,0,0);const wall=new Mesh(new BoxGeometry(.2,4,10),new MeshBasicMaterial());wall.position.set(2,2,0);root.add(wall);const p=spawn(Proposed,buildCollisionOctree(root),new Vector3(0,0,0));for(let i=0;i<120;i++)p.update(1/60,{x:1});assert.equal(p.onFloor,true);const initial=foot(p).y;let peak=initial;for(let i=0;i<60;i++){p.update(1/60,{x:1,jump:i===0});peak=Math.max(peak,foot(p).y);assert.ok(foot(p).x<1.56);}assert.ok(peak>initial+.5);return {jump_peak_m:peak-initial};
});
test('ramp jump is never canceled by downhill ground snap',()=>{
 const {tree}=rampTree(),p=spawn(Proposed,tree,new Vector3(4,2.18+.042,0));const initial=foot(p).y;let peak=initial;for(let i=0;i<60;i++){p.update(1/60,{x:-1,jump:i===0});peak=Math.max(peak,foot(p).y);if(i<8){assert.ok(p.velocity.y>0);assert.equal(p.onFloor,false);}}assert.ok(peak>initial+.5);return {jump_peak_m:peak-initial};
});
const actualFile='/workspace/shared/sunward-structure-build/runtime/diagnostic-r1/collision.glb';
if(fs.existsSync(actualFile)){
 const {GLTFLoader}=await import(pathToFileURL(project+'/node_modules/three/examples/jsm/loaders/GLTFLoader.js')),bytes=fs.readFileSync(actualFile),gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),''),tree=buildCollisionOctree(gltf.scene),routes=JSON.parse(fs.readFileSync('/workspace/shared/sunward-structure-build/runtime/diagnostic-r1/routes.json','utf8')).routes.filter(r=>r.category==='stairs'&&r.name.endsWith('_down'));
 const convert=p=>new Vector3(p[0],p[2],-p[1]);
 function actualTrace(C,route,sprint){const points=route.feet_blender.map(convert),start=points[0],goal=points.at(-1),delta=goal.clone().sub(start);delta.y=0;const length=delta.length(),axis=delta.normalize(),player=spawn(C,tree,start);let core=0,ungrounded=0,maxRun=0,run=0,frames=0;for(;frames<300;frames++){const current=foot(player),dx=goal.x-current.x,dz=goal.z-current.z;if(Math.hypot(dx,dz)<.1)break;const dist=Math.hypot(dx,dz);player.update(1/60,{x:dx/dist,z:-dz/dist,sprint});const f=foot(player),progress=f.clone().sub(start).dot(axis)/length;if(progress>.12&&progress<.88){core++;if(!player.onFloor)ungrounded++;}if(!player.onFloor){run++;maxRun=Math.max(maxRun,run);}else run=0;}return {controller:C===Proposed?'proposed':'original',route:route.name,sprint,core_samples:core,core_ungrounded_frames:ungrounded,max_unsupported_frames:maxRun,frames,terminal_feet:foot(player).toArray(),scope:'old-family diagnostic geometry flight core only; known source-anchor/wall defects are not accepted by this controller benchmark'};}
 for(const route of routes)for(const sprint of [false,true])test(`diagnostic authored ${route.name} ${sprint?'sprint':'walk'} keeps real flight contact`,()=>{const baseline=actualTrace(Original,route,sprint),proposed=actualTrace(Proposed,route,sprint);report.traces.push(baseline,proposed);assert.ok(proposed.core_samples>0);assert.equal(proposed.core_ungrounded_frames,0);return {baseline_ungrounded_core_frames:baseline.core_ungrounded_frames,proposed_ungrounded_core_frames:proposed.core_ungrounded_frames,baseline_max_unsupported_frames:baseline.max_unsupported_frames,proposed_max_unsupported_frames:proposed.max_unsupported_frames};});
}
report.passed=report.cases.every(c=>c.passed);const file='/workspace/shared/sunward-strike/docs/qa/structure-review/physics-zero-negative-independent.json';fs.writeFileSync(file,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({file,passed:report.passed,cases:report.cases},null,2));process.exitCode=report.passed?0:1;
