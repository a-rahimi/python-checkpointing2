"""Illustrate saving the callstack to disk and starting it up from a checkpoint.
"""

import logging
import sys

from function_checkpointing.basic import save_checkpoint, resume_from_checkpoint


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
        print("Running to completion and dumping checkpoints")
        processing(a=2, b=3)
        print("\nYou can now re-run passing checkpoint filename to restart")


main()
