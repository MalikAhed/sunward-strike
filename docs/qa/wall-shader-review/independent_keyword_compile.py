import ctypes as c,json,os
os.environ.setdefault('EGL_PLATFORM','surfaceless')
egl=c.CDLL('libEGL.so.1');gl=c.CDLL('libGL.so.1')
egl.eglGetPlatformDisplay.argtypes=[c.c_uint,c.c_void_p,c.c_void_p];egl.eglGetPlatformDisplay.restype=c.c_void_p
egl.eglInitialize.argtypes=[c.c_void_p,c.POINTER(c.c_int),c.POINTER(c.c_int)];egl.eglInitialize.restype=c.c_uint
egl.eglBindAPI.argtypes=[c.c_uint];egl.eglBindAPI.restype=c.c_uint
egl.eglChooseConfig.argtypes=[c.c_void_p,c.POINTER(c.c_int),c.POINTER(c.c_void_p),c.c_int,c.POINTER(c.c_int)];egl.eglChooseConfig.restype=c.c_uint
egl.eglCreateContext.argtypes=[c.c_void_p,c.c_void_p,c.c_void_p,c.POINTER(c.c_int)];egl.eglCreateContext.restype=c.c_void_p
egl.eglMakeCurrent.argtypes=[c.c_void_p,c.c_void_p,c.c_void_p,c.c_void_p];egl.eglMakeCurrent.restype=c.c_uint
D=egl.eglGetPlatformDisplay(0x31DD,None,None); a=c.c_int();b=c.c_int();assert egl.eglInitialize(D,c.byref(a),c.byref(b))
assert egl.eglBindAPI(0x30A2)
attrs=(c.c_int*5)(0x3040,8,0x3033,1,0x3038);config=c.c_void_p();n=c.c_int();assert egl.eglChooseConfig(D,attrs,c.byref(config),1,c.byref(n)) and n.value
contextattrs=(c.c_int*5)(0x3098,3,0x30FB,3,0x3038);C=egl.eglCreateContext(D,config,None,contextattrs);assert C
assert egl.eglMakeCurrent(D,None,None,C)
gl.glGetString.argtypes=[c.c_uint];gl.glGetString.restype=c.c_char_p
gl.glCreateShader.argtypes=[c.c_uint];gl.glCreateShader.restype=c.c_uint
gl.glShaderSource.argtypes=[c.c_uint,c.c_int,c.POINTER(c.c_char_p),c.POINTER(c.c_int)]
gl.glCompileShader.argtypes=[c.c_uint]
gl.glGetShaderiv.argtypes=[c.c_uint,c.c_uint,c.POINTER(c.c_int)]
gl.glGetShaderInfoLog.argtypes=[c.c_uint,c.c_int,c.POINTER(c.c_int),c.c_char_p]
results={'context':{'EGL':f'{a.value}.{b.value}','GL':gl.glGetString(0x1F02).decode(),'GLSL':gl.glGetString(0x8B8C).decode(),'renderer':gl.glGetString(0x1F01).decode()},'cases':[]}
for name,identifier in [('original_reserved_identifier','patch'),('corrected_safe_identifier','artPaintVariation')]:
 source=f'#version 300 es\nprecision highp float;\nout vec4 outColor;\nvoid main(){{float {identifier}=.25;outColor=vec4({identifier});}}\n'
 shader=gl.glCreateShader(0x8B30); text=c.c_char_p(source.encode());gl.glShaderSource(shader,1,c.byref(text),None);gl.glCompileShader(shader)
 status=c.c_int();length=c.c_int();gl.glGetShaderiv(shader,0x8B81,c.byref(status));gl.glGetShaderiv(shader,0x8B84,c.byref(length));buf=c.create_string_buffer(max(1,length.value));gl.glGetShaderInfoLog(shader,len(buf),None,buf)
 results['cases'].append({'name':name,'GLSL':'300 es','success':bool(status.value),'diagnostic':buf.value.decode(),'source':source})
print(json.dumps(results,indent=2))
assert results['cases'][0]['success'] is False and results['cases'][1]['success'] is True
