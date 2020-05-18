"""Test the gut of the package, save_restore.pyx
"""

from typing import Callable, List, Sequence
import dis
import unittest

import function_checkpointing.save_restore as save_restore


class TestLoopNestingLevel(unittest.TestCase):
    """Test the loop_nesting_level function."""

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

    def test_noloop(self):
        def func():
            a = i ** j

        self._test_func(func, 0)


    def test_func1(self):
        def func():
            for i in range(10):
                for j in range(20):
                    a = i ** j

        self._test_func(func, 2)

    @unittest.expectedFailure
    def test_func1_with_return(self):
        """A trivial loop that returns on the first iteration doesn't get
        a JUMP_ABSOLUTE instruction at the end of the loop. Such loops
        break the nesting counter.
        """
        def func():
            for i in range(10):
                for j in range(20):
                    return i ** j

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


class TestCheckpoints(unittest.TestCase):
    def test_level_depth(self):
        def func4():
            return save_restore.save_jump()

        def func3():
            return func4()

        def func2():
            return func3()

        def func():
            return func2()

        c1 = func()
        c2 = func2()

        self.assertEqual(len(c1), len(c2) + 1)

    def simple_call_stack_size(self):
        return 2

    def test_simple_call(self):
        def func():
            return save_restore.save_jump()

        c = func()
        self.assertEqual(len(c[0].stack_content), self.simple_call_stack_size(), c[0])

    def test_simple_call_vars(self):
        def func():
            a = 2
            return save_restore.save_jump()

        c = func()
        self.assertEqual(len(c[0].stack_content), self.simple_call_stack_size() + 1)

    def test_simple_call_have_args(self):
        def func2(a, b, c):
            return save_restore.save_jump()

        def func():
            return func2(1, 2, 3)

        c = func()
        self.assertEqual(len(c[1].stack_content), self.simple_call_stack_size() + 3)

    def test_simple_call_have_varargs(self):
        def func2(a, b, c, d, e):
            return save_restore.save_jump()

        def func():
            return func2(*(1, 2, 3, 4, 5))

        c = func()
        self.assertEqual(len(c[1].stack_content), self.simple_call_stack_size() + 1)

    def test_simple_call_have_varargs_and_kwargs(self):
        def func2(a0, b0, a, b, c, d, e):
            return save_restore.save_jump()

        def func():
            return func2(*("a0", "b0"), **{"a": 1, "b": 2, "c": 3, "d": 4, "e": 5})

        c = func()
        self.assertEqual(len(c[1].stack_content), self.simple_call_stack_size() + 2)

    def test_simple_call_have_kwargs_only(self):
        def func2(a, b, c, d, e):
            return save_restore.save_jump()

        def func():
            return func2(**{"a": 1, "b": 2, "c": 3, "d": 4, "e": 5})

        c = func()
        self.assertEqual(len(c[1].stack_content), self.simple_call_stack_size() + 2)

    def test_simple_call_forloop_1(self):
        def func():
            for a in range(1):
                ckpt = save_restore.save_jump()
            return ckpt

        c = func()
        dis.dis(func)
        self.assertEqual(c[0].stack_content[-1], save_restore.save_jump, c[0])

    def test_simple_call_forloop_2(self):
        def func():
            for a in range(1):
                for b in range(1):
                    ckpt = save_restore.save_jump()
            return ckpt

        c = func()
        self.assertEqual(c[0].stack_content[-1], save_restore.save_jump, c[0])

    def test_simple_call_forloop_whileloop(self):
        def func():
            for a in range(1):
                while True:
                    ckpt = save_restore.save_jump()
                    break
            return ckpt

        c = func()
        self.assertEqual(c[0].stack_content[-1], save_restore.save_jump)
