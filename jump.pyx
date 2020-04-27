import hashlib
import collections
import dummy_generator

Frame = collections.namedtuple('Frame',
        ('f_code', 'f_lasti', 'f_locals', 'stack_content', ))

jump_stack = []
jump_stack_idx = -1


def save_jump():
    cdef PyFrameObject *frame = PyEval_GetFrame()
    fake_stack = []
    while frame:
        stack_content = []
        for i in range(frame.f_stacktop - frame.f_localsplus):
            stack_content.append(<object>frame.f_localsplus[i])
        fake_stack.append(Frame(
            <object> frame.f_code,
            <object> frame.f_lasti,
            <object> frame.f_locals,
            stack_content,
            ))
        frame = frame.f_back
    return fake_stack


cdef PyObject* pyeval_fast_forward(PyFrameObject *frame, int exc):
    global jump_stack_idx
    frame_obj = <object> frame
    if frame_obj.f_code == jump_stack[jump_stack_idx].f_code:
        print 'jumping', frame_obj, 'to', jump_stack[-1].f_lasti

        # Fast forward the instruction pointer
        frame.f_lasti = jump_stack[jump_stack_idx].f_lasti
        frame.f_locals = <PyObject*>jump_stack[jump_stack_idx].f_locals
        for i, o in enumerate(jump_stack[jump_stack_idx].stack_content):
            frame.f_localsplus[i] = <PyObject*> o
        jump_stack_idx -= 1

    print 'evaluating', frame_obj
    return _PyEval_EvalFrameDefault(frame, exc)


def jump(func, fake_stack):
    global jump_stack_idx
    jump_stack.clear()
    jump_stack.extend(fake_stack)

    while func.__code__.co_code != jump_stack[-1].f_code.co_code:
        del jump_stack[-1]
    print 'The jump stack:', jump_stack
    jump_stack_idx = len(jump_stack) - 1

    cdef PyThreadState *state = PyThreadState_Get()
    state.interp.eval_frame = pyeval_fast_forward
    func()
    state.interp.eval_frame = _PyEval_EvalFrameDefault


funcall_log = {}
modules = []

def print_frame(frame):
    cdef PyFrameObject *f = <PyFrameObject *> frame

    if not frame:
        return 0

    indent = print_frame(frame.f_back)

    print ' ' * indent, frame.f_locals.get('func', '?'), f.f_lasti

    return indent + 1


cdef hash_code(f_code):
  h = hashlib.sha1(f_code.co_code)
  h.update(str(f_code.co_consts).encode("utf-8"))
  return h.digest()


cdef PyObject **current_stack_pointer():
    g = dummy_generator.generator()
    vs = next(g)
    print 'Generator valuestack', <unsigned long>((<PyGenObject*>g).gi_frame.f_valuestack)
    print 'Generator stacktop', <unsigned long>((<PyGenObject*>g).gi_frame.f_stacktop)

    return (<PyGenObject*>g).gi_frame.f_stacktop


cdef PyObject* pyeval_log_funcall_entry(PyFrameObject *frame, int exc):
  frame_obj = <object> frame
  cdef PyThreadState *state = PyThreadState_Get()

  # to ovoid the overhead of this call, log only if the function is in
  # the desired modules.
  if frame_obj.f_code.co_filename not in modules:
      state.interp.eval_frame = _PyEval_EvalFrameDefault
      r = _PyEval_EvalFrameDefault(frame, exc)
      state.interp.eval_frame = pyeval_log_funcall_entry
      return r

  print "---------Tracing-----"
  print frame_obj.f_code.co_filename, frame_obj.f_code.co_name

  cdef PyObject **stack_pointer = current_stack_pointer()
  num_objects_on_stack = stack_pointer - frame.f_valuestack
  print 'objects on stack:', <unsigned int>stack_pointer, <unsigned int>frame.f_valuestack, num_objects_on_stack

  # keep a fully qualified name for the function. and a sha1 of its code.
  # if we hold references to the frame object, we might cause a lot of
  # unexpected garbage to be kept around.
  funcall_log[(frame_obj.f_code.co_filename, frame_obj.f_code.co_name)] = (
          hash_code(frame_obj.f_code),
          num_objects_on_stack,
          )

  return _PyEval_EvalFrameDefault(frame, exc)


def trace_funcalls(module_fnames):
    cdef PyThreadState *state = PyThreadState_Get()
    modules.clear()
    modules.extend(module_fnames)
    state.interp.eval_frame = pyeval_log_funcall_entry


def stop_trace_funcalls():
    cdef PyThreadState *state = PyThreadState_Get()
    state.interp.eval_frame = _PyEval_EvalFrameDefault
