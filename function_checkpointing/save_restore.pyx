from typing import Generator, List, Tuple
SavedStackFrame = Tuple[int, List, bytes]
import dis

from jump cimport *

class NULLObject(object):
    pass

def save_jump() -> List[SavedStackFrame]:
    saved_stack: List[SavedStackFrame] = []

    if PyThreadState_Get().interp.eval_frame == pyeval_fast_forward:
        print('save_jump In the middle of a resume. Not saving.')
        return []

    cdef PyFrameObject *frame = PyEval_GetFrame()
    cdef child_frame_arg_count = 0  # the argcount of save_frame() above
    while frame.f_back:
        print('Saving frame "%s"' % <object>frame.f_code.co_name,
              'last_i=', frame.f_lasti,
              'co_argcount:', <object>frame.f_code.co_argcount)

        if frame.f_code.co_kwonlyargcount:
            print('co_kwonlyargcount:', <object>frame.f_code.co_kwonlyargcount)
            raise NotImplementedError("Can't yet handle functions with kw arguments "
                    "in the call chain")

        bytecode = dis.Bytecode(<object>frame.f_code, current_offset=frame.f_lasti)
        instructions = iter(bytecode)
        for _ in range(frame.f_lasti // 2):
            next(instructions)
        instr = next(instructions)

        # the local variables
        stack_size = frame.f_valuestack - frame.f_localsplus + child_frame_arg_count

        # The arguments to the CALL_FUNCTION instruction or whatever instruction
        # caused the method call.
        if instr.opname == 'CALL_FUNCTION':
            # +1 for the address of the function being called
            stack_size += 1
        elif instr.opname == 'CALL_METHOD':
            # +1 for the address of the method, +1 for the object
            stack_size += 2
        elif instr.opname == 'CALL_FUNCTION_KW':
            # +1 for the address of the function, +1 for the tuple containing
            # the names of variables
            stack_size += 2
        elif instr.opname:
            raise NotImplementedError("Don't know how to checkpoint around opcode"
                    f" {instr.opname} "
                    "Here is the function:\n"
                    + bytecode.dis())

        stack_content = [
                <object>frame.f_localsplus[i] if frame.f_localsplus[i] else NULLObject
                for i in range(stack_size)
            ]

        saved_stack.append((
            <object> frame.f_lasti,
            stack_content,
            <object>frame.f_code
            ))

        child_frame_arg_count = frame.f_code.co_argcount
        frame = frame.f_back

    return saved_stack


cdef reconstruct_frame(PyFrameObject *frame, saved_frame: SavedStackFrame):
    frame_obj = <object> frame
    saved_f_lasti, saved_stack_content, saved_f_code = saved_frame

    # TODO: remove the f_code entry when i'm more confident this is doing
    # the right thing
    if frame_obj.f_code != saved_f_code:
        print("OOPS!")
        print('Warning: trying to restore frame from wrong snapshot:',
                '\n   called_on.f_code', frame_obj.f_code, 
                '\n   saved_f_code', saved_f_code)
        return


    print('Fast forwarding', frame_obj, 'to instruction', saved_f_lasti)

    # Fast forward the instruction pointer. f_lasti points to a CALL instruction
    # (a CALL_METHOD or CALL_FUNCTION or similar). The frame evaluator starts
    # executin at f_lasti+2, but in this case, we want it to re-execute the call
    # to force it to recurse on itself. So preemptively decrement f_lasti by 2.
    frame.f_lasti = saved_f_lasti - 2

    cdef int i = 0
    for o in saved_stack_content:
        if o == NULLObject:
            frame.f_localsplus[i] = NULL
        else:
            frame.f_localsplus[i] = <PyObject*> o
            Py_INCREF(o)
        i += 1

    frame.f_stacktop = frame.f_localsplus + i

jump_stack = []


cdef PyObject* pyeval_fast_forward(PyFrameObject *frame, int exc):
    cdef _PyFrameEvalFunction *old_evaluator = set_evaluator()
    global jump_stack

    reconstruct_frame(frame, jump_stack.pop())

    if jump_stack:
        set_evaluator(old_evaluator)
    else:
        print('End of jump_stack. Removing pyeval_fast_forward handler.')
    
    print('>_PyEval_EvalFrameDefault')
    r = _PyEval_EvalFrameDefault(frame, exc)
    print('<_PyEval_EvalFrameDefault')
    return r


cdef _PyFrameEvalFunction *set_evaluator(_PyFrameEvalFunction *frame_evaluator = NULL):
    cdef PyThreadState *state = PyThreadState_Get()
    cdef _PyFrameEvalFunction *old_evaluator = state.interp.eval_frame

    if frame_evaluator:
        state.interp.eval_frame = frame_evaluator
    else:
        state.interp.eval_frame = _PyEval_EvalFrameDefault

    return old_evaluator 


def jump(saved_frames: List[SavedStackFrame]):
    global jump_stack_idx
    jump_stack.clear()
    jump_stack.extend(list(saved_frames))

    # TODO: Reconstruct the top of the stack.
    cdef PyFrameObject *f = PyEval_GetFrame()
    cdef PyFrameObject *top_frame = f
    while f.f_back:
        top_frame = f
        f = f.f_back

    set_evaluator(pyeval_fast_forward)
    return <object>pyeval_fast_forward(top_frame, 0)
