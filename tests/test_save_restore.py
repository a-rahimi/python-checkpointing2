"""Test the gut of the package, save_restore.pyx
"""

from typing import Callable, List, Sequence
import dis
import unittest

import function_checkpointing.save_restore as save_restore


class TestLoopnestingLevel(unittest.TestCase):
    """Test the loop_nesting_level function.
    """

    def _test_func(self, func, expected_nesting_level):
        instructions = list(dis.Bytecode(func))
        sentinel_instruction_addr = next(
            addr
            for addr, inst in enumerate(instructions)
            if inst.opname == "BINARY_POWER"
        )

        actual_nesting_level = save_restore.loop_nesting_level(
            instructions, sentinel_instruction_addr
        )

        print(dis.dis(func))

        self.assertEqual(expected_nesting_level, actual_nesting_level)

    def test_func1(self):
        def func():
            for i in range(10):
                for j in range(20):
                    a = i ** j

        self._test_func(func, 2)

    def test_func2(self):
        def func():
            for i in range(10):
                a = i ** 2

        self._test_func(func, 1)

    def test_func3(self):
        def func():
            for i in range(10):
                a = i

            for i in range(10):
                for j in range(20):
                    a = i ** j

        self._test_func(func, 2)

    def test_func4(self):
        def func():
            while True:
                for j in range(20):
                    a = i ** j

        self._test_func(func, 1)

    def test_func5(self):
        def func():
            for j in range(20):
                while True:
                    a = i ** j

        self._test_func(func, 1)

    def test_func6(self):
        def func():
            for j in range(20):
                while True:
                    while True:
                        a = i ** j

        self._test_func(func, 1)

    def test_func7(self):
        def func():
            for j in range(20):
                while True:
                    while True:
                        for i in range(10):
                            a = i ** j

        self._test_func(func, 2)
