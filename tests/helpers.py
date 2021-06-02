import time
import re

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"

COUNTER = 0

TEST_UID_REGEX = re.compile(r"[a-z_]{0,8}_?[a-z0-9]{8,20}")


def _to_base36(number: int) -> str:
    """Convert a positive integer to a base36 string."""
    if number < 0:
        raise ValueError("Cannot encode negative numbers")

    chars = ""
    while number != 0:
        number, i = divmod(number, 36)  # 36-character alphabet
        chars = ALPHABET[i] + chars

    return chars or "0"


def generate_test_uid(prefix=""):
    """
    Mimic a monotonically-increasing unique ID.

    For testing only; this is a very bad non-collision resistant
    string ID generator and should not be used in any production
    setting. Instead use a proper spec like cuid, ksuid or ulid.

    """
    global COUNTER
    COUNTER += 1
    millis = int(time.time() * 1000)
    return prefix + _to_base36(millis) + _to_base36(COUNTER)
