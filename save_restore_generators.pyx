from jump cimport *


def save_generator_state(gen):
    cdef PyFrameObject *frame = <PyFrameObject *>gen.gi_frame

    stack_size = frame.f_stacktop - frame.f_localsplus
    stack_content = [
            <object>frame.f_localsplus[i] if frame.f_localsplus[i] else None
            for i in range(stack_size)
        ]
    return (frame.f_lasti, stack_content)


def restore_generator(gen, saved_frame):
    cdef PyFrameObject *frame = <PyFrameObject *>gen.gi_frame
    saved_f_lasti, saved_stack_content = saved_frame

    frame.f_lasti = saved_f_lasti

    cdef int i = 0
    for o in saved_stack_content:
        # TODO: Make sure this is necessary and that i'm not leaking a reference here.
        Py_INCREF(o)
        frame.f_localsplus[i] = <PyObject*> o
        i += 1

    frame.f_stacktop = frame.f_localsplus + i
    assert frame.f_stacktop - frame.f_localsplus == len(saved_stack_content)

    return gen
