// Manager installs as tests/physics.test.js. Actual live controller, no browser.
import test from 'node:test';import assert from 'node:assert/strict';
import {Vector3,Group,Mesh,BufferGeometry,Float32BufferAttribute,PlaneGeometry,BoxGeometry,MeshBasicMaterial} from 'three';
import {WalkController} from '../../../src/physics.js';import {buildCollisionOctree} from '../../../src/collision.js';
const foot=p=>p.collider.start.clone().add(new Vector3(0,-.35,0));
function plane(root,width,depth,x,y){const m=new Mesh(new PlaneGeometry(width,depth),new MeshBasicMaterial());m.rotation.x=-Math.PI/2;m.position.set(x,y,0);root.add(m);}
function rampTree(yaw=0){const root=new Group();plane(root,12,8,-6,.18);plane(root,12,8,12,3.18);const g=new BufferGeometry();g.setAttribute('position',new Float32BufferAttribute([0,.18,-2,0,.18,2,6,3.18,2,6,3.18,-2],3));g.setIndex([0,1,2,0,2,3]);root.add(new Mesh(g,new MeshBasicMaterial()));root.rotation.y=yaw;return buildCollisionOctree(root);}
const orient=(x,y,yaw)=>new Vector3(Math.cos(yaw)*x,y,-Math.sin(yaw)*x);
function spawn(tree,feet){const p=new WalkController(tree);p.spawn(feet.clone().add(new Vector3(0,1.64,0)));for(let i=0;i<120;i++)p.update(1/60);return p;}
for(const yaw of [0,Math.PI/2])for(const sprint of [false,true])for(const dt of [1/60,1/30])test(`continuous ${sprint?'sprint':'walk'} descends ${yaw?'interior':'exterior'} axis ramp at${Math.round(1/dt)}Hz`,()=>{
 const p=spawn(rampTree(yaw),orient(7,3.18,yaw)),goal=orient(-1,.18,yaw);let samples=0;
 for(let i=0;i<Math.ceil(10/dt);i++){const f=foot(p),dx=goal.x-f.x,dz=goal.z-f.z,dist=Math.hypot(dx,dz);if(dist<.1)break;p.update(dt,{x:dx/dist,z:-dz/dist,sprint});const next=foot(p),localX=next.x*Math.cos(yaw)-next.z*Math.sin(yaw);if(localX>.6&&localX<5.4){samples++;assert.equal(p.onFloor,true);}}
 for(let i=0;i<90;i++)p.update(1/60);assert.ok(samples>0);assert.ok(foot(p).distanceTo(goal)<.16);assert.equal(p.onFloor,true);
});
test('one-meter ledge falls without teleporting or retaining grounded contact',()=>{
 const root=new Group();plane(root,10,8,5,1);plane(root,12,8,-6,0);const p=spawn(buildCollisionOctree(root),new Vector3(1.5,1,0));let firstBeyond=null,largestDrop=0,prev=foot(p).y,airborne=0;
 for(let i=0;i<150;i++){p.update(1/60,{x:-1});const f=foot(p);largestDrop=Math.max(largestDrop,prev-f.y);prev=f.y;if(f.x<-.4&&!firstBeyond)firstBeyond={y:f.y,onFloor:p.onFloor};if(!p.onFloor)airborne++;}
 assert.ok(firstBeyond&&firstBeyond.y>.5);assert.equal(firstBeyond.onFloor,false);assert.ok(airborne>5);assert.ok(largestDrop<.22);assert.equal(p.onFloor,true);assert.ok(Math.abs(foot(p).y)<.03);
});
test('flat jump retains upward velocity and lands normally',()=>{
 const root=new Group();plane(root,20,20,0,0);const p=spawn(buildCollisionOctree(root),new Vector3(0,0,0)),initial=foot(p).y;let peak=initial;
 for(let i=0;i<120;i++){p.update(1/60,{jump:i===0});peak=Math.max(peak,foot(p).y);if(i<8){assert.ok(p.velocity.y>0);assert.equal(p.onFloor,false);}}
 assert.ok(peak>initial+.5);assert.equal(p.onFloor,true);assert.ok(Math.abs(foot(p).y)<.03);
});
test('wall/floor jump remains available without passing through wall',()=>{
 const root=new Group();plane(root,20,20,0,0);const wall=new Mesh(new BoxGeometry(.2,4,10),new MeshBasicMaterial());wall.position.set(2,2,0);root.add(wall);const p=spawn(buildCollisionOctree(root),new Vector3(0,0,0));for(let i=0;i<120;i++)p.update(1/60,{x:1});assert.equal(p.onFloor,true);const initial=foot(p).y;let peak=initial;
 for(let i=0;i<60;i++){p.update(1/60,{x:1,jump:i===0});peak=Math.max(peak,foot(p).y);assert.ok(foot(p).x<1.56);}assert.ok(peak>initial+.5);
});
test('downhill ramp snap never cancels upward jump',()=>{
 const p=spawn(rampTree(),new Vector3(4,2.222,0)),initial=foot(p).y;let peak=initial;for(let i=0;i<60;i++){p.update(1/60,{x:-1,jump:i===0});peak=Math.max(peak,foot(p).y);if(i<8){assert.ok(p.velocity.y>0);assert.equal(p.onFloor,false);}}assert.ok(peak>initial+.5);
});
