import inspect
import sys
import calltrace

import calllog_subordinate


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
    calllog_subordinate.step2_1(1)
    print("<level 3")


def main():
    func = "main"
    calltrace.trace_funcalls([__file__, calllog_subordinate.__file__])
    level1()
    print("end of main")


main()
print(calltrace.funcall_log)
