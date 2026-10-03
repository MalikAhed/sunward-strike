from pathlib import Path
import json,zipfile,shutil
ROOT=Path(__file__).resolve().parent.parent.parent
OUT=Path('/workspace/scratch/3432990968d3/sunward-delivery-v2');OUT.mkdir(exist_ok=True)
corefiles=[ROOT/'Sunward_TestSite.blend',ROOT/'README.md',ROOT/'REFERENCES.md',ROOT/'qa_report.json',ROOT/'qa_collision_report.json',ROOT/'exports/resource_stats.json']
corefiles += [p for p in (ROOT/'source').glob('*.py') if p.name!='package_delivery.py']
corefiles += [ROOT/'refinement-v2'/n for n in ['add_architecture.py','add_foliage.py','add_foliage_dense.py']]
corefiles += [ROOT/'refinement-v2/source'/n for n in ['refine_art.py','polish_art.py','final_art_treatment.py','delivery_art.py','export_final.py','render_delivery.py','fix_ground_overlap.py']]
corefiles += [ROOT/'preview'/n for n in ['project.godot','main.gd','main.tscn','player.gd','README.md','refresh_assets.sh']]
info='SUNWARD v2.5\n\nThe Blender file opens on its own and contains all materials and textures.\nFor the local Godot walkthrough, extract Sunward_Walkthrough_Assets.zip into the same folder as this archive. It supplies Sunward_TestSite/preview/assets/*.glb.\nUse those GLBs directly for engine integration. They contain all texture images.\nGallery images are separate downloads so every ZIP stays under 5MB.\n'
core=OUT/'Sunward_Editable_Map_and_Walkthrough.zip'
with zipfile.ZipFile(core,'w',zipfile.ZIP_DEFLATED,9) as z:
 for p in corefiles:z.write(p,'Sunward_TestSite/'+str(p.relative_to(ROOT)))
 z.writestr('Sunward_TestSite/DOWNLOADS.txt',info)
with zipfile.ZipFile(OUT/'Sunward_Walkthrough_Assets.zip','w',zipfile.ZIP_DEFLATED,9) as z:
 for n in ['Sunward_Environment.glb','Sunward_Collision.glb']:z.write(ROOT/'exports'/n,'Sunward_TestSite/preview/assets/'+n)
shutil.copy2(core,OUT/'Sunward_Source_and_Walkthrough.zip')
for n in ['Sunward_TestSite.blend']:shutil.copy2(ROOT/n,OUT/n)
shutil.copy2(ROOT/'exports/Sunward_Environment.glb',OUT/'Sunward_Environment.glb')
# Called after final gallery completes; images are encoded to JPEG by Blender from its render result.
if all((ROOT/'renders'/f'{n}.jpg').exists() for n in ['01_hero','02_reverse','03_street','04_backyard','05_topdown','06_upper_sightline','07_ground_route','08_courtyard']):
 for name,keys in [('Sunward_Street_and_Backyard.zip',['03_street','04_backyard']),('Sunward_Reverse_View.zip',['02_reverse']),('Sunward_Upper_View.zip',['06_upper_sightline']),('Sunward_Interior_View.zip',['07_ground_route'])]:
  with zipfile.ZipFile(OUT/name,'w',zipfile.ZIP_DEFLATED,9) as z:
   for k in keys:z.write(ROOT/'renders'/f'{k}.jpg','Sunward_TestSite/renders/'+k+'.jpg')
 for src,name in [('01_hero.png','Sunward_Hero.png'),('05_topdown.png','Sunward_Topdown.png'),('08_courtyard.png','Sunward_Courtyard.png')]:shutil.copy2(ROOT/'renders'/src,OUT/name)
for p in OUT.glob('*.zip'):
 with zipfile.ZipFile(p) as z:assert z.testzip() is None
 assert p.stat().st_size<5_000_000,(p.name,p.stat().st_size)
print(json.dumps([{'name':p.name,'size_bytes':p.stat().st_size,'path':str(p)} for p in sorted(OUT.iterdir()) if p.is_file()],indent=2))
