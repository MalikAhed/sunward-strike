import bpy,os,json
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));PROJECT=os.path.dirname(ROOT);s=bpy.context.scene
base=bpy.data.objects.get('PLAYABLE_Base_58x74m')
if base:bpy.data.objects.remove(base,do_unlink=True)
s['build_version']='2.5';s['ground_overlap_fixed']='Redundant coplanar visual base removed. Static collision unchanged; world ground supplies the same visible level.'
# Reuse the validated grouped export path; this never exports the separate hidden collider.
code=open(ROOT+'/source/export_final.py').read().split('# Preserve editable objects; evaluated export copies are grouped spatially by collection/material.\n',1)[1]
code=code.replace("'build_version':'2.4'","'build_version':'2.5'")
exec(compile(code,'export_without_ground_overlap','exec'))
bpy.ops.wm.save_as_mainfile(filepath=PROJECT+'/Sunward_TestSite.blend',compress=True)
print('GROUND_OVERLAP_FIXED',flush=True)
