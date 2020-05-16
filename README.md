# Checkpointing Python Programs

**TL;DR:** Here's an implementation of setjmp() and longjmp() for Python 3.6+. With
twist and Python flavors.

If you write data processing pipelines that take hours to run on your desktop,
you live in fear of crashes. Maybe you've invested in some hand-woven
checkpointing code.

This package helps you checkpoint your pipeline's work somewhat automatically.
When your pipeline crashes, this package helps you restart it from the last
checkpoint.  As a bonus, if you modify your code to fix the crash, this package
starts from a known good checkpoint that does not get affected by the code
change.

Your code ends up looking like this:
```python
import function_checkpointing as ckpt

def sub_stage1():
   for step in range(5):
       ... do some work...

       # Snapshot the state of this function to disk
       ckpt.save_checkpoint(f"snapshot sub_stage1 {step}")  

def processing():
  sub_stage1()   # Do some heavy lifting

  ... do some more work...

   # Snapshot the state of this function to disk
  ckpt.save_checkpoint("snapshot 2")  

  ... do some more work...
```

You can drop a checkpoint anywhere in your code. After your code resumes,
you don't need to implement logic to fast-forward your code's state to the
checkpoint. All that happens for your automatically.

The function `save_checkpont` snapshots to disk the state of your program as of
when it's called to disk. When your program gets restored from this checkpoint,
it appears to just be returning from a call `save_checkpoint` with a return
value of `[]`.

Before we get too far, a disclaimer: It's nearly impossible to automatically
fully checkpoint a program.  That would require checkpointing the state of the
resources your program depends on too, like the disk files and database servers
it accesses, and the state of the GPU. That becomes very hard unless all these
external resources provide a standardized snapshotting mechanism. You may need
to store some of the state manually. This particular package also has some
intentional design [limitations](#Limitations).


# The semantics of checkpointing

The main functions are `save_checkpoint` and `resume_from_checkpoint`.  Under
the hood, these functions write and read from pickle files, and call functions
named `save_jump` `jump` respectively.  The functions `save_jump` and `jump`
are useful in their own right. If you grok them, you grok this package.


# `save_jump`

The function `save_jump` takes no argument. It packages up and returns the
chain of frames that led up to this call. This package contains the local
variables, the Python bytecode interpreter stack, and the bytecode instruction
pointer at the location where `save_jump` was called. It also includes this
information for the parent frame that `save_jump`, and its caller's frame, all
the way up to the topmost frame.  It then returns this stashed stack frame as a
Python object you can inspect (and modify if you wish).

But there's a twist: `save_jump` can return twice. The above is what happens
when you're taking a snapshot.  But `save_jump` can also return when you're
restoring a snapshot. In that case, the return value of `save_jump` is an empty
list. You can use this to check if your program is being restored or if it's
checkpointing:

```python
c = ckpt.save_jump()
if not c:
    # We're resuming from a checkpoint. Reopen connection to the database.
    db = connect_to_database()
```

The semanetics of `save_jump` are similar to those of the POSIX setjmp() function.


# `jump`

`jump` takes one argument: a snapshot returned by `save_jump`. It restores the
state of the frame stack to the state that `save_jump` captured.

But instead of rooting the stack frames from the topmost frame, it does this
under its own stack frame. That means when the topmost stackframe that
originated the sequence of calls that culminated in `save_jump` finishes,
control returns to the stack frame that called `jump`, and jump.

This is an important distinction with the POSIX `longjmp()` function, which
never returns.

Practically, this means the function foo() below returns twice, an unusual concept
in most programming languages:

```python
def foo():
   c = ckpt.save_jump()
   if c:
      print('saved checkpoint')
      ckpt.jump(c)
   else:
      print('restored from checkpoint')

   print('foo returns')
```

This function prints:
```
saved checkpoint
restored from checkpoint
foo returns
foo returns
````

To appreciate this, let's call this function from another function:
```python
def caller():
    print('caller->foo')
    foo()
    print('foo->caller')
```
Calling this function prints
```
caller->foo
saved checkpoint
restored from checkpoint
foo returns
foo->caller
foo returns
foo->caller
````
It looks like world has split in two at the point of `save_jump`. But all that's
happening is that `jump` is recreating the callchain leading to `save_jump` by
navigating the interpreter through the saved frames.

Here's an illustration of what's happening. Calling caller results in a call to
foo, which results in a call to save_jump. This diagram captures the snapshot
captured in `c`:

[](images/snapshot.png)

As execution proceed down foo, we reach a call to `jump`. Jump reroots the
callchain captured in `c` under itself and fast forwards the Python interprter
to the leaf frame:

[](images/jump.png)
The last frame, foo, continues executing until it returns. Then `caller`
finishes executing, then the top level module executes, and finaly, the `jump`
function returns. We have reach the end of foo, so foo returns. Notice that foo
returned twice.

If you're not enjoying this mindbending fact, you can just terminate your program
after jump rturns by calling `sys.exit` immediately after `jump`.


## Is this like `yield` and Python generators?

There is a superficial resemblence between `save_jump` and the Python `yield`
statement: both stash the current stack frame. But then yield forces the
interpreter to exit the stack frame and return control to the caller's stack
frame, essentially acting as `return`. `save_jump`, on the other hand, saves
the entire chain of stack frames, and allows execution to remain in the current
frame. `save_jump` appears as a normal function call and not at all like
`return`.

Similarly, there is a superficial resemblence between `jump` and calling a
generator's `send` method. Calling `send` resumes the generator frame's
execution at the last `yield`.  But `jump` does more than that: it resumes
execution of the entire stack chain leading up to `save_jump`, not just the
single stack frame where `save_jump` was called.

My [earlier attempt at an automatic
checkpointing](/a-rahimi/python-checkpointing) library used the `yield`.  The
practical limitation with generators is that you can only snapshot one function
(the generator), and not the call chain that resulted in the generator being
called. That meant that my previous attempt, if you wanted to take snapshots at
multiple layers of the call chain, you'd have to use `yield from`, which imposed
an inconvenient structure on your code.


# Bonus: Selecting a Checkpoint by Detecting Changes in your Code

Normally, you'd want to resume your program from the latest checkpoint it
created before it crashed. But after a crash you might modify your code to fix
the problem that caused the crash. In such cases,  instead of resuming from the
latest checkpoint, this package helps you identify the latest checkpoint that
incurred no code change, and to resume from that checkpoint.

To detect where your code has changed, the package provides a run-time profiler
that logs the function calls in your code. The call log is stored to disk along
with each checkpoint.  When it's time to restore the state of the program, we
identify the latest checkpoint whose call log involves no calls to any modified
function.

A few functions give you control over this automatic restart mechanism.
* `start_call_tracing` turns on the call tracer.
*  `save_checkpoint_and_call_log` is a variant of `save_checkpoint` that stores the call log along with the checkpoint.
*  `resume_from_last_unchanged_checkpoint` identifies and loads the
relevant checkpoint.

See [examples/detect_code_change.py](examples/detect_code_change.py) for an
example.


# Under the Hood

Saving the Python interpreter state is tricky. The CPython interpreter has
effectively two stacks: the interpeter stack, which the bytecode instructions
operate on, and the C stack, which the bytecode interpreter uses to keep track
of its own state. We manipulate the state of both the CPython interpert stack
and the C stack.

In my previous attempt, I documented [why this is
hard](https://github.com/a-rahimi/python-checkpointing#failed-attempts).  The
chief problem is that obtaining the top of the CPython stack frame seems
impossible ([there's also this excellent answer from
Stackoverflow](https://stackoverflow.com/a/44443331/711585)). This package
solves this problem by relying on some known facts about the depth of the
python stack: When a function is called, its arguments are on the stack. We can
inspect the number of arguments of the function from its code object. But
depending on the kind of funciton call (a method call, a call with kwargs,
etc), the stack can include the instance that owns the method, or a tuple of
variables names. We account for these situations by inspect the CALL bytecode
that resulted in the call.  More object can be on the stack: if an exceptoin is
being handled or the caller is in the middle of a loop, the stack contains
additional items: the exception triplet, and the loop iterator. We count the
level of nesting of exceptions and loops to count these items. This heuristic
changes across Python versions.

To manipulate the C stack, this package forces nested calls to
`_PyEval_EvalFrameDefault`, the CPython bytcode interpreterer responsible for
executing a frame. Each call fast-forwards the execution in a frame by setting
the frame instruction counter `f_lasti` to that specified in the checkpoint.
These nested calls to `_PyEval_EvalFrameDefault` cause the C stack to attain
the state it had when `save_jump` was called.

# Limitations

* Requires Python 3.6: I rely on
  [PEP523](https://www.python.org/dev/peps/pep-0523/), which is only available
  in 3.6+.

* Only tested in Python 3.7. There's no fundamental limitation here. That just
  happens to be what I have.

* Does not store global variables: Again, no fundamental limitation here. I
  think save globals is both relatively straightforward and simultaneously not
  particular useful, so it's not yet implemented (it might make sense to
  implement it as an auxiliary package to keep this one simple).

* Might crash. Your code might crash this package. I'll fix the package if you
  send me a bug report. Instead of developing the perfect checkpointer with
  exhaustive test cases, I built for myself the simplest checkpointer, and then
  refine it as my use case grows. If the package does something weird for you, tell
  me and I'll work on ti.


# Acknowledgement

I learned how to use Cython to do this manipulation frmo this
[very helpful repo](https://github.com/Elizaveta239/frame-eval). I also copied
code from it.

[`generator_tools`](https://pypi.org/project/generator_tools/) is a
sophisticated package that maniplates generators (it even rewrites the
generator's bytecode).  I decided not to use it because I could distill all the
generator manipulations I needed in
[`generator_checkpointing/save_restore_generators.pyx`](generator_checkpointing/save_restore_generators.pyx).
