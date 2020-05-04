# Checkpointing Data Processing Programs

If you write data processing pipelines that take hours to run on your desktop,
you live in fear of crashes. A crash a few hours into your pipeline means you
have to wait that much longer before you get to the next experiment. For big
production pipelines, the solution is to use an industrial strength workflow
manager. For smaller pipelines that run on your desktop, the typical solution
is invest in some hand-woven checkpointing code.

This package helps you checkpoint your pipeline's work. When your pipeline
crashes, this package helps you restart it from the last checkpoint.  As a
bonus, if you modify your code to fix the crash, this package starts from a
known good checkpoint that does not get affected by the code change.

Ideally, your code might look like this:
```python
import snapshotting

def processing_idealized():
  ... do step 1...  

   # Snapshot the state of this function to disk
  snapshotting.save_or_restore("snapshot 1")  

  ... do step 2...
  
   # Snapshot the state of this function to disk
  snapshotting.save_or_restore("snapshot 2")  

  ... do step 3...
```

The function save_or_restore would checkpoint the entire state of your program
where it's called. When your program gets restored from this checkpoint, your
program would appear to just be returning from a call to this function.

Under this package, you write your processing pipeline as a Python
generator.  Each time your pipeline calls "yield", your generator's state gets
snapshotted to disk. The next time your pipeline starts, your generator resumes
from a known good checkpoint.

Before we get too far, a disclaimer: It's nearly impossible to automatically
fully checkpoint a program.  That would require checkpointing the state of the
resources your program depends on too, like the disk files and database servers
it accesses. That becomes very hard unless all these external resources provide
a standardized snapshotting mechanism.


## Saving and Restoring the State of your Function

Your main processing pipline would look like this:
```python
def processing():
  ... do step 1...
  yield "step1"    # Snapshot the state of this function to disk
  ... do step 2...
  yield "step2"    # Snapshot the state of this function to disk
  ... do step 3...
```

To run the generator and checkpoint it along the way, you can call
```python
save_checkpoints(processing())
```

To restore from a specific checkpoint, you can call
```python
resume_from_checkpoint(processing(), '__checkpoint__/step2')
```

This examle gives a flavor of what's possible with saving the state of
generators, but this package goes a little further.


## Selecting a Checkpoint by Detecting Changes in your Code

Normally, you'd want to resume your program from the latest checkpoint it
created before it crashed.  But typically after a crash, you modify your code
to fix the problem. Starting from the latest checkpoint might mean you don't
take advantage of that code change and you'll encounter the same crash.

Instead of resuming from the latest checkpoint, this package helps you identify
the latest checkpoint that has incurred no code change, and to resume from that
checkpoint.

To detect where your code has changed, the package provides a fast run-time
call profiler (benchmarks forthcoming). The call profiler logs the important
function calls in your code (the ones that happen in the modules you specify),
along with a hash of the function's code.  Each checkpoint also stores the
function calls that were made since the last checkpoint.  When it's time to
restore the state of the program, we inspect the call log of the checkpoints in
chronological order. The function hash for each function in the call log is
compared against its hash in the currently running program to check if the
function hash has become stale. The program resumes from the latest checkpoint
with a call log that has no stale hash.

This might sound complicated, but the API is simple. See
[examples/detect_code_change.py](examples/detect_code_change.py) for an
example. As before, all the work happens in a function called `processing()`,
and main() calls this function with a wrapper as:
```python
def main():
  resume_and_save_checkpoints(processing(), [__file__])
```

The second argument to `resume_and_save_checkpoints` specifies the list of
modules whose calls are logged.


## Restoring State by Hand

Restoring a checkpoint restores the state of the generator that drives your
pipeline.  This includes the generator's local variables, the Python
instruction pointer, and the Python stack.  But external objects like file
objects aren't restored correctly. The burden of restoring these
difficult-to-restore objects falls on you.

The yield call in your processing pipeline evaluates to True whenever your code
is restored from its corresponding checkpoint. Checking the value of this yield
tells you when to restore the difficult to restore state.

A processing loop that depends on an external file might use this like so:
```python
def processing():
  f = open('file.dat')
  ... processs file ...

  if (yield "step2"):   # Save a checkpoint
    # We're being restored from a checkpoint here. Reopen the file
    f = open('file.dat')

  ... process file some more...
```


# How it Works Under the Hood

I wasn't initially trying to checkpoint generators. I was trying to checkpoint
normal functions.

## Failed Attempts

I investigated several ideas before I landed on the above implementation. Here
were the lowlights:

1) I tried saving and restoring
[PyFrameObjects](https://github.com/python/cpython/blob/703647732359200c54f1d2e695cc3a06b9a96c9a/Include/cpython/frameobject.h#L17).
This almost works, except for one field: `f_stacktop`. The problem is that
[`_PyEval_EvalFrameDefault`](https://github.com/python/cpython/blob/6d86a2331e6b64a2ae80c1a21f81baa5a71ac594/Python/ceval.c#L880),
the interpreter's bytecode interpreter, stores the top of the stack as a [local
C
variabe](https://github.com/python/cpython/blob/6d86a2331e6b64a2ae80c1a21f81baa5a71ac594/Python/ceval.c#L887).
It spills it to the outside on only two occasions: [line-level
tracing](https://github.com/python/cpython/blob/6d86a2331e6b64a2ae80c1a21f81baa5a71ac594/Python/ceval.c#L1382)
(which is too slow to enable for all programs), and the [YIELD bytecode
instruction](https://github.com/python/cpython/blob/6d86a2331e6b64a2ae80c1a21f81baa5a71ac594/Python/ceval.c#L2204)
(which is what I ended up using). I tried a variety of sneaky ways to deduce
the top of the stack in other ways. For example, I tried examining the chain of
frames, but each frame ends up allocating a fresh stack. I also tried catching
transition between frames when a function gets called. The top of the stack is
passed around through several layers of [function
calls](https://github.com/python/cpython/blob/6d86a2331e6b64a2ae80c1a21f81baa5a71ac594/Python/ceval.c#L3480)
before the next frame is created, but I couldn't steal it from the interpreter.

2) Since the YIELD bytecode instruction causes the interpreter to [save the
stack
top](https://github.com/python/cpython/blob/6d86a2331e6b64a2ae80c1a21f81baa5a71ac594/Python/ceval.c#L2204),
I tried various ways to inject a YIELD instruction into the bytecode to trick
the interpreter to save its stack top. The most promising strategy seemed to be
to dynamically modify the bytecode to inject a YIELD instruction, but the YIELD
instruction has the undesirable side effect of exiting the current frame. I
considered working around this by making the frame's `f_back` pointer point to
itself to prevent the frame from getting popped, but that comes with its own
problems.

3) I tried ignoring `f_stacktop` all together and setting it to the bottom of
the stack, right above the local variables. This surprising worked on all the test
code I used. It assumes that the Python stack has no values on it before the
yield, which happened to be true for most simple code. But it wasn't too hard
to write code that violates this assumption.

4) Longjump/setjump the interpreter state. I considered snapshotting the state
of the CPython interpreter itself using longjmp and set setjmp. This seemed
like a great way solve this problem, except this state can't be serialized
between runs of CPython. Once the interpreter exits, the parts the snapshot
that refers to dynamically allocated data or data on the stack (almost all of
the state) is no longer correct.


## Surgery on Checkpoints

Here's what I ended up doing. When you call the generator's `__next__` method,
the generator advances until its next yield, where it updates a
[snapshot](https://github.com/python/cpython/blob/ae00a5a88534fd45939f86c12e038da9fa6f9ed6/Include/genobject.h#L31)
of itself and returns it to its caller.  This generator snapshot can be
manipulated. You can read its fields, save copies of it as a Python object,
save it to disk, and restore it. However, these operations can't happen in
Python. They have to happen in C. The Cython files in this package do just
that.

Consider these two lines from [examples/rewgen.py](examples/rewgen.py):
```python
      gen = processing()
      checkpoints = [copy.deepcopy(gen_surgery.save_generator_state(gen)) for _ in gen]
```
The list comprehension iterates through the generator, saving its state as a list of
checkpoints.

You can resume the checkpoint from any of these states by re-creating the generator
and resetting its state by calling
```python
      gen = processing()
      gen_surgery.restore_generator(gen, checkpoints[1])
```
You can then iterate through it as before, excep that it will execute on from checkpoint 1 instead of its normal start.


# Acknowledgement

I learned how to use Cython to do this manipulation frmo this
[very helpful repo](https://github.com/Elizaveta239/frame-eval). I also copied
code from it.

[`generator_tools`](https://pypi.org/project/generator_tools/) is a
sophisticated package that maniplates generators (it even rewrites the
generator's bytecode).  I decided not to use it because I could distill all the
generator manipulations I needed in
[`generator_checkpointing/save_restore_generators.pyx`](generator_checkpointing/save_restore_generators.pyx).
