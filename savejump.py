import inspect
import sys
import jump
from jump import print_frame

import program_subordinate

jmp = None

def level1():
    print(">level 1")
    func = "level1"
    level2()
    print("<level 1")


def level2():
    print(">level 2")
    func = "level2"
    level3()
    print("<level 2")


def level3():
    global jmp

    func = "level3"
    print(">level 3")
    program_subordinate.step2_1(1)
    jmp = jump.save_jump()
    print("stack at level3")
    print_frame(inspect.currentframe())
    print("<level 3")


def main():
    func = "main"
    level1()
    print("end of main")


main()

jump.jump(main, jmp)
