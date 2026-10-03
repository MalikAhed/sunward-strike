import {Vector3,Ray} from 'three';
import {Capsule} from 'three/addons/math/Capsule.js';
import {normalizedInput} from './math.js';

// Original capsule controller. The authored collision GLB supplies stair ramps.
export class WalkController {
  constructor(tree=null){this.tree=tree;this.collider=new Capsule(new Vector3(0,.4,-31),new Vector3(0,1.5,-31),.35);this.velocity=new Vector3();this.onFloor=false;this.groundAge=Infinity;this.delta=new Vector3();this.floorRay=new Ray(new Vector3(),new Vector3(0,-1,0));this.floorNormal=new Vector3();}
  spawn(cameraPosition){const feet=cameraPosition.y-1.64;this.collider.start.set(cameraPosition.x,feet+.35,cameraPosition.z);this.collider.end.set(cameraPosition.x,feet+1.45,cameraPosition.z);this.velocity.set(0,0,0);this.onFloor=false;this.groundAge=Infinity;}
  update(dt,{x=0,z=0,yaw=0,sprint=false,jump=false}={}){
    if(!this.tree)return;
    const input=normalizedInput(x,0,z),speed=sprint?7.1:4.4;
    for(let i=0;i<5;i++){
      const step=dt/5,sin=Math.sin(yaw),cos=Math.cos(yaw),wasOnFloor=this.onFloor;
      this.velocity.x=(cos*input[0]-sin*input[2])*speed;
      this.velocity.z=(-sin*input[0]-cos*input[2])*speed;
      if(this.onFloor){this.velocity.y=0;if(jump){this.velocity.y=5.5;jump=false;}}else this.velocity.y-=19*step;
      this.collider.translate(this.delta.copy(this.velocity).multiplyScalar(step));
      const hit=this.tree.capsuleIntersect(this.collider);this.onFloor=false;
      if(hit){this.onFloor=hit.normal.y>.45;const inward=hit.normal.dot(this.velocity);if(inward<0)this.velocity.addScaledVector(hit.normal,-inward);this.collider.translate(hit.normal.multiplyScalar(hit.depth));}
      // The octree returns one combined resolution normal. At a wall/floor
      // corner its Y component can vanish although the feet still touch floor.
      // Probe vertically from the lower capsule center to retain that contact.
      if(!this.onFloor&&this.velocity.y<=.001){
        this.floorRay.origin.copy(this.collider.start);
        const floor=this.tree.rayIntersect(this.floorRay);
        if(floor){
          floor.triangle.getNormal(this.floorNormal);
          if(this.floorNormal.y>.45){
            // Retain recent grounded, nonascending contact over a small real
            // surface descent. Sphere support height depends on slope; the
            // signed lip tolerance never translates the capsule upward.
            const drop=floor.distance-this.collider.radius/this.floorNormal.y;
            if((wasOnFloor||this.groundAge<=.03)&&drop>=-.05&&drop<=.08){
              this.collider.translate(this.delta.set(0,-Math.max(0,drop),0));
              this.onFloor=true;this.velocity.y=0;
            }else if(floor.distance<=this.collider.radius+.025){
              this.onFloor=true;this.velocity.y=Math.max(0,this.velocity.y);
            }
          }
        }
      }
      this.groundAge=this.onFloor?0:this.groundAge+step;
    }
  }
  cameraPosition(target){return target.copy(this.collider.end).add(new Vector3(0,.19,0));}
}
