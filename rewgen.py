import jump


def processing():
    step = "step1"
    a = 2
    print(step, "a=", a)
    yield  # Save a checkpoint here

    step = "step2"
    b = 2
    a *= b
    print(step, "a=", a)
    yield  # Save a checkpoint here

    step = "step3"
    c = 2
    a *= c
    print(step, "a=", a)
    yield  # Save a checkpoint here

    print("end")


def main():
    print("-----Run the process to completion, saving checkpoints-----")
    gen = processing()
    checkpoints = [jump.save_generator_state(gen) for _ in gen]

    print("-----Restart the process from the second checkpoint-----")
    gen_restored = processing()
    jump.restore_generator(gen_restored, checkpoints[1])
    for _ in gen_restored:
        pass


main()
