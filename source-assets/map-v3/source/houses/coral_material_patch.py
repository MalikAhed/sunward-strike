"""Reversible material-only patch, B-coral-m1. No geometry or global writes.
Clones source plaster materials and inserts glTF-recognized Mix(RGBA,MULTIPLY,
Factor1) between existing packed BaseColor texture and Principled Base Color.
Packed image pixels, UVs, normal-map bindings and geometry are untouched.
"""
import bpy
VERSION='B-coral-m1'
SPECS={
 'V2_Saffron_Plaster':('V3_B_Coral_Plaster',(.93,.29,.45,1)),
 'V2_Warm_Plaster':('V3_B_Cream_Plaster',(.98,.94,.82,1)),
}

def owned_clone(source_name,target_name,factor):
    old=bpy.data.materials.get(target_name)
    if old and old.get('palette_revision')==VERSION:return old
    src=bpy.data.materials[source_name];m=src.copy();m.name=target_name;m['palette_revision']=VERSION;m['source_material']=source_name;m['palette_authority']='User supplied art collage: warm cream lower plaster and coral red upper facade; classic images govern structure only'
    p=m.node_tree.nodes.get('Principled BSDF');links=list(p.inputs['Base Color'].links)
    if len(links)!=1:raise RuntimeError('Expected one source base-color texture link, found '+str(len(links)))
    source_socket=links[0].from_socket;m.node_tree.links.remove(links[0])
    mix=m.node_tree.nodes.new('ShaderNodeMix');mix.name='Owned Coral Palette Multiply';mix.label='glTF BaseColor factor, packed texture preserved';mix.data_type='RGBA';mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1.0;mix.inputs[7].default_value=factor
    m.node_tree.links.new(source_socket,mix.inputs[6]);m.node_tree.links.new(mix.outputs[2],p.inputs['Base Color'])
    m.diffuse_color=tuple(src.diffuse_color[i]*factor[i] for i in range(4));return m

def apply_coral_material_patch(house_id='B_Saffron'):
    replacements={src:owned_clone(src,target,factor) for src,(target,factor) in SPECS.items()};changes=[]
    for o in bpy.data.objects:
        if o.type!='MESH' or o.get('house_id')!=house_id or o.name.startswith('COL_'):continue
        for slot in o.material_slots:
            if slot.material and slot.material.name in replacements:
                old=slot.material.name;slot.material=replacements[old];changes.append({'object':o.name,'old':old,'new':slot.material.name})
    return {'version':VERSION,'house_id':house_id,'changes':changes,'new_material_names':[q[0] for q in SPECS.values()],'shader_paint_layer_materials':['V3_B_Coral_Plaster','V3_B_Cream_Plaster'],'reversible_source_names':{target:src for src,(target,factor) in SPECS.items()},'gltf_factors':{target:list(factor) for src,(target,factor) in SPECS.items()},'preserved':['all geometry and object transforms','UVMap coordinates','packed base-color image data and variation','packed normal map, strength0.32','roughness0.88 and metallic0']}

def restore_source_materials(house_id='B_Saffron'):
    back={target:src for src,(target,factor) in SPECS.items()};count=0
    for o in bpy.data.objects:
        if o.type!='MESH' or o.get('house_id')!=house_id or o.name.startswith('COL_'):continue
        for slot in o.material_slots:
            if slot.material and slot.material.name in back:slot.material=bpy.data.materials[back[slot.material.name]];count+=1
    return count
