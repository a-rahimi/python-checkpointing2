import time
import logging

from function_checkpointing import save_checkpoint, resume_from_checkpoint

def main():
    i = 0

    try:
        resume_from_checkpoint("loop")
    except FileNotFoundError:
        pass

    while True:
        print(i)
        time.sleep(1)
        i += 1
        save_checkpoint("loop")

logging.basicConfig()
logging.getLogger("function_checkpointing.save_restore").setLevel(logging.DEBUG)
logging.root.setLevel(logging.DEBUG)
main()
