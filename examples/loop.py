import itertools
import time

from function_checkpointing import save_checkpoint, resume_from_checkpoint

def main():
    try:
        resume_from_checkpoint("loop")
    except FileNotFoundError:
        pass

    for i in itertools.count(0):
        print(i)
        time.sleep(1)
        save_checkpoint("loop")

main()
