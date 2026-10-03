export function hashSeed(seed,label){let hash=(seed>>>0)^2166136261;for(const character of String(label)){hash^=character.charCodeAt(0);hash=Math.imul(hash,16777619);}return hash>>>0;}
export class SeededRandom{
  constructor(seed=1){this.state=seed>>>0;}
  next(){let value=this.state+=0x6D2B79F5;value=Math.imul(value^value>>>15,value|1);value^=value+Math.imul(value^value>>>7,value|61);this.state>>>=0;return ((value^value>>>14)>>>0)/4294967296;}
  range(min,max){return min+(max-min)*this.next();}
  integer(min,max){return Math.floor(this.range(min,max+1));}
  pick(values){return values.length?values[Math.floor(this.next()*values.length)]:null;}
}
