import numpy as np

import runner
import program_subordinate


def step1():
    print("running step1")
    return np.array([1, 2, 3])


def step2(a):
    print("running step2")
    return a * 2


def step3(a, b):
    print("running step3")
    return a + b


import dill

def main():
    runner.resume()
    dill.load_session('__checkpoint__/interpreter02.dill')
    r = runner.Runner(modules=[__file__, program_subordinate.__file__])

    r.start()

    a = step1()
    r.checkpoint()

    b = step2(a)
    r.checkpoint()

    program_subordinate.step2_1(a)
    r.checkpoint()

    c = step3(a, b)
    r.checkpoint()

    r.stop()

    print(c)


if __name__ == "__main__":
    main()
