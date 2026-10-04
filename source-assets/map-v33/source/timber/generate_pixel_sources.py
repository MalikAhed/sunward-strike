"""Original medium-scale honey timber paint; no reference pixels are read."""
from pathlib import Path
import numpy as np
from PIL import Image
import json,hashlib
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--output-directory',required=True);args=parser.parse_args()
P=Path(args.output_directory).resolve();P.mkdir(parents=True,exist_ok=False);T=P/'textures';T.mkdir()
N=1024;y,x=np.mgrid[0:N,0:N];u=(x+.5)/N;v=(y+.5)/N;tau=2*np.pi
phase=u+.006*np.sin(tau*v)+.003*np.sin(tau*v*2)+.001*np.sin(tau*v*5)
primary=np.sin(tau*phase*29)
secondary=np.sin(tau*(phase*53+.10*np.sin(tau*v*3)))
late=np.maximum(primary,0)**6
broad=np.sin(tau*(u*7+.04*np.sin(tau*v)))
envelope=.60+.40*(.5+.5*np.sin(tau*(v*2+u*4)))
variation=.085*broad+(.110*primary-.090*late)*envelope+.035*secondary+.035*np.sin(tau*(v+u*3))
warm=.0060*np.sin(tau*(u*13+.12*np.sin(tau*v*2)))
target=np.array([.68,.36,.105])
rgb=target[None,None,:]*(1+variation[:,:,None])+warm[:,:,None]*np.array([1,.30,-.40])
rgb*=target/rgb.mean((0,1))
linear_to_srgb=lambda a:np.where(a<=.0031308,12.92*a,1.055*np.maximum(a,0)**(1/2.4)-.055)
srgb_to_linear=lambda a:np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
height=.00015*np.sin(tau*phase*17)-.0006*late
dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*2.6/N)
dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*2.6/N)
normal=np.stack([-dx,dy,np.ones_like(dx)],-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
rows=[]
for name,arr,role in [('Honey_Fibers_p5r3',linear_to_srgb(np.clip(rgb,0,.985)),'baseColor'),('Honey_Fibers_Normal_p5r3',normal*.5+.5,'normal')]:
 im=Image.fromarray(np.round(np.clip(arr,0,1)*255).astype(np.uint8),'RGB').resize((256,256),Image.Resampling.LANCZOS)
 f=T/(name+'.png');im.save(f,optimize=True)
 if role=='normal':
  # The original analytic normal formula must reproduce exact r1 bytes.
  assert hashlib.sha256(f.read_bytes()).hexdigest()=='6fad0c4f6dbdee36d66619e09d3dff1ddf3d8ad7f53e3f48ae8e8a7a3145d495'
 r={'name':name,'file':f.name,'role':role,'size':[256,256],'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'decoded_rgba_bytes':262144}
 if role=='baseColor':
  a=srgb_to_linear(np.asarray(im,dtype=float)/255);r['mean_linear_rgb']=a.mean((0,1)).tolist();r['mean_max_error']=float(np.max(np.abs(a.mean((0,1))-target)));r['luminance_relative_std']=float(np.std(a@np.array([.2126,.7152,.0722]))/np.mean(a@np.array([.2126,.7152,.0722])));assert r['mean_max_error']<.0006
 if role=='baseColor':assert r['sha256']=='8f3da98c9f1ec8b77f189e2e030a996a9aec6a73eb94fcf7dfea782acac123ce'
 rows.append(r)
m={'revision':'timber-finish-p5r3','source':'Original analytic directional paint; no supplied reference image pixels','target_linear_mean':target.tolist(),'image_count':2,'decoded_rgba_bytes':524288,'normal_strength_preserved':.30,'color_vector_scale':[3,1],'images':rows}
(P/'texture-manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps(m,indent=2))
