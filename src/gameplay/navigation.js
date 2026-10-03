import {distance} from './vectors.js';
export class WaypointNavigation{
  constructor(data,{canTraverse=()=>true,connectRadius=1.3}={}){
    this.nodes=data.nodes.map((position,index)=>({id:String(index),position:[...position]}));this.edges=this.nodes.map(()=>new Map());this.canTraverse=canTraverse;
    const link=(a,b)=>{if(a===b)return;const cost=distance(this.nodes[a].position,this.nodes[b].position);this.edges[a].set(b,cost);this.edges[b].set(a,cost);};
    for(const [a,b]of data.edges)if(this.nodes[a]&&this.nodes[b])link(a,b);
    const cells=new Map(),size=connectRadius;
    for(let i=0;i<this.nodes.length;i++){const p=this.nodes[i].position,c=[Math.floor(p[0]/size),Math.floor(p[2]/size)];for(let x=c[0]-1;x<=c[0]+1;x++)for(let z=c[1]-1;z<=c[1]+1;z++)for(const j of cells.get(x+','+z)||[]){const q=this.nodes[j].position;if(distance(p,q)<=connectRadius&&Math.abs(p[1]-q[1])<.5&&canTraverse(p,q))link(i,j);}const key=c.join(',');if(!cells.has(key))cells.set(key,[]);cells.get(key).push(i);}
  }
  nearest(position,{blocked=new Set(),limit=4}={}){return this.nodes.map((node,index)=>({node,index,distance:distance(node.position,position)})).filter(x=>!blocked.has(x.node.id)).sort((a,b)=>a.distance-b.distance).slice(0,12).find(x=>x.distance<=limit&&this.canTraverse(position,x.node.position))?.index??null;}
  findPath(start,goal,{blocked=new Set()}={}){
    if(this.canTraverse(start,goal))return {points:[[...goal]],nodeIds:[]};
    const begin=this.nearest(start,{blocked}),end=this.nearest(goal,{blocked});if(begin===null||end===null)return {points:[],nodeIds:[]};
    const open=[begin],best=new Map([[begin,0]]),parent=new Map(),closed=new Set();
    while(open.length){open.sort((a,b)=>(best.get(b)+distance(this.nodes[b].position,goal))-(best.get(a)+distance(this.nodes[a].position,goal)));const current=open.pop();if(closed.has(current))continue;if(current===end){const ids=[end];let node=end;while(node!==begin){node=parent.get(node);ids.push(node);}ids.reverse();const points=ids.map(id=>[...this.nodes[id].position]);if(this.canTraverse(points.at(-1),goal))points.push([...goal]);return {points,nodeIds:ids.map(String)};}closed.add(current);for(const [next,cost]of this.edges[current]){if(closed.has(next)||blocked.has(String(next)))continue;const value=best.get(current)+cost;if(value<(best.get(next)??Infinity)){best.set(next,value);parent.set(next,current);open.push(next);}}}
    return {points:[],nodeIds:[]};
  }
  patrolPoints(){this._patrolPoints ||= this.nodes.filter(node=>this.canTraverse(node.position,node.position)).map(node=>[...node.position]);return this._patrolPoints.map(point=>[...point]);}
}
