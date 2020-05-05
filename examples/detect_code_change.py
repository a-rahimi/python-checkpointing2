"""Illustrate saving checkpoints and resuming from the last modified function.

Run this code first to generate the call graph and breakpoints. Then modify one
of the functions step0, step1, or step2. When you rerun the code, it will
resume from whichever function you modified.
"""


from generator_checkpointing import resume_and_save_checkpoints


def step0():
    print(">step 1")


def step1():
    print(">step 2")


def step2():
    print(">step 3")


def processing():
    print("starting")

    if (yield "step0"):
        print("Resuming before step0")

    step0()

    if (yield "step1"):
        print("Resuming before step1")

    step1()

    if (yield "step2"):
        print("Resuming before step2")

    step2()

    print("done")


def main():
    resume_and_save_checkpoints(processing(), [__file__])


if __name__ == "__main__":
    main()
