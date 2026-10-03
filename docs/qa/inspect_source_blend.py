import bpy,json
from pathlib import Path
s=bpy.context.scene
r={'filepath':bpy.data.filepath,'scene_extras':dict(s.items()),'mesh_objects':sum(o.type=='MESH' for o in bpy.data.objects),'packed_images':[{'name':i.name,'packed':bool(i.packed_file),'filepath':i.filepath} for i in bpy.data.images],'collision_collection_present':any(c.name.startswith('91_') for c in bpy.data.collections),'collision_collection_names':[c.name for c in bpy.data.collections if c.name.startswith('91_')],'playable_base_present':'PLAYABLE_Base_58x74m' in bpy.data.objects,'source_texts':list(bpy.data.texts.keys())}
Path('/workspace/shared/sunward-strike/docs/qa/map-editable-inspection.json').write_text(json.dumps(r,indent=2,default=str)+'\n')
print('EDITABLE_SOURCE',json.dumps(r,default=str))
