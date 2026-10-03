"""Reversible p1r5 lawn-only overlay on material-palette p1r5 base.
Original deterministic 512px turf tile, never derived from reference image pixels.
No mesh, UV, transform, light, world, collision or non-lawn material changes.
"""
import bpy, numpy as np, json, hashlib, importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
VERSION='lawn-finish-p1r5'
NAME='V3_Tone_TurfCarpet_p1r5'
KEY='palette_p1r5_lawn_original_slot_'

def linear_to_srgb(a):return np.where(a<=.0031308,12.92*a,1.055*np.maximum(a,0)**(1/2.4)-.055)
def srgb_to_linear(a):return np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
def base_module():
 path=HERE/'material_palette_patch.py'
 spec=importlib.util.spec_from_file_location('palette_p1r5_base',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def turf_arrays(n=512):
 rng=np.random.default_rng(418529)
 y,x=np.mgrid[0:n,0:n].astype(np.float32);x/=n;y/=n
 def periodic_field(freqs):
  result=np.zeros((n,n),np.float32)
  for lo,hi,amplitude in freqs:
   for _ in range(7):
    fx=int(rng.integers(lo,hi+1));fy=int(rng.integers(-hi,hi+1));phase=float(rng.uniform(0,2*np.pi))
    result+=amplitude*np.sin(2*np.pi*(x*fx+y*fy)+phase)/7
  return result
 field=periodic_field([(2,5,.28),(11,23,.17),(47,97,.10)])
 noise=rng.uniform(-.035,.035,(n,n)).astype(np.float32)
 # Low-amplitude irregular color variation is turf pigmentation/occlusion, not painted cast shadows.
 base=np.array([.165,.275,.028],np.float32)
 rgb=np.clip(base[None,None,:]*(1+field[:,:,None]+noise[:,:,None]),0,1)
 cool=np.clip(-field-.015,0,.30)[:,:,None]
 rgb=rgb*(1-cool)+np.array([.055,.145,.047],np.float32)*cool
 height=np.zeros((n,n),np.float32)
 colors=np.array([[.295,.398,.042],[.245,.355,.025],[.15,.275,.031],[.105,.225,.045],[.36,.44,.052]],np.float32)
 for i in range(22000):
  cx=float(rng.uniform(0,n));cy=float(rng.uniform(0,n));angle=float(rng.uniform(0,np.pi*2))
  length=float(rng.uniform(2.7,7.0));width=float(rng.uniform(.38,.92));r=int(np.ceil(length*.6+width+1))
  xs=np.arange(int(cx)-r,int(cx)+r+1);ys=np.arange(int(cy)-r,int(cy)+r+1)
  dx=xs[None,:]-cx;dy=ys[:,None]-cy;c=np.cos(angle);s=np.sin(angle)
  u=dx*c+dy*s;v=-dx*s+dy*c;t=u/length+.5
  shape=np.maximum(0,1-np.abs(v)/(width*(1-.70*np.clip(t,0,1))))
  shape*=np.maximum(0,1-(u/(length*.5))**4)
  mask=(t>=0)&(t<=1);alpha=(shape*mask*.75).astype(np.float32)
  ix=np.ix_(ys%n,xs%n);col=colors[int(rng.integers(0,len(colors)))]*float(rng.uniform(.93,1.06))
  rgb[ix]=rgb[ix]*(1-alpha[:,:,None])+col*alpha[:,:,None]
  height[ix]=np.maximum(height[ix],shape*mask*float(rng.uniform(.0007,.0023)))
 # UV repeat is 5.6 m across; normal strength stays subtle for centimeter-scale turf.
 dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*(n/5.6)*.5
 dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*(n/5.6)*.5
 normal=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
 return rgb,normal*.5+.5

def packed_png(name,rgb,is_color=True,folder=None):
 found=bpy.data.images.get(name)
 if found and found.get('lawn_revision')==VERSION:return found
 p=Path(folder) if folder else HERE/'textures';p.mkdir(exist_ok=True,parents=True)
 n=rgb.shape[0];arr=np.concatenate((linear_to_srgb(rgb) if is_color else rgb,np.ones((n,n,1),np.float32)),axis=-1).astype(np.float32)
 im=bpy.data.images.new(name,width=n,height=n,alpha=True,float_buffer=False)
 im.colorspace_settings.name='sRGB' if is_color else 'Non-Color';im.pixels.foreach_set(arr.ravel());im.update()
 path=p/(name+'.png');im.filepath_raw=str(path);im.file_format='PNG';im.save();bpy.data.images.remove(im)
 im=bpy.data.images.load(str(path),check_existing=False);im.name=name;im.colorspace_settings.name='sRGB' if is_color else 'Non-Color';im['lawn_revision']=VERSION;im['generator_seed']=418529;im.pack();return im

def apply_lawn_finish(texture_dir=None):
 mod=base_module();before=mod.geometry_hash();collision=mod.geometry_hash(True)
 original_images={im.name:mod.image_hash(im) for im in bpy.data.images if im.has_data and im.get('lawn_revision')!=VERSION}
 obj=bpy.data.objects.get('LAYOUT_Playable_Grass_Outline')
 if not obj:raise RuntimeError('Expected accepted layout playable lawn object')
 changes=[];mat=bpy.data.materials.get(NAME)
 if not mat:
  src=next((s.material for s in obj.material_slots if s.material and s.material.name=='V3_Tone_Warm_GrassBase_p1r5'),None)
  if not src:raise RuntimeError('Apply p1r5 base first; the lawn-only overlay expects its original lawn slot')
  mat=src.copy();mat.name=NAME;mat['palette_revision']=VERSION;mat['palette_baked']=True;mat['skip_reference_palette_tint']=True
  color,normal=turf_arrays();base=packed_png(NAME+'_BaseColor',color,True,texture_dir);norm=packed_png(NAME+'_Normal',normal,False,texture_dir)
  tx=mod.color_texture(mat);tx.image=base
  bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bsdf.inputs['Roughness'].default_value=.96
  nn=next(n for n in mat.node_tree.nodes if n.type=='NORMAL_MAP');nn.inputs['Strength'].default_value=.75
  normal_tx=next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.colorspace_settings.name=='Non-Color')
  normal_tx.image=norm;mat.diffuse_color=(*color.mean(axis=(0,1)).tolist(),1)
 for i,slot in enumerate(obj.material_slots):
  if slot.material and slot.material.name=='V3_Tone_Warm_GrassBase_p1r5':
   obj[KEY+str(i)]=slot.material.name;slot.material.use_fake_user=True;slot.material=mat;changes.append({'object':obj.name,'slot':i,'new':mat.name})
 after=mod.geometry_hash();col_after=mod.geometry_hash(True)
 mutated=[n for n,d in original_images.items() if mod.image_hash(bpy.data.images[n])!=d]
 assert before==after and collision==col_after and not mutated
 return {'version':VERSION,'base_revision':'material-palette-p1r5','changes':changes,'geometry_unchanged':before==after,
  'geometry_sha256':before,'collision_unchanged':collision==col_after,'original_images_unchanged':not mutated,
  'material':NAME,'target':'LAYOUT_Playable_Grass_Outline only','tile_resolution':[512,512],
  'uv_repeat_m':5.6,'seed':418529,'runtime':'Baked sRGB base color + linear tangent normal; skip legacy tint callbacks',
  'mean_linear_color':list(mat.diffuse_color[:3]),'base_color_encoding':'scene-linear to sRGB exactly once',
  'texture_memory_delta_bytes':512*512*4*2-256*256*4,
  'limits':'2D turf carpet supplements short blade geometry. Does not replace silhouette/coverage work.'}

def restore_lawn_finish():
 n=0
 for obj in bpy.data.objects:
  if obj.type!='MESH':continue
  for i,slot in enumerate(obj.material_slots):
   key=KEY+str(i)
   if key in obj:
    slot.material=bpy.data.materials[obj[key]];del obj[key];n+=1
 return n
