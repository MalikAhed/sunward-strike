import {GAMEPLAY_TUNING} from './tuning.js';
import {clamp,dot,sub,add,scale,forward} from './vectors.js';
const radians=Math.PI/180;
export function damageAtRange(weapon,distance,zone='body'){
  const fraction=clamp((distance-weapon.nearRange)/(weapon.farRange-weapon.nearRange),0,1);
  return (weapon.damageNear+(weapon.damageFar-weapon.damageNear)*fraction)*(zone==='head'?weapon.headMultiplier:1);
}
export function idealTimeToKill(weapon,health=100,range=0,zone='body') {return Math.max(0,Math.ceil(health/damageAtRange(weapon,range,zone))-1)*60/weapon.rpm;}
function raySphere(origin,direction,center,radius){const offset=sub(origin,center),b=dot(offset,direction),c=dot(offset,offset)-radius*radius;if(c<=0)return 0;const discriminant=b*b-c;if(discriminant<0)return Infinity;const hit=-b-Math.sqrt(discriminant);return hit>=0?hit:Infinity;}
// Exact intersection with a vertical capsule, including inside origins and caps.
export function rayActor(origin,direction,actor){
  const radius=actor.radius??GAMEPLAY_TUNING.actor.radius,height=Math.max(radius*2,actor.height??GAMEPLAY_TUNING.actor.height),feet=actor.position;
  const lower=[feet[0],feet[1]+radius,feet[2]],upper=[feet[0],feet[1]+height-radius,feet[2]];
  let nearest=Math.min(raySphere(origin,direction,lower,radius),raySphere(origin,direction,upper,radius));
  const ox=origin[0]-feet[0],oz=origin[2]-feet[2],a=direction[0]**2+direction[2]**2,b=ox*direction[0]+oz*direction[2],c=ox*ox+oz*oz-radius*radius;
  if(c<=0&&origin[1]>=lower[1]&&origin[1]<=upper[1])nearest=0;
  if(a>1e-12){const discriminant=b*b-a*c;if(discriminant>=0)for(const hit of[(-b-Math.sqrt(discriminant))/a,(-b+Math.sqrt(discriminant))/a]){const y=origin[1]+direction[1]*hit;if(hit>=0&&y>=lower[1]&&y<=upper[1])nearest=Math.min(nearest,hit);}}
  if(!Number.isFinite(nearest))return null;
  const point=add(origin,scale(direction,nearest));return {distance:nearest,point,zone:point[1]-feet[1]>=height*.795?'head':'body'};
}
export function traceShot({origin,direction,range,shooterId,actors,world}){
  const obstruction=world.raycast(origin,direction,range);
  const wallDistance=typeof obstruction==='number'?obstruction:obstruction?.distance??Infinity;
  let nearest=Math.min(range,Math.max(0,wallDistance)),target=null,impact=null;
  for(const actor of actors){if(!actor.alive||actor.id===shooterId)continue;const hit=rayActor(origin,direction,actor);if(hit&&hit.distance<nearest-1e-6){nearest=hit.distance;target=actor;impact=hit;}}
  return {actor:target,zone:impact?.zone??null,distance:nearest,point:add(origin,scale(direction,nearest)),hitWorld:!target&&wallDistance<=range};
}
export class WeaponState{
  constructor(weaponId='carbine',random,overrides={}){if(!GAMEPLAY_TUNING.weapons[weaponId])throw new RangeError('Unknown weapon');this.id=weaponId;this.spec={...GAMEPLAY_TUNING.weapons[weaponId],...overrides};this.random=random;this.reset();}
  reset(){this.ammo=this.spec.magazine;this.reserve=this.spec.reserveAmmo;this.reloading=false;this.reloadEndsAt=Infinity;this.nextShotAt=0;this.lastSprintAt=-Infinity;this.lastShotAt=-Infinity;this.adsFraction=0;this.recoil=[0,0];this.triggerHeld=false;this.reloadHeld=false;this.shotCount=0;this.dryAt=-Infinity;}
  beginReload(time,events){if(this.reloading||this.ammo===this.spec.magazine||(!this.spec.infiniteReserve&&this.reserve<=0))return false;this.reloading=true;this.reloadEndsAt=time+(this.ammo===0?this.spec.reloadEmpty:this.spec.reloadTactical);events.push({type:'reload-started',time,endsAt:this.reloadEndsAt});return true;}
  step(start,end,command={},context={}){
    const events=[],dt=end-start,spec=this.spec;this.adsFraction=clamp(this.adsFraction+(command.ads?1:-1)*dt/spec.adsSeconds,0,1);
    if(context.sprinting)this.lastSprintAt=end;
    if(start-this.lastShotAt>.10){const decay=Math.exp(-spec.recoilRecovery*dt);this.recoil=this.recoil.map(value=>value*decay);}
    if(command.reload&&!this.reloadHeld)this.beginReload(start,events);this.reloadHeld=!!command.reload;
    let reloadCompletedAt=-Infinity;
    if(this.reloading&&this.reloadEndsAt<=end+1e-9){reloadCompletedAt=this.reloadEndsAt;const need=spec.magazine-this.ammo,given=spec.infiniteReserve?need:Math.min(need,this.reserve);this.ammo+=given;if(!spec.infiniteReserve)this.reserve-=given;this.reloading=false;events.push({type:'reload-completed',time:reloadCompletedAt,ammo:this.ammo,reserve:this.reserve});}
    const trigger=!!command.fire&&context.alive!==false;
    if(trigger&&!this.triggerHeld)this.nextShotAt=Math.max(start,this.nextShotAt);this.triggerHeld=trigger;
    if(!trigger||this.reloading||context.sprinting)return events;
    this.nextShotAt=Math.max(this.nextShotAt,start,this.lastSprintAt+spec.sprintToFire,reloadCompletedAt);
    while(this.nextShotAt<=end+1e-9){
      const time=this.nextShotAt;
      if(this.ammo<=0){if(time-this.dryAt>.2){events.push({type:'dry-fire',time});this.dryAt=time;}this.beginReload(time,events);break;}
      this.ammo--;this.lastShotAt=time;this.shotCount++;
      const spread=(spec.hipSpreadDegrees+(spec.adsSpreadDegrees-spec.hipSpreadDegrees)*this.adsFraction)*(context.moving?spec.movingSpread:1)*(context.airborne?spec.airSpread:1)*(context.sliding?spec.slideSpread:1)*radians;
      const azimuth=this.random.next()*Math.PI*2,radius=Math.sqrt(this.random.next())*spread;
      const yaw=(command.yaw||0)+this.recoil[1]+Math.cos(azimuth)*radius,pitch=clamp((command.pitch||0)+this.recoil[0]+Math.sin(azimuth)*radius,-1.5,1.5);
      events.push({type:'shot-request',time,direction:forward(yaw,pitch),ammo:this.ammo,shotNumber:this.shotCount,adsFraction:this.adsFraction});
      this.recoil[0]=Math.min(spec.maxRecoilDegrees*radians,this.recoil[0]+spec.recoilPitchDegrees*radians);this.recoil[1]=clamp(this.recoil[1]+this.random.range(-spec.recoilYawDegrees,spec.recoilYawDegrees)*radians,-spec.maxRecoilDegrees*radians,spec.maxRecoilDegrees*radians);
      this.nextShotAt+=60/spec.rpm;
    }
    return events;
  }
  snapshot(){return {id:this.id,ammo:this.ammo,reserve:this.reserve,infiniteReserve:this.spec.infiniteReserve,reloading:this.reloading,reloadEndsAt:this.reloading?this.reloadEndsAt:null,adsFraction:this.adsFraction,recoil:[...this.recoil],shotCount:this.shotCount};}
}
