from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, NoReturn

from cuid import cuid as generate_cuid

from .exceptions import CuidInvalid, CuidPrefixMismatch, CuidTypeMismatch
from .validation import is_valid_cuid


@dataclass(eq=True, order=False, frozen=True)
class Cuid:
    """
    Represent a prefixable cuid.

    This is the object returned by CuidField in normal use, such
    that the prefix and actual cuid of the full prefixed string are
    easily accessible.

    Instantiated with a cuid string with the optional prefix, this
    container validates the string as having the expected prefix and
    being a valid cuid before holding the values separately; while also
    enabling the cycling of a cuid with ease.

    NB: the dataclass is set up as `frozen` to protect against external
    modification of internal attributes; instead callers must be use the
    presented API.
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
            raise CuidInvalid(
                f"`{cuid}` `{type(cuid)}` is not a valid cuid, prefix: `{prefix}`"
            )

        # object.__setattr__ is used over simple assignment as dataclases
        # frozen=True encorces semi-fake immutability by overriding the
        # get/set methods on the class itself. This comes with a small perf
        # cost but it's worth it to ensure the values get treated as immutable
        # -to-external-entities (see docstring for more).
        object.__setattr__(self, "cuid", cuid)
        object.__setattr__(self, "prefix", prefix)

    def __str__(self) -> str:
        return self.prefix + self.cuid

    def cycle(self, generator: Callable | None = None) -> NoReturn:
        """
        Generate a new cuid in-place, with the same prefix.

        Allows for usage on a model field like:

            MyModel.cuid.cycle()
        """
        cuid_generator = generator or generate_cuid
        object.__setattr__(self, "cuid", cuid_generator())

    def __lt__(self, other: object) -> bool:
        if other.__class__ is not self.__class__:
            return NotImplemented

        if other.prefix != self.prefix:
            raise ValueError("Only Cuids with the same prefix can be compared")

        return self.cuid < other.cuid

    def __le__(self, other: object) -> bool:
        if other.__class__ is not self.__class__:
            return NotImplemented

        if other.prefix != self.prefix:
            raise ValueError("Only Cuids with the same prefix can be compared")

        return self.cuid <= other.cuid

    def __gt__(self, other: object) -> bool:
        if other.__class__ is not self.__class__:
            return NotImplemented

        if other.prefix != self.prefix:
            raise ValueError("Only Cuids with the same prefix can be compared")

        return self.cuid > other.cuid

    def __ge__(self, other: object) -> bool:
        if other.__class__ is not self.__class__:
            return NotImplemented

        if other.prefix != self.prefix:
            raise ValueError("Only Cuids with the same prefix can be compared")

        return self.cuid >= other.cuid
