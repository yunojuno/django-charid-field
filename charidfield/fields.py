from __future__ import annotations

from typing import Any, Callable

from django.core import checks, exceptions
from django.db import models
from django.db.models.fields import NOT_PROVIDED, CharField
from django.utils.translation import gettext_lazy as _


def prefixed_default(default: Callable | str, *, prefix: str) -> Callable:
    if callable(default):
        return lambda: f"{prefix}{default()}"
    else:
        return lambda: f"{prefix}{default}"


class CharIDField(CharField):
    default_error_messages = {
        "invalid_type": _("The value must be text"),
        "invalid_prefix": _("“%(value)s” requires the prefix “%(prefix)s”."),
    }
    description = _("Collision-resistant universal identifier")
    empty_strings_allowed = False

    def __init__(
        self,
        prefix: str = "",
        default: Callable | NOT_PROVIDED | None = NOT_PROVIDED,
        *args: Any,
        **kwargs: Any,
    ) -> None:

        self.prefix = prefix

        if self.prefix:
            # We wrap the default passed in so that we can apply the prefix.
            kwargs["default"] = prefixed_default(default, prefix=prefix)
        else:
            kwargs["default"] = default

        # Ensure a unique index is set up by default unless the caller
        # explicitly disables it; this seems like the sane thing to do.
        kwargs.setdefault("unique", True)

        super().__init__(*args, **kwargs)

    def get_internal_type(self) -> str:
        return "CharField"

    def deconstruct(
        self,
    ) -> tuple[str, str, list, dict]:
        """Provide init values to serialize as part of migration freezing."""
        name, path, args, kwargs = super().deconstruct()

        kwargs["prefix"] = self.prefix

        return name, path, args, kwargs

    def check(self, **kwargs: Any) -> list[checks.CheckMessage]:
        errors = super().check(**kwargs)
        errors.extend(self._check_prefix())
        return errors

    def _check_prefix(self) -> list[checks.Error]:
        # Types have to be ignored here because these are runtime type checks
        # that will run against 3rd-party codebases we can't possibly predict.
        if not isinstance(self.prefix, str):  # type: ignore[unreachable]
            return [  # type: ignore [unreachable]
                checks.Error(
                    "'prefix' keyword argument must be a string",
                    hint=(
                        "Pass a string or alternatively remove the "
                        "argument to disable prefixing."
                    ),
                    obj=self,
                    id="CharIDField.E001",
                )
            ]
        return []

    def validate(self, value: object, model_instance: models.Model):
        """Validate the fields value, called from .clean() on parent."""

        # No non-string types.
        if not isinstance(value, str):
            raise exceptions.ValidationError(
                self.error_messages["invalid_type"],
                code="invalid_type",
            )

        # Value must have prefix if the prefix is set.
        if self.prefix and not value.startswith(self.prefix):
            raise exceptions.ValidationError(
                self.error_messages["invalid_prefix"],
                code="invalid_prefix",
                params={"value": value, "prefix": self.prefix},
            )

        return super().validate(value, model_instance)

    #def get_default(self) -> str | None:
    #    """Return the prefixed default value for this field."""
    #    default = self._get_default()

    #    if default is None:
    #        return None

    #    return f"{self.prefix}{default}"
