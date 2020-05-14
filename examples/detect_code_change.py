"""Illustrate saving checkpoints and resuming from the last modified function.

Run this code first to generate the call graph and breakpoints. Then modify one
of the functions step0, step1, or step2. When you rerun the code, it will
resume from whichever function you modified.
"""
import logging
import function_checkpointing as ckpt


def step0():
    print(">step 1")


def step1():
    print(">step 2")


def step2():
    print(">step 3")


def processing():
    print("starting processing")

    if not ckpt.save_checkpoint_and_call_log("step0"):
        print("Resuming before step0")

    step0()

    if not ckpt.save_checkpoint_and_call_log("step1"):
        print("Resuming before step1")

    step1()

    if not ckpt.save_checkpoint_and_call_log("step2"):
        print("Resuming before step2")

    step2()

    print("done")


def main():
    logging.basicConfig()
    logging.getLogger("function_checkpointing").setLevel(logging.DEBUG)
    logging.getLogger("function_checkpointing.save_restore").setLevel(logging.DEBUG)
    logging.root.setLevel(logging.DEBUG)

    try:
        ckpt.resume_from_last_unchanged_checkpoint()
        return
    except ckpt.CheckpointNotFound:
        print('Starting from scratch')
        ckpt.start_call_tracing([__file__])
        processing()


if __name__ == "__main__":
    main()
