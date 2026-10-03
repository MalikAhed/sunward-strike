export const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
export const add=(a,b)=>a.map((v,i)=>v+b[i]);
export const sub=(a,b)=>a.map((v,i)=>v-b[i]);
export const scale=(a,n)=>a.map(v=>v*n);
export const dot=(a,b)=>a.reduce((sum,v,i)=>sum+v*b[i],0);
export const length=a=>Math.hypot(...a);
export const distance=(a,b)=>length(sub(a,b));
export const normalize=a=>{const n=length(a);return n>1e-10?scale(a,1/n):[0,0,-1];};
export const forward=(yaw,pitch=0)=>[-Math.sin(yaw)*Math.cos(pitch),Math.sin(pitch),-Math.cos(yaw)*Math.cos(pitch)];
export const angles=direction=>{const d=normalize(direction);return{yaw:Math.atan2(-d[0],-d[2]),pitch:Math.asin(clamp(d[1],-1,1))};};
export const wrapAngle=a=>Math.atan2(Math.sin(a),Math.cos(a));
export function turnAngle(from,to,maxStep){return from+clamp(wrapAngle(to-from),-maxStep,maxStep);}
export function finitePoint(point){return Array.isArray(point)&&point.length===3&&point.every(Number.isFinite);}
