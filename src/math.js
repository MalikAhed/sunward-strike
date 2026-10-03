import {MAP_CONFIG} from './map-config.js';
export const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
export const lerp = (a, b, t) => a + (b-a)*t;
export const damp = (a, b, speed, dt) => lerp(a, b, 1-Math.exp(-speed*dt));
export function normalizedInput(x,y,z){const length=Math.hypot(x,y,z);return length>1?[x/length,y/length,z/length]:[x,y,z];}
export function yawPitchDirection(yaw,pitch){return [-Math.sin(yaw)*Math.cos(pitch),Math.sin(pitch),-Math.cos(yaw)*Math.cos(pitch)];}
export function rotationFromLook(position,target){const dx=target[0]-position[0],dy=target[1]-position[1],dz=target[2]-position[2];return {yaw:Math.atan2(-dx,-dz),pitch:Math.atan2(dy,Math.hypot(dx,dz))};}
// Ray crossing with an edge-distance margin supports the traced irregular outline.
export function withinPlayBounds(x,z,margin=.45){
  const points=MAP_CONFIG.outline;
  let inside=false;
  for(let i=0,j=points.length-1;i<points.length;j=i++){
    const [ax,az]=points[j], [bx,bz]=points[i];
    if((az>z)!==(bz>z)&&x<(bx-ax)*(z-az)/(bz-az)+ax)inside=!inside;
    const dx=bx-ax,dz=bz-az,t=clamp(((x-ax)*dx+(z-az)*dz)/(dx*dx+dz*dz),0,1);
    if(Math.hypot(x-ax-dx*t,z-az-dz*t)<=margin)return false;
  }
  return inside;
}
export const VIEWPOINTS=MAP_CONFIG.viewpoints;

// Fit the entire traced map at overview presets on narrow as well as wide screens.
export function fittedOverviewPosition(view,aspect,fov=58){
  const dot=(a,b)=>a.reduce((s,n,i)=>s+n*b[i],0);
  const unit=v=>{const d=Math.hypot(...v);return v.map(n=>n/d);};
  const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
  const forward=unit(view.target.map((n,i)=>n-view.position[i]));
  const right=unit(cross(forward,[0,1,0])),up=cross(right,forward);
  const tanV=Math.tan(fov*Math.PI/360),tanH=tanV*Math.max(.25,aspect);
  let distance=Math.hypot(...view.target.map((n,i)=>n-view.position[i]));
  for(const [x,z] of MAP_CONFIG.outline)for(const y of [0,12]){
    const q=[x-view.target[0],y-view.target[1],z-view.target[2]],depth=dot(q,forward);
    distance=Math.max(distance,Math.abs(dot(q,right))/(tanH*.86)-depth,Math.abs(dot(q,up))/(tanV*.78)-depth);
  }
  return view.target.map((n,i)=>n-forward[i]*distance);
}

export function overviewFrameOnResize(viewpoint,aspect,{active,mode}){
  return active&&mode!=='walk'&&['hero','topdown'].includes(viewpoint)
    ? fittedOverviewPosition(VIEWPOINTS[viewpoint],aspect) : null;
}

export const overviewFrameAfterModeChange=(active,mode)=>mode==='walk'?false:active;
