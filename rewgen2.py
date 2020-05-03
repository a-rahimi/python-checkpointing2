import os
import pickle
import sys

import jump


class Checkpoint:
    def __init__(self, msg):
        self.msg = msg
        self.generator_state = None


def save_checkpoints(gen):
    os.makedirs('__checkpoints__', exist_ok=True)
    for ckpt in gen:
        ckpt.generator_state = jump.save_generator_state(gen)
        pickle.dump(ckpt, open(os.path.join('__checkpoints__', ckpt.msg), 'wb'))

def processing():
    step = 'step1'
    print(step)
    yield Checkpoint('step1')

    step = 'step2'
    print(step)
    yield Checkpoint('step2')

    step = 'step3'
    print(step)
    yield Checkpoint('step3')

    print('end')

def main():
    if len(sys.argv) > 1:
        # Restore the requested checkpoint
        ckpt = pickle.load(open(os.path.join('__checkpoints__', sys.argv[1]), 'rb'))
        gen_restored = jump.restore_generator(processing(), ckpt.generator_state)
        for _ in gen_restored:
            pass
    else:
        # Do a full run
        print("Running to completition and dumping checkpoints")
        checkpoints = save_checkpoints(processing())
        print("Re-run passing checkpoint filename to restart")

main()
