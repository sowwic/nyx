"""Random value functions."""

import random
import string
import typing
import uuid


def random_float() -> float:
    """Get a random number from 0 up to, not including, 1."""
    return random.random()


def random_uniform(low: float, high: float) -> float:
    """Get a random number between low and high.

    Args:
        low: Lowest number.
        high: Highest number.
    """
    return random.uniform(low, high)


def random_int(low: int, high: int) -> int:
    """Get a random integer from low to high, both included.

    Args:
        low: Lowest integer.
        high: Highest integer.
    """
    return random.randint(low, high)


def random_gauss(mean: float = 0.0, deviation: float = 1.0) -> float:
    """Get a random number from a normal distribution.

    Args:
        mean: Center of the values.
        deviation: How far the values spread around the center.
    """
    return random.gauss(mean, deviation)


def random_bool(probability: float = 0.5) -> bool:
    """Get true with the given chance, 0 never and 1 always.

    Args:
        probability: Chance of true from 0 to 1.
    """
    return random.random() < probability


def random_choice(items: list) -> typing.Any:
    """Get a random item of a list.

    Args:
        items: List to take an item from.
    """
    return random.choice(items)


def random_sample(items: list, count: int) -> list:
    """Get a number of different random items of a list.

    Args:
        items: List to take items from.
        count: How many items to take.
    """
    return random.sample(items, count)


def shuffle(items: list) -> list:
    """Get the items of a list in random order.

    Args:
        items: List to put in random order.
    """
    return random.sample(items, len(items))


def random_string(length: int = 8, alphabet: str = "") -> str:
    """Get random characters, letters and digits unless an alphabet is given.

    Args:
        length: Number of characters.
        alphabet: Characters to choose from, letters and digits if empty.
    """
    characters = alphabet or string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def random_uuid() -> str:
    """Get a new random UUID."""
    return str(uuid.uuid4())


def set_seed(seed: int) -> int:
    """Make the random values that follow repeatable. Get the seed.

    Args:
        seed: Number the random values start from.
    """
    random.seed(seed)
    return seed
