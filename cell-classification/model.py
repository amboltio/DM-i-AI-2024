import numpy as np
import random

### CALL YOUR CUSTOM MODEL VIA THIS FUNCTION ###
def predict(image: np.ndarray) -> int:

    is_homogenous = example_model(image)

    return is_homogenous


def example_model(image) -> int:

    is_homogenous = random.randint(0, 1)

    return is_homogenous