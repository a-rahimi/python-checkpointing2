from typing import Dict, List, Sequence, Set, Tuple
import hashlib
import importlib
import glob
import os
import sys

import dill


def hash_code(f_code) -> bytes:
    h = hashlib.sha1(f_code.co_code)
    h.update(str(f_code.co_consts).encode("utf-8"))
    return h.digest()


class Runner:
    def __init__(self, modules: Sequence[str] = [sys.modules["__main__"].__file__]):
        self.functions: Dict[Tuple[str, str], bytes] = {}
        self.modules: Set[str] = set(modules)
        self.checkpoint_count = 0

    def start(self):
        self.functions.clear()
        sys.settrace(self._log_function_calls)

    def stop(self):
        self.functions.clear()
        sys.settrace(None)

    def checkpoint(self):
        os.makedirs("__checkpoint__", exist_ok=True)

        # Save set of functions to disk
        with open(
            "__checkpoint__/functions%02d.dill" % self.checkpoint_count, "wb"
        ) as f:
            dill.dump(self.functions, f)

        # Save the state of the interpreter to disk
        dill.dump_session(
            "__checkpoint__/interpreter%02d.dill" % self.checkpoint_count)

        self.functions.clear()
        self.checkpoint_count += 1

    def _log_function_calls(self, frame, event, args):
        if event != "call":
            return

        # to ovoid the overhead of this call, log only if the function is in
        # the desired modules.
        if frame.f_code.co_filename not in self.modules:
            return

        #print("---------")
        #print(frame.f_code.co_filename, frame.f_code.co_name)
        #print(frame.f_code.co_consts)

        # keep a fully qualified name for the function. and a sha1 of its code.
        # if we hold references to the frame object, we might cause a lot of
        # unexpected garbage to be kept around.
        self.functions[(frame.f_code.co_filename, frame.f_code.co_name)] = hash_code(
            frame.f_code
        )

        return self._log_function_calls


def resume():
    module_cache = {}

    # Inspect each checkpoint in sequence to see if the code in invoked has changed
    for functions_dill in sorted(glob.glob("__checkpoint__/functions*.dill")):
        print("Inspecting", functions_dill)
        with open(functions_dill, "rb") as f:
            functions = dill.load(f)

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
            current_hash = hash_code(getattr(module, function_name).__code__)

            if current_hash != expected_hash:
                print(filename, function_name, "has changed")
                break

    # Load the corresponding interpreter state
