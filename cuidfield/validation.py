"""Validation functions."""


def is_valid_cuid(value: str) -> bool:
    """
    Validate if a value is likely to be a valid cuid.

    "Likely" because there are no real constraints, see:
    https://github.com/ericelliott/cuid/issues/88

    Mirrors the current official implementation + an additional length check:
    https://github.com/ericelliott/cuid/blob/215b27bdb78d3400d4225a4eeecb3b71891a5f6f/index.js#L69
    """
    if not value.startswith("c"):
        return False

    # This library does not deal with cuid shortcodes, and thus
    # we only validate successfully against full length ones.
    # cuids are not length limited for future compatability.
    if len(value) < 25:
        return False

    return True
