import inspect
import jump
from jump import print_frame

global frame, last_is


def level1():
    print('>level 1')
    func = 'level1'
    level2()
    print('<level 1')

def level2():
    print('>level 2')
    func = 'level2'
    level3()
    print('<level 2')

def level3():
    func = 'level3'
    print('>level 3')
    global frame, last_is
    frame = inspect.currentframe()
    last_is = []
    f = frame
    while f:
        last_is.append(f.f_lasti)
        f = f.f_back
    print('stack at level3')
    print_frame(inspect.currentframe())
    print('<level 3')

def level3_again():
    func = 'level3_again'
    global frame, last_is

    print('frame before lasti fixup', last_is)
    print_frame(frame)
    jump.fixup_lasti(frame, last_is)
    jump.jump(frame)
    print('stack after jump')
    print_frame(inspect.currentframe())

def main():
    func = 'main'
    level1()
    level3_again()
    print('end of main')

def mainmain():
    func = 'mainmain'
    main()
    print_frame(inspect.currentframe())

mainmain()
