from typing import Generator, List, Tuple
import dis
import logging

from function_checkpointing.jump cimport *

SavedStackFrame = Tuple[int, List, bytes]

class NULLObject(object):
    pass

log = logging.getLogger(__name__)


cdef object snapshot_frame(PyFrameObject *frame, int child_frame_arg_count):
    log.debug('Saving frame %s(co_argcount=%d) last_i=%d',
        <object>frame.f_code.co_name,
        <object>frame.f_code.co_argcount,
        <object>frame.f_lasti)

    if frame.f_code.co_kwonlyargcount:
        raise NotImplementedError("Can't yet handle functions with kw arguments "
                "in the call chain. Frame: " + str(<object>frame))

    # Take a guess at the stack size.

    # Add the local variables and the number of arguments we had to pass
    # to our child frame.
    stack_size = frame.f_valuestack - frame.f_localsplus + child_frame_arg_count

    # Disassemble the currently call instruction. Add the number of arguments
    # it needed to have on the stack. To do this, disassemble the frame's code
    # object and jump to the index of the last instruction execute. This is a
    # CALL instruction of some kind (CALL_FUNCTION, CALL_METHOD, etc) because
    # this frame was captured in the middle of a call to save_frame().
    bytecode = dis.Bytecode(<object> frame.f_code, current_offset=frame.f_lasti)
    instructions = iter(bytecode)
    for _ in range(frame.f_lasti // 2):  # Fast forward to f_lasti.
        next(instructions)
    call_instr = next(instructions)

    # The arguments to the CALL_FUNCTION instruction or whatever instruction
    # caused the method call.
    if call_instr.opname == 'CALL_FUNCTION':
        # +1 for the address of the function being called
        stack_size += 1
    elif call_instr.opname == 'CALL_METHOD':
        # +1 for the address of the method, +1 for the object
        stack_size += 2
    elif call_instr.opname == 'CALL_FUNCTION_KW':
        # +1 for the address of the function, +1 for the tuple containing
        # the names of variables
        stack_size += 2
    elif call_instr.opname:
        raise NotImplementedError("Don't know how to checkpoint around opcode"
                f" {call_instr.opname}. Here is the function:\n"
                + bytecode.dis())

    # Save a copy of the stack using the above guess. Convent NULL pointers to
    # objects to a Python object sentinel value.
    stack_content = [
            <object>frame.f_localsplus[i] if frame.f_localsplus[i] else NULLObject
            for i in range(stack_size)
        ]

    saved_frame = (
            <object> frame.f_lasti,
            stack_content,
            <object> frame.f_code.co_code
            )

    return saved_frame


def save_jump() -> List[SavedStackFrame]:
    """Snapshot of the stack frame leading to this call.

    The ephemeral state of the stack frames between the caller and the topmost
    stack frame are copied to a list and returned. The list can be saved as a
    global, pickled, unpickled, etc. You can restore the call stack by calling
    jump() on the returned object.

    When this function returns, it can return two things:
       1. The saved state of the stack so that you can jump back to this point
       2. The empty list if you've jumped back to this point.
    """
    saved_stack: List[SavedStackFrame] = []

    if PyThreadState_Get().interp.eval_frame == pyeval_fast_forward:
        PyThreadState_Get().interp.eval_frame = _PyEval_EvalFrameDefault
        log.debug('save_jump In the middle of a resume. Not saving.')
        return []

    cdef PyFrameObject *frame = PyEval_GetFrame()
    cdef int child_frame_arg_count = 0  # initially, the argcount of save_jump()
    while frame.f_back:
        saved_stack.append(snapshot_frame(frame, child_frame_arg_count))
        child_frame_arg_count = frame.f_code.co_argcount
        frame = frame.f_back

    return saved_stack


cdef PyObject *restore_frame(PyFrameObject *frame, saved_frame: SavedStackFrame):
    """Restore the ephemeral state of a frame from the saved state.

    Copies the frame's instruction pointer and stack content from saved_frame
    to the frame object.
    """
    frame_obj = <object> frame
    saved_f_lasti, saved_stack_content, saved_code = saved_frame

    log.debug('Restoring frame %s', frame_obj)

    if frame_obj.f_code.co_code != saved_code:
        raise RuntimeError('Trying to restore frame from wrong snapshot:'
                f'\n   called_on.f_code.co_code: {frame_obj.f_code.co_code}'
                f'\n   saved_code: {saved_code}')

    # Fast forward the instruction pointer. f_lasti points to a CALL
    # instruction (a CALL_METHOD or CALL_FUNCTION or similar). The frame
    # evaluator starts executing at f_lasti+2, but in this case, we want it to
    # re-execute the call instruction to force it to recurse on itself. So
    # preemptively decrement f_lasti by 2.
    frame.f_lasti = saved_f_lasti - 2

    # Restore the content of the stack.
    cdef int i = 0
    for o in saved_stack_content:
        if o == NULLObject:
            # Translate the sentinel value back to NULL.
            frame.f_localsplus[i] = NULL
        else:
            frame.f_localsplus[i] = <PyObject*> o
            Py_INCREF(o)
        i += 1

    frame.f_stacktop = frame.f_localsplus + i


jump_stack = []


cdef PyObject* pyeval_fast_forward(PyFrameObject *frame, int exc):
    global jump_stack

    # Temporarily disable calling ourselves while we restore the frame. This
    # lets us call Python functions in restore_frame()
    PyThreadState_Get().interp.eval_frame = _PyEval_EvalFrameDefault
    log.debug('Disabled pyeval_fast_forward to restore a frame')

    restore_frame(frame, jump_stack.pop())

    log.debug('Re-enabled pyeval_fast_forward')
    PyThreadState_Get().interp.eval_frame = pyeval_fast_forward

    return _PyEval_EvalFrameDefault(frame, exc)


def jump(saved_frames: List[SavedStackFrame]):
    """Restore the state of the call stack.

    `saved_frames` is an object returned by save_jump().

    Restores the Python stack frames, the content of the stack frames, and the
    state of the CPython's internal call stack (the "C stack").

    The program proceeds from where saved_frames was generated and continues
    until the outermost function in the call stack returns. The return value
    of jump() is the return value of that outerframe.
    """
    global jump_stack
    jump_stack.clear()
    jump_stack.extend(list(saved_frames))

    cdef PyFrameObject *f = PyEval_GetFrame()
    cdef PyFrameObject *top_frame = f
    while f.f_back:
        top_frame = f
        f = f.f_back

    PyThreadState_Get().interp.eval_frame = pyeval_fast_forward
    return <object>pyeval_fast_forward(top_frame, 0)