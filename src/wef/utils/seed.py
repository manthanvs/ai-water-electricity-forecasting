import os
import random
import sys

import numpy as np


def set_seed(seed: int = 42) -> None:
    """Seed Python and NumPy, and TensorFlow if it is already imported.

    TensorFlow is not imported here (slow); the deep-learning module calls set_seed after importing it.
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    tf = sys.modules.get("tensorflow")
    if tf is not None:
        tf.keras.utils.set_random_seed(seed)
        tf.config.experimental.enable_op_determinism()
