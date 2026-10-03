import test from 'node:test';
import assert from 'node:assert/strict';
import {MatchAudio} from '../src/gameplay/match-audio.js';
function fakeContext(){
 const nodes=[];
 const parameter=()=>({value:0,setValueAtTime(){},exponentialRampToValueAtTime(){}});
 const node=()=>{const value={frequency:parameter(),gain:parameter(),connect(target){return target;},disconnect(){this.disconnected=true;},start(){this.started=true;},stop(){this.stopped=true;}};nodes.push(value);return value;};
 return {state:'suspended',currentTime:0,sampleRate:8000,destination:node(),nodes,resumes:0,
  resume(){this.state='running';this.resumes++;return Promise.resolve();},close(){this.state='closed';return Promise.resolve();},
  createOscillator:node,createGain:node,createBiquadFilter:node,createBufferSource:node,
  createBuffer(_channels,length){return {getChannelData:()=>new Float32Array(length)};},
 };
}
test('sound never creates/resumes a context from simulation events',()=>{
 let created=0;const context=fakeContext(),audio=new MatchAudio({contextFactory:()=>{created++;return context;}});
 audio.shot();audio.hit();audio.reload();audio.death();audio.tag();assert.equal(created,0);
 audio.activate();assert.equal(created,1);assert.equal(context.resumes,1);audio.shot();assert.equal(context.resumes,1);assert.ok(audio.voices.size>0);
 audio.dispose();assert.equal(context.state,'closed');assert.equal(audio.voices.size,0);
});
test('procedural cues are bounded, muted immediately and disconnect ended voices',()=>{
 const context=fakeContext(),audio=new MatchAudio({contextFactory:()=>context,maxVoices:8});audio.activate();
 for(let i=0;i<80;i++){context.currentTime+=.1;audio.shot();audio.reload(i%2===0);audio.hit();audio.tag(i%2===0);}
 assert.ok(audio.voices.size<=8);assert.ok(context.nodes.some(node=>node.stopped&&node.disconnected));
 const first=audio.voices.values().next().value;first.source.onended();assert.equal(audio.voices.has(first),false);assert.equal(first.source.disconnected,true);
 audio.setEnabled(false);assert.equal(audio.voices.size,0);const count=context.nodes.length;audio.shot();audio.reload();assert.equal(context.nodes.length,count);
 audio.setEnabled(true);audio.activate();audio.death();assert.equal(audio.voices.size,1);audio.stopAll();assert.equal(audio.voices.size,0);
});
