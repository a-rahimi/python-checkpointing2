import jump


def run_with_checkpoints(gen):
    checkpoints = []
    for _ in gen:
        checkpoints.append(jump.save_generator_state(gen))
    return checkpoints


def processing():
    step = "step1"
    print(step)
    yield

    step = "step2"
    print(step)
    yield

    step = "step3"
    print(step)
    yield

    print("end")


def main():
    checkpoints = run_with_checkpoints(processing())

    gen_restored = processing()
    jump.restore_generator(gen_restored, checkpoints[1])

    print("-----After restore-----")
    for _ in gen_restored:
        pass


main()
