"""Compile/link GLSL ES 3.00 using an installed driver, without a browser.

A missing Python/EGL/OpenGL implementation is an explicit skipped test (77).
Shader compilation/link errors are failures (1), never skips. No packages are
installed and no network, server, window, or browser is used.
"""
import ctypes as C
import ctypes.util
import json
import os
import sys

os.environ.setdefault('MESA_SHADER_CACHE_DISABLE', 'true')


def function(library, name, restype, *argtypes):
    func = getattr(library, name)
    func.restype = restype
    func.argtypes = list(argtypes)
    return func


try:
    egl_name = ctypes.util.find_library('EGL')
    gl_name = ctypes.util.find_library('GL')
    if not egl_name or not gl_name:
        raise RuntimeError('installed EGL/OpenGL libraries unavailable')
    egl = C.CDLL(egl_name)
    gl = C.CDLL(gl_name)
    get_proc = function(egl, 'eglGetProcAddress', C.c_void_p, C.c_char_p)
    display_address = get_proc(b'eglGetPlatformDisplayEXT')
    if not display_address:
        raise RuntimeError('surfaceless EGL platform unavailable')
    get_display = C.CFUNCTYPE(C.c_void_p, C.c_uint, C.c_void_p, C.POINTER(C.c_int))(display_address)
    display = get_display(0x31dd, None, None)  # EGL_PLATFORM_SURFACELESS_MESA
    initialize = function(egl, 'eglInitialize', C.c_uint, C.c_void_p, C.POINTER(C.c_int), C.POINTER(C.c_int))
    major, minor = C.c_int(), C.c_int()
    if not initialize(display, C.byref(major), C.byref(minor)):
        raise RuntimeError('surfaceless EGL initialization unavailable')
    bind_api = function(egl, 'eglBindAPI', C.c_uint, C.c_uint)
    if not bind_api(0x30a0):  # EGL_OPENGL_ES_API
        raise RuntimeError('OpenGL ES API unavailable')
    choose = function(egl, 'eglChooseConfig', C.c_uint, C.c_void_p, C.POINTER(C.c_int), C.POINTER(C.c_void_p), C.c_int, C.POINTER(C.c_int))
    attributes = (C.c_int * 13)(0x3033, 0x0001, 0x3040, 0x0040, 0x3024, 8, 0x3023, 8, 0x3022, 8, 0x3021, 8, 0x3038)  # PBUFFER, ES3, RGBA8
    config, count = C.c_void_p(), C.c_int()
    if not choose(display, attributes, C.byref(config), 1, C.byref(count)) or not count.value:
        raise RuntimeError('OpenGL ES 3 configuration unavailable')
    create_context = function(egl, 'eglCreateContext', C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p, C.POINTER(C.c_int))
    context = create_context(display, config, None, (C.c_int * 3)(0x3098, 3, 0x3038))
    if not context:
        raise RuntimeError('OpenGL ES 3 context unavailable')
    make_current = function(egl, 'eglMakeCurrent', C.c_uint, C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p)
    if not make_current(display, None, None, context):
        raise RuntimeError('surfaceless OpenGL ES context unavailable')
except (OSError, AttributeError, RuntimeError) as error:
    print(json.dumps({'unavailable': str(error)}))
    sys.exit(77)

get_string = function(gl, 'glGetString', C.c_char_p, C.c_uint)
create_shader = function(gl, 'glCreateShader', C.c_uint, C.c_uint)
shader_source = function(gl, 'glShaderSource', None, C.c_uint, C.c_int, C.POINTER(C.c_char_p), C.POINTER(C.c_int))
compile_shader = function(gl, 'glCompileShader', None, C.c_uint)
get_shader_iv = function(gl, 'glGetShaderiv', None, C.c_uint, C.c_uint, C.POINTER(C.c_int))
get_shader_log = function(gl, 'glGetShaderInfoLog', None, C.c_uint, C.c_int, C.POINTER(C.c_int), C.c_char_p)
create_program = function(gl, 'glCreateProgram', C.c_uint)
attach_shader = function(gl, 'glAttachShader', None, C.c_uint, C.c_uint)
link_program = function(gl, 'glLinkProgram', None, C.c_uint)
get_program_iv = function(gl, 'glGetProgramiv', None, C.c_uint, C.c_uint, C.POINTER(C.c_int))
get_program_log = function(gl, 'glGetProgramInfoLog', None, C.c_uint, C.c_int, C.POINTER(C.c_int), C.c_char_p)
delete_shader = function(gl, 'glDeleteShader', None, C.c_uint)
delete_program = function(gl, 'glDeleteProgram', None, C.c_uint)
results = []
for item in json.load(sys.stdin):
    compiled = []
    errors = []
    for stage, shader_type in [('vertex', 0x8b31), ('fragment', 0x8b30)]:
        shader = create_shader(shader_type)
        compiled.append(shader)
        source = C.c_char_p(item[stage].encode('utf8'))
        shader_source(shader, 1, C.byref(source), None)
        compile_shader(shader)
        status, length = C.c_int(), C.c_int()
        get_shader_iv(shader, 0x8b81, C.byref(status))
        get_shader_iv(shader, 0x8b84, C.byref(length))
        log = C.create_string_buffer(max(1, length.value))
        get_shader_log(shader, len(log), None, log)
        if not status.value:
            errors.append({'stage': stage, 'log': log.value.decode()})
    linked = False
    if not errors:
        program = create_program()
        for shader in compiled:
            attach_shader(program, shader)
        link_program(program)
        status, length = C.c_int(), C.c_int()
        get_program_iv(program, 0x8b82, C.byref(status))
        get_program_iv(program, 0x8b84, C.byref(length))
        log = C.create_string_buffer(max(1, length.value))
        get_program_log(program, len(log), None, log)
        linked = bool(status.value)
        if not linked:
            errors.append({'stage': 'link', 'log': log.value.decode()})
        delete_program(program)
    for shader in compiled:
        delete_shader(shader)
    results.append({'name': item['name'], 'compiled': not errors, 'linked': linked, 'errors': errors})
print(json.dumps({'driver': get_string(0x1f02).decode(), 'glsl': get_string(0x8b8c).decode(), 'results': results}))
# The caller checks individual outcomes, including deliberate negative fixtures.
