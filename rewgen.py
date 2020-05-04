import jump


def run_with_checkpoints(gen):
    checkpoints = []
    for _ in gen:
        checkpoints.append(jump.save_generator_state(gen))
        print('Checkpointed stored')
    return checkpoints


def processing():
    step = "step1"
    a = 2.1
    print(step, a)
    yield

    step = "step2"
    b = 2.2
    a *= b
    print(step, a)
    yield

    step = "step3"
    c = 2.3
    a *= c
    print(step, a)
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
