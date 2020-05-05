"""Illustrate the call tracer.


$ python3 calllog.py
...
[('calllog.py', 'level1'),
 ('calllog.py', 'level2'),
 ('calllog.py', 'level3'),
 ('/Users/alrhim/Runner/examples/calllog_subordinate.py', 'step2_1')]
"""

import pprint

import generator_checkpointing.calltrace as calltrace

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
pprint.pprint(list(calltrace.funcall_log.keys()))
