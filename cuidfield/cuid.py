from __future__ import annotations

from dataclasses import dataclass

from .exceptions import CuidPrefixMismatch, CuidTypeMismatch, CuidInvalid
from .validation import is_valid_cuid


@dataclass(eq=True, order=False, frozen=True)
class Cuid:
    """
    Represent a prefixable immutable cuid.

    This is the object returned by CuidField in normal use.

    Instantiated with a cuid string with the optional prefix, this
    container validates the string as having the expected prefix and
    being a valid cuid before holding the values separately.
    """

    # Holds the cuid string, sans prefix.
    cuid: str

    # Holds the desired prefix for the ID. e.g "cus_".
    prefix: str = ""

    def __init__(self, value: object, *, prefix: str = ""):

        if not isinstance(value, str):
            raise CuidTypeMismatch(f"Value must be a string, not `{type(value)}`")

        if prefix and not value.startswith(prefix):
            raise CuidPrefixMismatch(
                f"Value `{value}` needs expected prefix: `{prefix}`"
            )

        if prefix:
            cuid = value.removeprefix(prefix)
        else:
            cuid = value

        if not is_valid_cuid(cuid):
            raise CuidInvalid("Value does not contain a valid cuid")

        # object.__setattr__ is used over simple assignment as dataclases
        # frozen=True encorces semi-fake immutability by overriding the
        # get/set methods on the class itself. This comes with a small perf
        # cost but it's worth it to ensure the values get treated as immutable.
        object.__setattr__(self, "cuid", cuid)
        object.__setattr__(self, "prefix", prefix)

    def __str__(self):
        return self.prefix + self.cuid

    def __lt__(self, other):
        if other.__class__ is not self.__class__:
            return NotImplemented

        if other.prefix != self.prefix:
            raise ValueError("Only Cuids with the same prefix can be compared")

        return self.cuid < other.cuid

    def __le__(self, other):
        if other.__class__ is not self.__class__:
            return NotImplemented

        if other.prefix != self.prefix:
            raise ValueError("Only Cuids with the same prefix can be compared")

        return self.cuid <= other.cuid

    def __gt__(self, other):
        if other.__class__ is not self.__class__:
            return NotImplemented

        if other.prefix != self.prefix:
            raise ValueError("Only Cuids with the same prefix can be compared")

        return self.cuid > other.cuid

    def __ge__(self, other):
        if other.__class__ is not self.__class__:
            return NotImplemented

        if other.prefix != self.prefix:
            raise ValueError("Only Cuids with the same prefix can be compared")

        return self.cuid >= other.cuid
