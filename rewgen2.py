from typing import Generator
import collections
import os
import pickle
import sys

import save_restore_generators as jump


Checkpoint = collections.namedtuple("Checkpoint", ["name", "generator_state"])


def save_checkpoints(gen: Generator):
    os.makedirs("__checkpoints__", exist_ok=True)
    for checkpoint_name in gen:
        ckpt = Checkpoint(checkpoint_name, jump.save_generator_state(gen))
        pickle.dump(ckpt, open(os.path.join("__checkpoints__", ckpt.name), "wb"))


def resume_from_checkpoint(gen: Generator, checkpoint_name: str):
    with open(os.path.join("__checkpoints__", checkpoint_name), "rb") as f:
        ckpt = pickle.load(f)

    if ckpt.name != checkpoint_name:
        raise RuntimeError(
            f"Loaded checkpoint name {ckpt.name} did not match requested "
            f"name {checkpoint_name}"
        )

    jump.restore_generator(gen, ckpt.generator_state)

    gen.send(True)
    for _ in gen:
        pass


def processing():
    lst = []
    step = "step1"
    a = 1
    lst.append(step)
    print(step, lst)

    t = yield "step1"
    if t:
        print("Resuming after step1")

    step = "step2"
    b = 2
    a *= 2
    lst.append(step)
    print(step, lst)

    t = yield "step2"
    if t:
        print("Resuming after step2")

    step = "step3"
    c = 2
    a *= 2
    lst.append(step)
    print(step, lst)

    t = yield "step3"
    if t:
        print("Resuming after step3")

    print("end")


def main():
    if len(sys.argv) > 1:
        # Restore the requested checkpoint
        resume_from_checkpoint(processing(), sys.argv[1])
    else:
        # Do a full run
        print("Running to completition and dumping checkpoints")
        checkpoints = save_checkpoints(processing())
        print("\nYou can now re-run passing checkpoint filename to restart")


main()
