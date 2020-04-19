def jump(frame):
    cdef PyFrameObject *current_frame = PyEval_GetFrame()
    current_frame.f_back = <PyFrameObject *>frame

def fixup_lasti(frame, last_is):
    cdef PyFrameObject *f = <PyFrameObject *> frame
    i = 0
    while f:
        f.f_lasti = last_is[i]
        f = f.f_back
        i += 1

def print_frame(frame):
    cdef PyFrameObject *f = <PyFrameObject *> frame

    if not frame:
        return 0

    indent = print_frame(frame.f_back)

    print ' ' * indent, frame.f_locals.get('func', '?'), f.f_lasti

    return indent + 1
