"""Independent static delivery checks. Run after `npm run build`.
No browser behavior or performance is inferred by this script.
"""
from pathlib import Path
import hashlib,json,re,sys
from inspect_glb import report
ROOT=Path(__file__).resolve().parents[2]
EXPECTED={
 'sunward-v2.5.glb':'5c55f997e74eb39d3a32a842ac417d04b37c905f982f60bdc8ab814ca10aec42',
 'carbine-revision2.glb':'13f9c861adb51e8e18556a47fe60ca33d16ae65f593b979f4e3a8c1a7ac210ce',
 'sunward-collision.glb':'378d5121d97faf7ca5af615c13c0104742c59cffe77e247c32ede25fdece83ce',
}
results=[]
def check(name,condition,detail=''):
 results.append({'check':name,'pass':bool(condition),'detail':detail})
 print(('PASS ' if condition else 'FAIL ')+name+(': '+detail if detail else ''))
for filename,expected in EXPECTED.items():
 p=ROOT/'public/assets'/filename
 check('source copy exists '+filename,p.is_file())
 if not p.is_file():continue
 sha=hashlib.sha256(p.read_bytes()).hexdigest()
 check('exact source SHA-256 '+filename,sha==expected,sha)
 r=report(p)
 check('self-contained GLB '+filename,not r['external_uris'],str(r['external_uris']))
 if filename=='sunward-v2.5.glb':
  check('map build version',r['build_version']=='2.5',str(r['build_version']))
  check('map triangles',r['triangles']==207294,str(r['triangles']))
  check('map material/texture retention',r['materials']==57 and r['images']==11,f"{r['materials']} materials / {r['images']} images")
 elif filename=='carbine-revision2.glb':
  check('rifle clips intact',set(r['animations'])=={'Fire','Reload','Charge','Inspect'},str(r['animations']))
  check('rifle triangles/materials',r['triangles']==25225 and r['materials']==10,f"{r['triangles']} / {r['materials']}")
# Mathematically verify the integration rotation recommended by the reviewer.
import numpy as np,math
angle=-math.pi/2
rot=np.array([[math.cos(angle),0,math.sin(angle)],[0,1,0],[-math.sin(angle),0,math.cos(angle)]])
check('rifle wrapper suggested -Y rotation maps -X to -Z',np.allclose(rot@[-1,0,0],[0,0,-1]))
index=ROOT/'dist/index.html'
check('production index exists',index.is_file())
if index.is_file():
 html=index.read_text();urls=re.findall(r'(?:src|href)=["\']([^"\']+)',html)
 local=[u for u in urls if not re.match(r'(?:https?:|data:|#|mailto:)',u)]
 check('HTML avoids root-relative URLs',all(not u.startswith('/') for u in local),str(local))
 check('HTML local references exist',all((ROOT/'dist'/u.split('?')[0]).exists() for u in local),str(local))
 check('production entry lacks localhost',not re.search(r'(?:localhost|127\.0\.0\.1|/src/)',html))
 for filename,expected in EXPECTED.items():
  p=ROOT/'dist/assets'/filename
  check('production asset exists '+filename,p.is_file())
  if p.is_file():check('production asset hash '+filename,hashlib.sha256(p.read_bytes()).hexdigest()==expected)
 js=list((ROOT/'dist/assets').glob('*.js'))
 code='\n'.join(p.read_text() for p in js)
 check('production JS exists',bool(js))
 check('production JS lacks localhost runtime origin',not re.search(r'(?:https?://(?:localhost|127\.0\.0\.1))',code))
 check('production JS avoids absolute GLB paths',not re.search(r'["\']/assets/[^"\']+\.glb',code))
# Source path hygiene excludes a deliberately referenced documentation URL.
source_files=[p for p in (ROOT/'src').rglob('*') if p.is_file()]
app='\n'.join(p.read_text() for p in source_files)
check('application source exists',bool(source_files))
check('application assets avoid root-relative GLB URLs',not re.search(r'["\']/assets/[^"\']+\.glb',app))
check('application has no runtime CDN import',not re.search(r'import.*["\']https?://',app))
out={'method':'Static source/production/GLB checks only; browser runtime remains separate','results':results,'passed':all(r['pass'] for r in results)}
(ROOT/'docs/qa/static-results.json').write_text(json.dumps(out,indent=2)+'\n')
sys.exit(0 if out['passed'] else 1)
