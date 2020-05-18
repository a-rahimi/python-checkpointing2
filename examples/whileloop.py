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
        save_checkpoint("loop")
        i += 1

        if i > 5:
            break


if __name__ == "__main__":
    main()
