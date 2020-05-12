"""Illustrate saving the callstack to disk and starting it up from a checkpoint.
"""

import logging
import os
import pickle
import sys

import function_checkpointing.save_restore as save_restore


def resume_from_checkpoint(fname: str):
    with open(f"__checkpoints__/{fname}", "rb") as f:
        ckpt = pickle.load(f)
    save_restore.jump(ckpt)


def save_checkpoint(fname: str):
    os.makedirs("__checkpoints__", exist_ok=True)

    ckpt = save_restore.save_jump()
    if ckpt:
        with open(f"__checkpoints__/{fname}", "wb") as f:
            pickle.dump(ckpt, f)
        return True
    else:
        print("Checkpoint is being resumed")
        return False


def subroutine(a):
    print("entering subroutine. a=%d" % a)
    save_checkpoint("subroutine")
    print("leaving subroutine. a=%d" % a)


def processing(a, b):
    lst = []
    step = "step1"
    lst.append(step)
    print(step, "a=", a, "lst=", lst)

    save_checkpoint("step1")

    subroutine(a)

    step = "step2"
    b = 2
    a *= b
    lst.append(step)
    print(step, "a=", a, "lst=", lst)

    save_checkpoint("step2")

    step = "step3"
    c = 2
    a *= c
    lst.append(step)
    print(step, "a=", a, "lst=", lst)

    save_checkpoint("step3")

    print("end")


def main():
    logging.basicConfig()
    logging.getLogger("function_checkpointing.save_restore").setLevel(logging.DEBUG)
    logging.root.setLevel(logging.DEBUG)

    if len(sys.argv) > 1:
        # Restore the requested checkpoint
        resume_from_checkpoint(sys.argv[1])
        print("Jump finished")
    else:
        print("Running to completition and dumping checkpoints")
        processing(a=2, b=3)
        print("\nYou can now re-run passing checkpoint filename to restart")


main()
