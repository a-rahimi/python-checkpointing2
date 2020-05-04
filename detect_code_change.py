from typing import Generator, Set
import collections
import glob
import importlib
import os
import pickle

import calltrace
import save_restore_generators as jump

Checkpoint = collections.namedtuple("Checkpoint", ["name", "count", "generator_state"])


def change_point():
    module_cache = {}

    # Inspect each checkpoint in sequence to see if the code invoked has changed
    for trace_fname in sorted(glob.glob("__checkpoints__/functions*.pkl")):
        print("Inspecting", trace_fname)
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
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                module_cache[filename] = module

            # The hash for the current implementation of the function
            current_hash = calltrace.hash_code(getattr(module, function_name).__code__)

            if current_hash != expected_hash:
                return trace_fname


def save_checkpoints(gen: Generator, module_names: Set[str]):
    os.makedirs("__checkpoints__", exist_ok=True)

    calltrace.trace_funcalls(module_names)
    for checkpoint_i, checkpoint_name in enumerate(gen):
        # Turn off tracing while we're processing this checkpoint. This isn't
        # strictly necessary but as the code changes, this makes it easier to reason
        # about infinite loops.
        calltrace.stop_trace_funcalls()

        # Save the checkpoint
        ckpt = Checkpoint(checkpoint_name, checkpoint_i, jump.save_generator_state(gen))
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


def step1():
    print(">step 1")


def step2():
    print(">step 2")


def step3():
    print(">step 3")


def processing():
    yield "step1"
    step1()
    yield "step2"
    step2()
    yield "step3"
    step3()


def main():
    print("Code changed at", change_point())

    save_checkpoints(processing(), [__file__])


if __name__ == "__main__":
    main()
