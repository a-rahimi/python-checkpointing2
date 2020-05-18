import time

import function_checkpointing.save_restore as save_restore


def foo(a, b, c, d):
    print("foo in", a, b, c, d)
    r = save_restore.save_jump()
    print("foo out", a, b, c, d)
    return r


def main():
    chkpt = foo(*(1, 2), **{"c": 3, "d": 4})

    if chkpt:
        # Don't try to jump again if we're being resumed.
        save_restore.jump(chkpt)


if __name__ == "__main__":
    main()
