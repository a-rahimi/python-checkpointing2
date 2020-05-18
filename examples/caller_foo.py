import function_checkpointing.save_restore as save_restore


def foo():
    c = save_restore.save_jump()
    if c:
        print("saved checkpoint")
        save_restore.jump(c)
    else:
        print("restored from checkpoint")

    print("foo returns")


def caller():
    print("caller->foo")
    foo()
    print("foo->caller")


caller()
