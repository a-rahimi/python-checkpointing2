import inspect
import sys
import jump
from jump import print_frame

import program_subordinate


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
    func = "level3"
    print(">level 3")
    global frame, last_is
    frame = inspect.currentframe()
    last_is = []
    f = frame
    while f:
        last_is.append(f.f_lasti)
        f = f.f_back
    program_subordinate.step2_1(1)
    print("stack at level3")
    print_frame(inspect.currentframe())
    print("<level 3")


def main():
    func = "main"
    jump.trace_funcalls([__file__, program_subordinate.__file__])
    level1()
    print("end of main")


main()
print(jump.funcall_log)
