"""Public API for generator-based checkpointing.
"""

from typing import Generator, Set, Tuple
import collections
import glob
import importlib.util
import os
import pickle
import re


import generator_checkpointing.calltrace as calltrace
import generator_checkpointing.save_restore_generators as gen_surgery

Checkpoint = collections.namedtuple("Checkpoint", ["name", "count", "generator_state"])


def _change_point() -> str:
    """Identify a function call log whose functions have been modified.

    Browse the call logs in chronological order and report the first call log that
    contains a function call whose source code has changed since the call log was 
    recorded.

    If no such call log is found, returns the last call log. If there are no
    call logs at all, returns an empty string.
    """
    module_cache = {}

    # Inspect each checkpoint in sequence to see if the code invoked has changed
    last_intact_trace_fname: str = ""
    for trace_fname in sorted(glob.glob("__checkpoints__/functions*.pkl")):
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


def _checkpoint_to_resume() -> Tuple[int, str]:
    """Identify the checkpoint to resume.

    Find call log with a modified function and reports its corresponding checkpoint.
    """
    trace_fname = _change_point()
    if not trace_fname:
        return -1, ""
       
    m = re.match(r"(.*/)(functions)(\d*)(\.pkl)", trace_fname)
    if not m:
        raise RuntimeError(f"Bad calltrace file path {trace_fname}")

    return int(m[3]), m[1] + "checkpoint" + m[3] + m[4]


def resume_and_save_checkpoints(gen: Generator, module_names: Set[str]) -> None:
    """Resume a generator at the last checkpoint that contains unmodified code.

    This is the most automated part of this API.

    Suppose you've defined your processing pipeline as a generator of the form

       def process():
          ... do some work ...
          yield "step1"
          ... do some work ...
          yield "step1"
          ....

    Calling

       resume_and_save_checkpoints(process(), [__file__])

    starts your generator, saves its state to disk on every yield, and keeps
    track of the functions it calls along the way. If your generator had save
    checkpoints on a previous run of this program, resume_and_save_checkpoints
    first restarts your generator from the the latest checkpoint that can be
    reached without traversing a function whose code has been modified.

    See README.md for a more detailed explanation and
    examples/detect_code_change.py
    """
    os.makedirs("__checkpoints__", exist_ok=True)

    checkpoint_i, checkpoint_fname = _checkpoint_to_resume()
    if checkpoint_fname:
        with open(checkpoint_fname, "rb") as f:
            ckpt = pickle.load(f)
        gen_surgery.restore_generator(gen, ckpt.generator_state)
        resume_point = True
    else:
        resume_point = None

    print("Starting from checkpoint", checkpoint_i, checkpoint_fname)

    calltrace.trace_funcalls(module_names)
    while True:
        try:
            checkpoint_name = gen.send(resume_point)
        except StopIteration:
            break
        resume_point = False
        checkpoint_i += 1

        # Turn off tracing while we're processing this checkpoint. This isn't
        # strictly necessary but as the code changes, this makes it easier to reason
        # about infinite loops.
        calltrace.stop_trace_funcalls()

        # Save the checkpoint
        ckpt = Checkpoint(
            checkpoint_name, checkpoint_i, gen_surgery.save_generator_state(gen)
        )
        with open("__checkpoints__/checkpoint%02d.pkl" % ckpt.count, "wb") as f:
            pickle.dump(ckpt, f)

        # Save the call log in a separae file
        with open("__checkpoints__/functions%02d.pkl" % ckpt.count, "wb") as f:
            pickle.dump(calltrace.funcall_log, f)

        # Clear the call log so that the next checkpoint only records the function
        # calls that happen after this checkpoint.
        calltrace.funcall_log.clear()

        # Resume tracing just for the next call to the generator
        calltrace.trace_funcalls(module_names)


def save_checkpoints(gen: Generator):
    """Simple checkpoint driver.

    Suppose you've defined a generator like so:

       def process():
          ... do some work ...
          yield "step1"
          ... do some work ...
          yield "step1"
          ....

    To execute this generator and save checkpoints on every yield, invoke

       save_checkpoints(process())

    Every yield specifies the name of a checkpoint file in which the state of the
    generatoe is saved as a pickle. You can then restore the generator with 
    resume_from_checkpoint().

    For further examples, see examples/rewgen.py and examples/rewgen2.py.
    """
    os.makedirs("__checkpoints__", exist_ok=True)
    for checkpoint_name in gen:
        ckpt = Checkpoint(checkpoint_name, gen_surgery.save_generator_state(gen))
        pickle.dump(ckpt, open(os.path.join("__checkpoints__", ckpt.name), "wb"))


def resume_from_checkpoint(gen: Generator, checkpoint_name: str):
    """Simple checkpoint restorer.

    Suppose you've written your generator as described in save_checkpoints(),

       def process():
          ... do some work ...
          yield "step1"
          ... do some work ...
          yield "step1"
          ....

    and have saved its state as a pickle with save_checkpoints(). You can restore
    its state to the state it had when it executed 'yield "step1"' and resumes
    its execution from there by calling

       resume_from_checkpoint(process(), '__checkpoints__/step1')

    The yield point where the generator is resurrected evaluates to "True", whereas
    all subsequent yield pints evaluate to None. You can use this fact to restore
    the portion of that state of the generator that's otherwise hard to restore. For
    example, if you need to restore a file object at step1, your restore code could
    look like

      def processing():
         f = open('file.dat')
         ... processs file ...

         if (yield):   # Save a checkpoint
           # We're being restored from a checkpoint here. Reopen the file
           f = open('file.dat')

         ... process file some more...
    """
    with open(os.path.join("__checkpoints__", checkpoint_name), "rb") as f:
        ckpt = pickle.load(f)

    gen_surgery.restore_generator(gen, ckpt.generator_state)

    gen.send(True)
    for _ in gen:
        pass
