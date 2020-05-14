"""Public API for generator-based checkpointing.
"""

from typing import List, Set, Tuple
import collections
import glob
import importlib.util
import itertools
import logging
import os
import pickle
import re


import function_checkpointing.calltrace as calltrace
import function_checkpointing.save_restore as save_restore

log = logging.getLogger(__name__)


def resume_from_checkpoint(fname: str):
    with open(f"__checkpoints__/{fname}", "rb") as f:
        ckpt = pickle.load(f)
    log.info("jump(%s)", fname)
    return save_restore.jump(ckpt)


def save_checkpoint(fname: str):
    if fname.startswith("calltrace-"):
        raise ValueError(
            '"calltrace-" is a reserved prefix in checkpoint "%s".' % fname
        )

    os.makedirs("__checkpoints__", exist_ok=True)

    ckpt = save_restore.save_jump()
    if ckpt:
        # We're actually saving instead of returning from save_jump after
        # a restore.
        with open(f"__checkpoints__/{fname}", "wb") as f:
            pickle.dump(ckpt, f)

    return ckpt


def sorted_calltraces():
    for _, fname in sorted(
        (os.path.getmtime(fname), fname)
        for fname in glob.glob("__checkpoints__/calltrace-*")
    ):
        yield fname


def checkpoint_from_trace(trace_fname: str) -> str:
    b = os.path.basename(trace_fname)
    if not b.startswith("calltrace-"):
        raise ValueError('Bad trace file name "%s"' % trace_fname)

    return "__checkpoints__/" + b[len("calltrace-") :]


def _change_point() -> str:
    """Identify a function call log whose functions have been modified.

    Browse the call logs in chronological order. Identify the first call log
    that contains a function whose code has been modified in the currently
    running program.

    Return the call log immediate preceding that one.  If no such call log is
    found, returns the last call log. If there are no call logs at all, returns
    an empty string.
    """
    module_cache = {}

    # Inspect each checkpoint in sequence to see if the code invoked has changed
    last_intact_trace_fname: str = ""

    for trace_fname in sorted_calltraces():
        with open(trace_fname, "rb") as f:
            functions = pickle.load(f)

        # Check each function the was called between this checkpoint and the previous
        # checkpoint. Determine whether the function's code has changed by comparing
        # the hash of its current bytecode against its old bytecode hash.
        for (filename, function_name), expected_hash in functions.items():
            # Load the file as a module. Use our own module cache to avoid polluting
            # the module cache.
            try:
                module = module_cache[filename]
            except KeyError:
                spec = importlib.util.spec_from_file_location("temporary", filename)
                if not spec:
                    raise RuntimeError(f"Could not load {filename}")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                module_cache[filename] = module

            # The hash for the current implementation of the function
            current_hash = calltrace.hash_code(getattr(module, function_name).__code__)

            if current_hash != expected_hash:
                log.info(
                    "Calllog %s has change %s:%s", trace_fname, filename, function_name
                )
                return last_intact_trace_fname

        last_intact_trace_fname = trace_fname

    return last_intact_trace_fname


class CheckpointNotFound(Exception):
    pass


def resume_from_last_unchanged_checkpoint():
    """Resume from the latest checkpoint that contains unmodified code.
    """
    trace_fname = _change_point()
    if not trace_fname:
        raise CheckpointNotFound()

    checkpoint_fname = checkpoint_from_trace(trace_fname)
    log.info("Restoring from checkpoint %s", checkpoint_fname)

    # delete all the checkpoints that appear after this
    fnames_to_del = itertools.dropwhile(lambda t: t != trace_fname, sorted_calltraces())
    next(fnames_to_del)
    for t in fnames_to_del:
        log.info("Deleting modified trace file & checkpoint %s", t)
        os.unlink(t)
        os.unlink(checkpoint_from_trace(t))

    return resume_from_checkpoint(os.path.basename(checkpoint_fname))


def start_call_tracing(module_names: List[str]):
    calltrace.trace_funcalls(module_names)


def save_checkpoint_and_call_log(checkpoint_name: str):
    # Turn off tracing while we're processing this checkpoint. We need to do
    # this because jump() needs to take over same python frame evaluator the
    # call tracer is using.
    modules = list(calltrace.modules)
    calltrace.stop_trace_funcalls()

    ckpt = save_checkpoint(checkpoint_name)
    if ckpt:
        log.debug('About to save the checkpoint "%s"', checkpoint_name)
        # We're actually saving a checkpoint. Save the call log in a separate file
        with open("__checkpoints__/calltrace-" + checkpoint_name, "wb") as f:
            pickle.dump(calltrace.funcall_log, f)
    else:
        log.debug('Restored from checkpoint "%s"', checkpoint_name)

    # Clear the call log so that the next checkpoint only records the function
    # calls that happen after this checkpoint.
    calltrace.funcall_log.clear()
    calltrace.trace_funcalls(modules)

    return ckpt
