"""End to end tests.

These tests check that the examples behave as expected.
"""


import shutil
import subprocess
import unittest


class TestExamples(unittest.TestCase):
    def assertLinesEqual(self, o1: str, o2: str):
        for i, (line1, line2) in enumerate(zip(o1.split("\n"), o2.split("\n"))):
            self.assertEqual(line1, line2, "Discrepancy at line %d" % i)

    def check_output(self, cmd, expected_output):
        p = subprocess.run(cmd, capture_output=True, check=True)
        actual_output = p.stdout.decode("utf8")
        self.assertLinesEqual(expected_output, actual_output)

    def delete_checkpoints(self):
        shutil.rmtree('__checkpoints__', ignore_errors=True)

    def tearDown(self):
        self.delete_checkpoints()

    def setUp(self):
        self.delete_checkpoints()

    def test_snapshot_in_loop(self):
        self.check_output(
            ["python3", "../examples/snapshot_in_loop.py"],
            """---Run processing to completion, saving checkpoints---
step1 a= 2 lst= ['step1']
step2 a= 4 lst= ['step1', 'step2']
step3 a= 8 lst= ['step1', 'step2', 'step3']
end
step1 a= 2 lst= ['step1']
step2 a= 4 lst= ['step1', 'step2']
step3 a= 8 lst= ['step1', 'step2', 'step3']
end
step1 a= 2 lst= ['step1']
step2 a= 4 lst= ['step1', 'step2']
step3 a= 8 lst= ['step1', 'step2', 'step3']
end
---There are 4 checkpoints. Fastforward to 2nd checkpont---
Checkpoint is being resumed
Resuming from subroutine
step2 a= 4 lst= ['step1', 'step2']
step3 a= 8 lst= ['step1', 'step2', 'step3']
end
step1 a= 2 lst= ['step1']
step2 a= 4 lst= ['step1', 'step2']
step3 a= 8 lst= ['step1', 'step2', 'step3']
end
step1 a= 2 lst= ['step1']
step2 a= 4 lst= ['step1', 'step2']
step3 a= 8 lst= ['step1', 'step2', 'step3']
end
---There are only 10 checkpoints now---
EXITING MAIN
<save_restore.jump(checkpoints[1])
EXITING MAIN
""",
        )

    def test_raise_during_restore(self):
        self.check_output(
            ["python3", "../examples/raise_during_restore.py"], 
            """---Run processing to completion, saving checkpoints---
step1 a= 2 lst= ['step1']
entering subroutine. a=2
leaving subroutine. a=2
step2 a= 4 lst= ['step1', 'step2']
step3 a= 8 lst= ['step1', 'step2', 'step3']
end
---There are 4 checkpoints. Fastforward to 2nd checkpont---
Checkpoint is being resumed
Resuming from subroutine
Caught resume exception
---There are only 0 checkpoints now---
EXITING MAIN
<save_restore.jump(checkpoints[1])
EXITING MAIN""")

    def test_save_to_disk(self):
        self.check_output(["python3", "../examples/save_to_disk.py"],
                """Running to completion and dumping checkpoints
step1 a= 2 lst= ['step1']
entering subroutine. a=2
leaving subroutine. a=2
step2 a= 4 lst= ['step1', 'step2']
step3 a= 8 lst= ['step1', 'step2', 'step3']
end

You can now re-run passing checkpoint filename to restart
""")
        self.check_output(["python3", "../examples/save_to_disk.py", "step2"],
                """step3 a= 8 lst= ['step1', 'step2', 'step3']
end

You can now re-run passing checkpoint filename to restart
Jump finished
""")

    def test_while_loop(self):
        self.check_output(["python3", "../examples/whileloop.py"],
                """0
1
2
3
4
5""")

    def test_varargs(self):
        self.check_output(["python3", "../examples/varargs.py"],
                """foo in 1 2 3 4
foo out 1 2 3 4
foo out 1 2 3 4""")
