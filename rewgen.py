import copy

import jump


def processing():
    lst = []
    step = "step1"
    a = 2
    lst.append(step)
    print(step, "a=", a, "lst=", lst)

    yield  # Save a checkpoint here
    step = "step2"
    b = 2
    a *= b
    lst.append(step)
    print(step, "a=", a, "lst=", lst)

    yield  # Save a checkpoint here
    step = "step3"
    c = 2
    a *= c
    lst.append(step)
    print(step, "a=", a, "lst=", lst)

    yield  # Save a checkpoint here
    print("end")


def main():
    print("-----Run processing to completion, saving checkpoints-----")
    gen = processing()
    checkpoints = [copy.deepcopy(jump.save_generator_state(gen)) for _ in gen]

    print("-----Restart processing from the second checkpoint-----")
    gen_restored = processing()
    jump.restore_generator(gen_restored, checkpoints[1])
    for _ in gen_restored:
        pass


main()
