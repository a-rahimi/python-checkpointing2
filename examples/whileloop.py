import time

from function_checkpointing import save_checkpoint, resume_from_checkpoint


def main():
    try:
        resume_from_checkpoint("loop")
    except FileNotFoundError:
        pass

    i = 0
    while True:
        print(i)
        time.sleep(1)
        save_checkpoint("loop")
        i += 1

main()
