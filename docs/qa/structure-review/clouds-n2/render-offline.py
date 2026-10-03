"""Render only the authored atmosphere with actual generated GLES shaders.
This is an offline EGL software-driver preview, not a browser/full-map test.
"""
import contextlib
import ctypes as C
import io
import json
from pathlib import Path
import runpy
import sys

root=Path(__file__).resolve().parents[3]
sys.stdin=io.StringIO('[]')
with contextlib.redirect_stdout(io.StringIO()):
    compiler=runpy.run_path(str(Path(__file__).parent/'compile-egl-rgba8.py'))
gl=compiler['gl'];egl=compiler['egl'];display=compiler['display'];context=compiler['context'];config=compiler['config'];f=compiler['function']
fixture=json.loads((Path(__file__).parent/'fixture.json').read_text())
w,h=fixture['width'],fixture['height']
create_surface=f(egl,'eglCreatePbufferSurface',C.c_void_p,C.c_void_p,C.c_void_p,C.POINTER(C.c_int))
surface=create_surface(display,config,(C.c_int*5)(0x3057,w,0x3056,h,0x3038))
if not surface: raise RuntimeError('EGL pbuffer unavailable')
if not compiler['make_current'](display,surface,surface,context): raise RuntimeError('EGL pbuffer could not become current')
viewport=f(gl,'glViewport',None,C.c_int,C.c_int,C.c_int,C.c_int)
clearcolor=f(gl,'glClearColor',None,C.c_float,C.c_float,C.c_float,C.c_float)
clear=f(gl,'glClear',None,C.c_uint)
enable=f(gl,'glEnable',None,C.c_uint)
depthmask=f(gl,'glDepthMask',None,C.c_uint)
use=f(gl,'glUseProgram',None,C.c_uint)
genvao=f(gl,'glGenVertexArrays',None,C.c_int,C.POINTER(C.c_uint))
bindvao=f(gl,'glBindVertexArray',None,C.c_uint)
genbuffers=f(gl,'glGenBuffers',None,C.c_int,C.POINTER(C.c_uint))
bindbuffer=f(gl,'glBindBuffer',None,C.c_uint,C.c_uint)
bufferdata=f(gl,'glBufferData',None,C.c_uint,C.c_size_t,C.c_void_p,C.c_uint)
attriblocation=f(gl,'glGetAttribLocation',C.c_int,C.c_uint,C.c_char_p)
attribpointer=f(gl,'glVertexAttribPointer',None,C.c_uint,C.c_int,C.c_uint,C.c_uint,C.c_int,C.c_void_p)
enableattrib=f(gl,'glEnableVertexAttribArray',None,C.c_uint)
uniformlocation=f(gl,'glGetUniformLocation',C.c_int,C.c_uint,C.c_char_p)
uniformmatrix4=f(gl,'glUniformMatrix4fv',None,C.c_int,C.c_int,C.c_uint,C.POINTER(C.c_float))
uniformmatrix3=f(gl,'glUniformMatrix3fv',None,C.c_int,C.c_int,C.c_uint,C.POINTER(C.c_float))
uniform3=f(gl,'glUniform3fv',None,C.c_int,C.c_int,C.POINTER(C.c_float))
drawarrays=f(gl,'glDrawArrays',None,C.c_uint,C.c_int,C.c_int)
drawelements=f(gl,'glDrawElements',None,C.c_uint,C.c_int,C.c_uint,C.c_void_p)
readpixels=f(gl,'glReadPixels',None,C.c_int,C.c_int,C.c_int,C.c_int,C.c_uint,C.c_uint,C.c_void_p)
geterror=f(gl,'glGetError',C.c_uint)

def floats(values): return (C.c_float*len(values))(*values)
programs=[]
for source in fixture['programs']:
    program=compiler['create_program']()
    for stage,enum in [('vertex',0x8b31),('fragment',0x8b30)]:
        shader=compiler['create_shader'](enum);text=C.c_char_p(source[stage].encode());compiler['shader_source'](shader,1,C.byref(text),None);compiler['compile_shader'](shader);compiler['attach_shader'](program,shader)
    compiler['link_program'](program)
    linked=C.c_int();compiler['get_program_iv'](program,0x8b82,C.byref(linked))
    if not linked.value: raise RuntimeError('shader link failed')
    programs.append(program)
viewport(0,0,w,h);clearcolor(.4,.6,.8,1);clear(0x4000|0x0100);enable(0x0b71)
for mesh in fixture['meshes']:
    program=programs[mesh['program']];use(program);depthmask(0 if mesh['program']==0 else 1)
    for name,values in [('projectionMatrix',fixture['projection']),('viewMatrix',fixture['view']),('modelMatrix',mesh['model']),('modelViewMatrix',mesh['modelView'])]:uniformmatrix4(uniformlocation(program,name.encode()),1,0,floats(values))
    uniformmatrix3(uniformlocation(program,b'normalMatrix'),1,0,floats(mesh['normal']))
    for name,values in fixture['programs'][mesh['program']]['uniforms'].items():uniform3(uniformlocation(program,name.encode()),1,floats(values))
    vao=C.c_uint();genvao(1,C.byref(vao));bindvao(vao)
    geometry=fixture['geometries'][mesh['geometry']]
    for name in ['position','normal']:
        location=attriblocation(program,name.encode())
        if location<0: continue
        buffer=C.c_uint();genbuffers(1,C.byref(buffer));bindbuffer(0x8892,buffer);values=floats(geometry[name]);bufferdata(0x8892,C.sizeof(values),values,0x88e4);enableattrib(location);attribpointer(location,3,0x1406,0,0,None)
    if geometry['index']:
        buffer=C.c_uint();genbuffers(1,C.byref(buffer));bindbuffer(0x8893,buffer);values=(C.c_uint*len(geometry['index']))(*geometry['index']);bufferdata(0x8893,C.sizeof(values),values,0x88e4);drawelements(0x0004,len(values),0x1405,None)
    else: drawarrays(0x0004,0,len(geometry['position'])//3)
pixels=(C.c_ubyte*(w*h*4))();readpixels(0,0,w,h,0x1908,0x1401,pixels)
if geterror():raise RuntimeError('GL render error')
from PIL import Image
image=Image.frombytes('RGBA',(w,h),bytes(pixels)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
image.save(Path(__file__).parent/'atmosphere-offline-rgba8.png')
print(json.dumps({'preview':'atmosphere-offline-rgba8.png','driver':compiler['get_string'](0x1f02).decode(),'scope':'atmosphere-only EGL preview; no browser/full-map render'}))
