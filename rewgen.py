import copy

import save_restore_generators as jump


def processing():
    lst = []
    step = "step1"
    a = 2
    lst.append(step)
    print(step, "a=", a, "lst=", lst)

    t = yield  # Save a checkpoint here
    if t:
        print('Resuming from step2')
    step = "step2"
    b = 2
    a *= b
    lst.append(step)
    print(step, "a=", a, "lst=", lst)

    t = yield  # Save a checkpoint here
    if t:
        print('Resuming from step3')
    step = "step3"
    c = 2
    a *= c
    lst.append(step)
    print(step, "a=", a, "lst=", lst)

    t = yield  # Save a checkpoint here
    if t:
        print('Resuming from end')
    yield  # Save a checkpoint here
    print("end")


def main():
    print("-----Run processing to completion, saving checkpoints-----")
    gen = processing()
    checkpoints = [copy.deepcopy(jump.save_generator_state(gen)) for _ in gen]

    print("-----Restart processing from the first checkpoint-----")
    gen = processing()
    jump.restore_generator(gen, checkpoints[0])
    gen.send(True)
    for _ in gen:
        pass


main()
