# Forked and heavily modified from
#   https://github.com/Elizaveta239/frame-eval

from typing import Dict, Iterable, List, Tuple

from function_checkpointing.jump cimport *

import hashlib

funcall_log: Dict[Tuple[str, str], bytes] = {}
modules: List[str] = []


def hash_code(f_code) -> bytes:
  h = hashlib.sha1(f_code.co_code)
  h.update(str(f_code.co_consts).encode("utf-8"))
  return h.digest()


cdef object pyeval_log_funcall_entry(PyFrameObject *frame, int exc):
  frame_obj = <object> frame
  cdef PyThreadState *state = PyThreadState_Get()

  # to ovoid the overhead of this call, log only if the function is in
  # the desired modules.
  if frame_obj.f_code.co_filename not in modules:
      state.interp.eval_frame = _PyEval_EvalFrameDefault
      r = _PyEval_EvalFrameDefault(frame, exc)
      state.interp.eval_frame = pyeval_log_funcall_entry
      return r

  #print("---------Tracing-----")
  #print(frame_obj.f_code.co_filename, frame_obj.f_code.co_name)

  # Keep a fully qualified name for the function and a sha1 of its code.
  # If we hold references to the frame object, we might cause a lot of
  # unexpected garbage to be kept around.
  funcall_log[(frame_obj.f_code.co_filename, frame_obj.f_code.co_name)] = hash_code(
          frame_obj.f_code)

  return _PyEval_EvalFrameDefault(frame, exc)


def trace_funcalls(module_fnames: Iterable[str]) -> None:
    modules.clear()
    modules.extend(module_fnames)
    PyThreadState_Get().interp.eval_frame = pyeval_log_funcall_entry


def stop_trace_funcalls() -> None:
    PyThreadState_Get().interp.eval_frame = _PyEval_EvalFrameDefault
