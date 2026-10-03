"""Package the editable asset, optimized exports, renders and local walkthrough."""
from pathlib import Path
import zipfile,hashlib,shutil,json
ROOT=Path(__file__).resolve().parent.parent
OUT=Path('/workspace/scratch/3432990968d3/sunward-delivery')
OUT.mkdir(parents=True,exist_ok=True)
files=[ROOT/'README.md',ROOT/'REFERENCES.md',ROOT/'Sunward_TestSite.blend',ROOT/'qa_report.json',ROOT/'qa_collision_report.json']
for folder in ['exports','renders','source','preview']:
 for p in sorted((ROOT/folder).rglob('*')):
  if not p.is_file() or any(x in p.parts for x in ['.godot','__pycache__']):continue
  if p.suffix in ['.log','.pyc','.import'] or p.name.endswith('.blend1'):continue
  if p.name=='package_delivery.py':continue
  files.append(p)
manifest='\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(ROOT)) for p in files)+'\n'
(ROOT/'SHA256SUMS.txt').write_text(manifest);files.append(ROOT/'SHA256SUMS.txt')
zip_path=OUT/'Sunward_Source_and_Walkthrough.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in files:z.write(p,'Sunward_TestSite/'+str(p.relative_to(ROOT)))
with zipfile.ZipFile(zip_path) as z:
 assert z.testzip() is None
for src,name in [(ROOT/'Sunward_TestSite.blend','Sunward_TestSite.blend'),(ROOT/'exports/Sunward_Environment.glb','Sunward_Environment.glb'),(ROOT/'exports/Sunward_Collision.glb','Sunward_Collision.glb'),(ROOT/'renders/01_hero.png','Sunward_Hero.png'),(ROOT/'renders/05_topdown.png','Sunward_Topdown.png')]:shutil.copy2(src,OUT/name)
print(json.dumps([{'name':p.name,'size_bytes':p.stat().st_size,'path':str(p)} for p in sorted(OUT.iterdir()) if p.is_file()],indent=2))
