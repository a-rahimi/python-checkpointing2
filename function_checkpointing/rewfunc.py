"""Illustrate snapshotting a generator and rewinding it.
"""

import copy

import save_restore

checkpoints = []

def save_checkpoint():
    ckpt = save_restore.save_jump()
    if not ckpt:
        print('Checkpoint is being resumed')
        global checkpoints
        checkpoints.clear()
        return False

    checkpoints.append(copy.deepcopy(ckpt))
    return True

def processing(a, b):
    lst = []
    step = "step1"
    lst.append(step)
    print(step, "a=", a, "lst=", lst)

    save_checkpoint()

    step = "step2"
    b = 2
    a *= b
    lst.append(step)
    print(step, "a=", a, "lst=", lst)

    save_checkpoint()

    step = "step3"
    c = 2
    a *= c
    lst.append(step)
    print(step, "a=", a, "lst=", lst)

    save_checkpoint()

    print("end")


def main():
    print("---Run processing to completion, saving checkpoints---")
    processing(a=2, b=3)

    if len(checkpoints) == 3:
        print("---There are 3 checkpoints. Fastforward to 2nd checkpont---")
        save_restore.jump(checkpoints[1])
    else:
        print("---There are only %d checkpoints now---" % len(checkpoints))


main()
