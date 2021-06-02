from __future__ import annotations

from typing import Any, Callable, Type

from django.core import checks, exceptions
from django.db import models
from django.db.models.fields import NOT_PROVIDED, CharField, Field
from django.utils.translation import gettext_lazy as _

# See tests.models.get_prefix_from_class_name for an example prefix generator.
PrefixGenerator = Callable[[models.Model, Field, str], str]


class CharIDField(CharField):
    default_error_messages = {
        "invalid_type": _("“%(value)s” is not a string."),
        "invalid_prefix": _("“%(value)s” requires the prefix “%(prefix)s”."),
    }
    description = _("Collision-resistant universal identifier")
    empty_strings_allowed = False

    def __init__(
        self,
        prefix: str = "",
        default: PrefixGenerator | NOT_PROVIDED | None = NOT_PROVIDED,
        *args: Any,
        **kwargs: Any,
    ) -> None:

        # See `contribute_to_class` for true prefix setup.
        self.init_prefix = prefix

        # We only re-declare the default kwarg ourselves to give
        # the user some type-hints to help with the creation of
        # the callable.
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

        kwargs["prefix"] = self.init_prefix

        return name, path, args, kwargs

    def check(self, **kwargs: Any) -> list[checks.CheckMessage]:
        errors = super().check(**kwargs)
        errors.extend(self._check_prefix())
        return errors

    def _check_prefix(self) -> list[checks.Error]:
        # Types have to be ignored here because these are runtime type checks
        # that will run against 3rd-party codebases we can't possibly predict.
        if not isinstance(self.init_prefix, str) and not callable(
            self.init_prefix
        ):  # type: ignore[unreachable]
            return [  # type: ignore [unreachable]
                checks.Error(
                    "'prefix' keyword argument must be a string, or a callable",
                    hint=(
                        "Pass a string or a callable function (see docs for spec); "
                        "alternatively remove the argument to disable prefixing."
                    ),
                    obj=self,
                    id="CharIDField.E001",
                )
            ]
        return []

    def to_python(self, value: object) -> str | None:
        """Convert value to correct type, while validating."""
        if value is None:
            return value

        # We simply opt-out of dealing with non-strings as
        # there is no sane way to convert every type.
        if not isinstance(value, str):
            raise exceptions.ValidationError(
                self.error_messages["invalid_type"],
                code="invalid_type",
                params={"value": value},
            )

        if self.prefix and not value.startswith(self.prefix):
            raise exceptions.ValidationError(
                self.error_messages["invalid_prefix"],
                code="invalid_prefix",
                params={"value": value, "prefix": self.prefix},
            )

        return value

    def get_default(self) -> str | None:
        """Return the prefixed default value for this field."""
        default = self._get_default()

        if default is None:
            return None

        return f"{self.prefix}{default}"

    def contribute_to_class(
        self, cls: Type[models.Model], name: str, **kwargs: Any
    ) -> None:
        """
        Register the field with the model class it belongs to.

        After initialisation the field is registered against a model class
        and it is at this point that Django calls `contribute_to_class` so
        that fields can carry out any model-specific actions.

        In our case, this is the first time we have access to the model that
        requested this field and thus we can pass it to the prefix callable
        (if it was supplied as one) allowing it to generate a prefix based on
        model attributes or other meta.
        """
        if callable(self.init_prefix):
            self.prefix = self.init_prefix(
                model_class=cls,
                field_instance=self,
                field_name=name,
            )
        else:
            self.prefix = self.init_prefix

        super().contribute_to_class(cls, name, **kwargs)
