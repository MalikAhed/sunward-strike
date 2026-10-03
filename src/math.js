export const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
export const lerp = (a, b, t) => a + (b-a)*t;
export const damp = (a, b, speed, dt) => lerp(a, b, 1-Math.exp(-speed*dt));
export function normalizedInput(x,y,z){const length=Math.hypot(x,y,z);return length>1?[x/length,y/length,z/length]:[x,y,z];}
export function yawPitchDirection(yaw,pitch){return [-Math.sin(yaw)*Math.cos(pitch),Math.sin(pitch),-Math.cos(yaw)*Math.cos(pitch)];}
export function rotationFromLook(position,target){const dx=target[0]-position[0],dy=target[1]-position[1],dz=target[2]-position[2];return {yaw:Math.atan2(-dx,-dz),pitch:Math.atan2(dy,Math.hypot(dx,dz))};}
export function withinPlayBounds(x,z,margin=.45){return Math.abs(x)<29-margin&&Math.abs(z)<37-margin;}
export const VIEWPOINTS = Object.freeze({
  hero:{label:'Hero view',position:[43,34,49],target:[0,2,0]},
  street:{label:'Central street',position:[-15,2,0],target:[4,2,1]},
  mint:{label:'Mint courtyard',position:[-13,3,-31],target:[0,3,-17]},
  saffron:{label:'Saffron courtyard',position:[13,3,31],target:[0,3,17]},
  rooftop:{label:'Rooftop survey',position:[13,13,24],target:[0,3,-12]},
  topdown:{label:'Top down',position:[0,75,.01],target:[0,0,0]}
});
