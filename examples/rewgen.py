"""Illustrate snapshotting a generator and rewinding it.
"""

import copy

import generator_checkpointing.save_restore_generators as gen_surgery


def processing():
    lst = []
    step = "step1"
    a = 2
    lst.append(step)
    print(step, "a=", a, "lst=", lst)

    if (yield):  # Save a checkpoint here
        print("Resuming from step2")
    step = "step2"
    b = 2
    a *= b
    lst.append(step)
    print(step, "a=", a, "lst=", lst)

    if (yield):  # Save a checkpoint here
        print("Resuming from step3")
    step = "step3"
    c = 2
    a *= c
    lst.append(step)
    print(step, "a=", a, "lst=", lst)

    if (yield):  # Save a checkpoint here
        print("Resuming from end")
    yield  # Save a checkpoint here
    print("end")


def main():
    print("-----Run processing to completion, saving checkpoints-----")
    gen = processing()
    checkpoints = [copy.deepcopy(gen_surgery.save_generator_state(gen)) for _ in gen]

    print("-----Restart processing from the first checkpoint-----")
    gen = processing()
    gen_surgery.restore_generator(gen, checkpoints[0])
    gen.send(True)
    for _ in gen:
        pass


main()
