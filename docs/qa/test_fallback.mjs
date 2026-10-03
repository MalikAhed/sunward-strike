// Independent fail-path simulation of the actual fallback/start source.
// Mock DOM and forced renderer error: not browser rendering or layout evidence.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const root=new URL('../../',import.meta.url);
const source=fs.readFileSync(new URL('src/main.js',root),'utf8');
let prefix=source.slice(source.indexOf('const $'),source.indexOf('function start()'));
prefix=prefix.replaceAll('import.meta.env.BASE_URL',JSON.stringify('./'));
const startPrefix=source.slice(source.indexOf('function start()'),source.indexOf('renderer.outputColorSpace'));
class Element {
 constructor(tag='div'){this.tag=tag;this.children=[];this.classes=new Set();this.listeners={};this.attrs={};this.classList={add:(...cs)=>cs.forEach(c=>this.classes.add(c))};}
 append(...children){this.children.push(...children);}
 setAttribute(k,v){this.attrs[k]=v;}
 addEventListener(k,f){this.listeners[k]=f;}
}
const elements=new Map();const element=(name)=>{if(!elements.has(name))elements.set(name,new Element());return elements.get(name);};
const document={getElementById:(id)=>element('#'+id),querySelector:element,createElement:(tag)=>new Element(tag)};
const warnings=[];let reloads=0;
const context=vm.createContext({document,window:{},location:{reload(){reloads++;}},console:{warn(...xs){warnings.push(xs.map(String).join(' '));}},THREE:{WebGLRenderer:class{constructor(){throw new Error('Forced unavailable WebGL2');}}}});
vm.runInContext(prefix+startPrefix+'globalThis.runtimeEntered=true;\n}\nstart();',context);
assert.notEqual(context.runtimeEntered,true,'Failure must return before renderer/animation setup');
const debug=context.window.sunwardDebug;
assert.equal(debug.fallback,true);assert.equal(debug.ready,false);assert.equal(debug.renderer.webgl2,false);
const fallback=element('#app').children[0];assert.equal(fallback.className,'graphics-fallback');
const [poster,card]=fallback.children;assert.equal(poster.src,'./assets/map-poster.png');assert.match(poster.alt,/Static Blender/);
assert.equal(card.children[0].textContent,'STATIC SOURCE PREVIEW');
assert.match(card.children[2].textContent,/static Blender preview/);
const retry=card.children.at(-1);assert.equal(retry.textContent,'RETRY PAGE');retry.listeners.click();assert.equal(reloads,1);
for(const id of ['#loading','#intro','#controls','#help-toggle','#fullscreen','.mode-switch','.bottombar','.touch-controls'])assert.ok(element(id).classes.has('hidden'),id+' hidden');
assert.equal(warnings.length,1);
const out={method:'Actual fallback/start source extracted into VM with mock DOM and forced WebGLRenderer error. No browser visual/layout test implied.',passed:true,checks:['No cascading renderer/animation setup after failure','Explicit static-source label and truthful poster alt/description','Relative poster path','Dead controls hidden','Retry Page invokes reload','Read-only debug reports fallback=true, ready=false, webgl2=false']};
fs.writeFileSync(new URL('docs/qa/fallback-results.json',root),JSON.stringify(out,null,2)+'\n');
console.log(JSON.stringify(out,null,2));
