"""Illustrate saving the state of a generator to disk and starting it up from
a checkpoint.
"""

import sys

from generator_checkpointing import save_checkpoints, resume_from_checkpoint


def processing():
    lst = []
    step = "step1"
    a = 1
    lst.append(step)
    print(step, lst)

    if (yield "step1"):
        print("Resuming after step1")

    step = "step2"
    b = 2
    a *= 2
    lst.append(step)
    print(step, lst)

    if (yield "step2"):
        print("Resuming after step2")

    step = "step3"
    c = 2
    a *= 2
    lst.append(step)
    print(step, lst)

    if (yield "step3"):
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
