"""Original procedural short-turf silhouettes. No supplied imagery is read."""
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
import random, math, json, hashlib

HERE = Path(__file__).resolve().parent
OUT = HERE / 'textures'
OUT.mkdir(exist_ok=True)
N, S = 128, 4

def srgb(a):
    return np.where(a <= .0031308, 12.92*a, 1.055*np.maximum(a, 0)**(1/2.4)-.055)

atlas = Image.new('RGBA', (512, 256))
for cell in range(8):
    rng = random.Random(6261003 + cell % 4)
    yy = np.linspace(1, 0, N*S, dtype=np.float32)[:, None, None]
    shade = [.94, 1.0][cell//4]
    base = np.array([.169, .278, .030], np.float32)*shade
    tip = np.array([.48, .61, .055], np.float32)*shade
    background = (base[None,None,:]*(1-yy)+tip[None,None,:]*yy)
    rgb = np.tile(background, (1, N*S, 1))
    alpha = np.zeros((N*S, N*S), np.float32)
    # Tall blades form an irregular narrow silhouette; the second row closes
    # the base rather than leaving several individual broad ornamental plants.
    blades = []
    for row, count in [(0, 9)]:
        for i in range(count):
            x = 64+rng.uniform(-.45,.45)
            target_x = 12+i*(104/(count-1))+rng.uniform(-1.7,1.7)
            h = 89+27*abs(target_x-64)/54+rng.uniform(-7,5)
            w = rng.uniform(9.5,14.5)
            lean = target_x-x
            root_y = rng.uniform(126,126.5)
            blades.append((x, root_y, h, w, lean, rng.uniform(.83, 1.12)))
    for x, root, h, w, lean, variance in blades:
        # Outward-splayed individual blades from a narrow common root. A
        # downward-pointing support triangle leaves room for unequal tips;
        # there is no shared upper apex or solid low-mip basal strip.
        left=[];right=[]
        for j in range(13):
            t=j/12;center_x=x+lean*(t**1.25)
            half_width=.48*w*math.sin(math.pi*t)*(1-.28*t)+.18*(1-t)
            y=root-h*t;left.append((center_x-half_width,y));right.append((center_x+half_width,y))
        points=left+list(reversed(right))
        mask = Image.new('L', (N*S, N*S), 0)
        ImageDraw.Draw(mask).polygon([(round(px*S),round(py*S)) for px,py in points], fill=255)
        a = np.asarray(mask).astype(np.float32)/255
        t = np.clip((root-np.arange(N*S)[:,None]/S)/h, 0, 1)[:,:,None]
        col = (base[None,None,:]*(1-t)+tip[None,None,:]*t)*variance
        # Restrained central facet gives depth without baked directional shadow.
        facet = 1 + .055*np.cos((np.arange(N*S)[None,:]/S-x)*.65)
        col = np.clip(col*facet[:,:,None],0,1)
        rgb = rgb*(1-a[:,:,None])+col*a[:,:,None]
        alpha = np.maximum(alpha,a)
    # Resize straight RGB and coverage separately. Premultiplied RGBA Lanczos
    # can overshoot to white in almost-transparent texels, contaminating mips.
    color = Image.fromarray(np.clip(srgb(rgb)*255,0,255).astype(np.uint8),'RGB').resize((N,N),Image.Resampling.LANCZOS)
    coverage = Image.fromarray((alpha*255).astype(np.uint8),'L').resize((N,N),Image.Resampling.LANCZOS)
    a = np.concatenate((np.asarray(color),np.asarray(coverage)[:,:,None]),axis=-1)
    a[:6,:,3]=0; a[:,:6,3]=0; a[:,-6:,3]=0
    # Extend appropriate green/yellow RGB through transparent texels. No white
    # matte can enter a mip or a bilinear alpha edge.
    for y in range(N):
        t = 1-y/(N-1)
        c = np.clip(srgb(base*(1-t)+tip*t)*255,0,255).astype(np.uint8)
        a[y,a[y,:,3]==0,:3] = c
    atlas.paste(Image.fromarray(a,'RGBA'),((cell%4)*N,(cell//4)*N))

path=OUT/'sunward_short_turf_r6i.png'
atlas.save(path)
raw=path.read_bytes()
manifest={'origin':'Original deterministic procedural curved grass blades; no supplied image pixels read or reused',
          'seed':6261003,'dimensions':[512,256],'cells':8,'blades_per_card':9,
          'gutter_px_sides_top':6,'alpha':'MASK cutoff 0.5; nonwhite matte RGB in transparent texels',
          'color_encoding':'authored scene-linear gradient converted once to sRGB',
          'base_decoded_rgba_bytes':512*256*4,'mip_chain_rgba_bytes_approx':699052,
          'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
(OUT/'sunward_short_turf_r6i_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
