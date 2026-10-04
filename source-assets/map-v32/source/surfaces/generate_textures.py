"""Original compact analytic painted surfaces. No reference pixels are read."""
import numpy as np
from PIL import Image
from pathlib import Path
import json,hashlib

HERE=Path(__file__).resolve().parent
OUT=HERE/'textures';OUT.mkdir(exist_ok=True)
N=512
y,x=np.mgrid[0:N,0:N];u=(x+.5)/N;v=(y+.5)/N
TAU=2*np.pi
manifest=[]

def linear_to_srgb(a):return np.where(a<=.0031308,12.92*a,1.055*np.maximum(a,0)**(1/2.4)-.055)
def srgb_to_linear(a):return np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
def save(name,a,role,target=None):
 # Supersampling is only antialiasing of original analytic paint, not source-image editing.
 rgb=np.round(np.clip(a,0,1)*255).astype(np.uint8)
 size=(256,256) if name.startswith(('Honey_','Grain_')) else (128,128)
 im=Image.fromarray(rgb,'RGB').resize(size,Image.Resampling.LANCZOS)
 path=OUT/(name+'.png');im.save(path,optimize=True)
 row={'file':path.name,'name':name,'role':role,'size':list(im.size),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'decoded_rgba_bytes':im.width*im.height*4}
 if target is not None:
  decoded=srgb_to_linear(np.asarray(im,dtype=float)/255)
  row.update(target_linear_rgb=list(target),mean_decoded_linear_rgb=decoded.mean((0,1)).tolist(),mean_max_error=float(np.max(np.abs(decoded.mean((0,1))-target))))
  assert row['mean_max_error']<.004
 manifest.append(row)

def color(name,base,variation,hue=None):
 rgb=np.asarray(base)[None,None,:]*(1+variation[:,:,None])
 if hue is not None:rgb+=hue
 rgb*=np.asarray(base)/rgb.mean((0,1))
 save(name,linear_to_srgb(np.clip(rgb,0,.985)),'baseColor',base)

def normal(name,height):
 # Physical-height derivative in a 2.6m periodic tile. Applied strength remains <=.45.
 dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*2.6/N)
 dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*2.6/N)
 # PNG rows run downward, Blender V upward.
 xyz=np.stack([-dx,dy,np.ones_like(dx)],-1);xyz/=np.linalg.norm(xyz,axis=-1,keepdims=True)
 save(name,xyz*.5+.5,'normal')

def siding(vertical=False):
 across=u if vertical else v
 along=v if vertical else u
 phase=across*10
 board=np.floor(phase);t=phase-board
 edge=np.minimum(t,1-t)
 groove=np.exp(-(edge/.070)**2)
 # Quiet broad individual-board variation, with brush-scale waves along each plank.
 boardtone=.038*np.sin(TAU*board/10+.41)+.020*np.sin(TAU*board*3/10+2.1)
 brush=.012*np.sin(TAU*(along*2+.10*np.sin(TAU*across)))+.007*np.sin(TAU*(along*5+across))
 fine=.003*np.sin(TAU*(across*70+.13*np.sin(TAU*along*3)))
 variation=boardtone+brush+fine-.105*groove
 height=.0018*(1-groove)+.0004*np.sin(np.pi*t)**2+.00010*np.sin(TAU*(across*50+.1*np.sin(TAU*along*2)))
 return variation,height

h,hheight=siding(False);vertical,vheight=siding(True)
color('Turquoise_Siding_H',(.065,.56,.42),h)
color('SunnyYellow_Siding_V',(.86,.67,.12),vertical)
normal('Siding_H_Normal',hheight);normal('Siding_V_Normal',vheight)

def roof(horizontal):
 # Horizontal courses progress along V; rotate analytically for roofs sloping in local X.
 a,b=(u,v) if horizontal else (v,u)
 row=np.floor(b*10);t=b*10-row
 cell=a*6+(row%2)*.5;col=np.floor(cell);f=cell-col
 rowgap=np.exp(-(np.minimum(t,1-t)/.062)**2)
 colgap=np.exp(-(np.minimum(f,1-f)/.045)**2)
 joints=np.maximum(rowgap,colgap*.64)
 piece=.047*np.sin(TAU*(col/6+row*.3))+.028*np.cos(TAU*(col*.5+row*.1))
 broad=.014*np.sin(TAU*(a*3+b*2))+.007*np.cos(TAU*(a*7-b*3))
 variation=piece+broad-.18*joints
 height=.0027*(1-rowgap)+.0005*(1-colgap)+.00020*np.cos(TAU*(a*4+b*2))
 return variation,height

for direction,horizontal in [('V',False)]:
 z,ht=roof(horizontal);color('Lavender_Shingle_'+direction,(.16,.18,.30),z);normal('Shingle_'+direction+'_Normal',ht)

def timber(vertical):
 across,along=(u,v) if vertical else (v,u)
 # Long flowing quiet grain. No knotholes, nail marks, dirt or strongly directed lighting.
 warp=.032*np.sin(TAU*along)+.014*np.sin(TAU*(along*2+across))
 phase=across+warp
 grain=.012*np.sin(TAU*(phase*61))+.006*np.sin(TAU*(phase*109+along))
 broad=.035*np.sin(TAU*(across*5+.12*np.sin(TAU*along)))+.016*np.sin(TAU*(across*17+along))
 ht=.00018*np.sin(TAU*phase*61)+.00008*np.sin(TAU*(phase*109+along))
 return broad+grain,ht

for direction,vertical in [('V',True)]:
 z,ht=timber(vertical);color('Honey_Grain_'+direction,(.68,.36,.105),z);normal('Grain_'+direction+'_Normal',ht)

(HERE/'texture-manifest.json').write_text(json.dumps({'version':'surface-detail-p2r2','source':'Original analytic artwork; no input image pixels','tile_meters':2.6,'images':manifest,'decoded_rgba_bytes':sum(r['decoded_rgba_bytes'] for r in manifest),'png_bytes':sum(r['bytes'] for r in manifest)},indent=2))
print('TEXTURES_READY',len(manifest),sum(r['bytes'] for r in manifest))
