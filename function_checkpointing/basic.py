import pickle
import os

import function_checkpointing.save_restore as save_restore


def resume_from_checkpoint(fname: str):
    with open(f"__checkpoints__/{fname}", "rb") as f:
        ckpt = pickle.load(f)
    save_restore.jump(ckpt)


def save_checkpoint(fname: str):
    os.makedirs("__checkpoints__", exist_ok=True)

    ckpt = save_restore.save_jump()
    if ckpt:
        with open(f"__checkpoints__/{fname}", "wb") as f:
            pickle.dump(ckpt, f)
    return ckpt
