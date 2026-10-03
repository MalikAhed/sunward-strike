// Deliberately small DOM model for portable integration checks. This is not a
// browser, CSS layout engine, WebGL implementation or visual acceptance proof.
export class NodeModel {
  constructor(tag = 'div', attrs = {}, document = null) {
    this.tagName = tag.toUpperCase(); this.attrs = {...attrs}; this.document = document;
    this.children = []; this.parentNode = null; this.handlers = new Map(); this.dataset = {};
    this.style = {setProperty(name, value) { this[name] = value; }};
    this._text = ''; this.value = attrs.value ?? ''; this.disabled = 'disabled' in attrs;
    this.classes = new Set((attrs.class ?? '').split(/\s+/).filter(Boolean));
    for (const [name, value] of Object.entries(attrs)) if (name.startsWith('data-')) this.dataset[name.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())] = value;
    this.classList = {add: (...names) => names.forEach(name => this.classes.add(name)), remove: (...names) => names.forEach(name => this.classes.delete(name)),
      contains: name => this.classes.has(name), toggle: (name, force) => { const next = force === undefined ? !this.classes.has(name) : force; if(next)this.classes.add(name);else this.classes.delete(name); return next; }};
  }
  set textContent(value) { this._text = String(value); }
  get textContent() { return this._text; }
  set className(value) { this.classes = new Set(value.split(/\s+/).filter(Boolean)); }
  get className() { return [...this.classes].join(' '); }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  getAttribute(name) { return this.attrs[name] ?? null; }
  append(...nodes) { for(const node of nodes){node.parentNode=this;this.children.push(node);} }
  addEventListener(type, fn) { if(!this.handlers.has(type))this.handlers.set(type,new Set()); this.handlers.get(type).add(fn); }
  removeEventListener(type, fn) { this.handlers.get(type)?.delete(fn); }
  dispatch(type, event = {}) { const result={target:this,button:0,pointerId:1,preventDefault(){this.defaultPrevented=true;},...event}; for(const fn of this.handlers.get(type)??[])fn(result); return result; }
  matches(selector) {
    if(selector.startsWith('#'))return this.attrs.id===selector.slice(1);
    if(selector.startsWith('.'))return this.classes.has(selector.slice(1));
    const match=selector.match(/^(\w+)?(?:\[([\w-]+)(?:="([^"]*)")?\])?$/);
    return Boolean(match && (!match[1] || this.tagName===match[1].toUpperCase()) && (!match[2] || match[2] in this.attrs && (match[3]===undefined || this.attrs[match[2]]===match[3])));
  }
  querySelectorAll(selector) { const selectors=selector.split(',').map(value=>value.trim()),out=[]; const visit=node=>{for(const child of node.children){if(selectors.some(s=>child.matches(s)))out.push(child);visit(child);}};visit(this);return out; }
  querySelector(selector) { return this.querySelectorAll(selector)[0]??null; }
  closest(selector) { let node=this;while(node){if(node.matches(selector))return node;node=node.parentNode;}return null; }
  focus() { if(this.document)this.document.activeElement=this; }
  setPointerCapture() {}
  get options() { return this.children.filter(child=>child.tagName==='OPTION'); }
}
export function parseDOM(html) {
  const document=new NodeModel('document');document.document=document;document.activeElement=null;
  document.getElementById=id=>document.querySelector(`#${id}`);
  document.createElement=tag=>new NodeModel(tag,{},document);
  const stack=[document],voids=new Set(['meta','link','img','br','input','hr','source','path']);
  for(const token of html.matchAll(/<\/?[a-zA-Z][^>]*>|[^<]+/g)){
    const text=token[0];if(!text.startsWith('<')){stack.at(-1)._text+=text;continue;}
    const close=text.match(/^<\/([\w-]+)/);if(close){for(let i=stack.length-1;i>0;i--)if(stack[i].tagName===close[1].toUpperCase()){stack.length=i;break;}continue;}
    const tag=text.match(/^<([\w-]+)/)[1],attrs={};
    const rest=text.slice(tag.length+1,-1);for(const attr of rest.matchAll(/([\w-]+)(?:="([^"]*)"|='([^']*)')?/g))attrs[attr[1]]=attr[2]??attr[3]??'';
    const node=new NodeModel(tag,attrs,document);stack.at(-1).append(node);if(!voids.has(tag)&&!text.endsWith('/>'))stack.push(node);
  }
  for(const select of document.querySelectorAll('select'))select.value=select.options.find(option=>'selected'in option.attrs)?.value??select.options[0]?.value??'';
  return document;
}
