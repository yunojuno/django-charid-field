from __future__ import annotations

from typing import Any, Type, Callable

from cuid import cuid as generate_cuid
from django.core import checks, exceptions
from django.db import models
from django.db.models.fields import NOT_PROVIDED, Field, CharField
from django.db.models.query_utils import DeferredAttribute
from django.utils.translation import gettext_lazy as _

from .cuid import Cuid
from .exceptions import CuidInvalid, CuidPrefixMismatch, CuidTypeMismatch


def generate_cuid_string(prefix: str = "") -> str:
    return f"{prefix}{generate_cuid()}"


class CuidDescriptor(DeferredAttribute):
    """
    Define a field descriptor for CuidFields on a model instance.

    Returns a Cuid when accessed to enable usage like::

        >>> from things import Thing
        >>> thing = Thing.object.get(name='Square')
        >>> str(thing.cuid_field)
        'cus_ckodhg53j000001labr7zezao'
        >>> thing.cuid_field.cuid
        'ckodhg53j000001labr7zezao'
        >>> thing.cuid_field.prefix
        'cus_'
    """

    def __set__(self, instance: models.Model, value: object) -> None:
        """Handle the setting of the fields value."""
        if value is None or isinstance(value, Cuid):
            instance.__dict__[self.field.name] = value
        else:
            instance.__dict__[self.field.name] = Cuid(value, prefix=self.field.prefix)


# See tests.models.get_prefix_from_class_name for an example prefix generator.
PrefixGenerator = Callable[[models.Model, Field, str], str]


class CuidField(CharField):
    default_error_messages = {
        "invalid_type": _("“%(value)s” is not a string."),
        "invalid_cuid": _("“%(value)s” does not contain a valid cuid string."),
        "invalid_prefix": _("“%(value)s” requires the prefix “%(prefix)s”."),
    }
    description = _("Collision-resistant universal identifier")
    empty_strings_allowed = False

    descriptor_class = CuidDescriptor

    def __init__(
        self,
        prefix: str = "",
        default: PrefixGenerator | NOT_PROVIDED | None = NOT_PROVIDED,
        *args: Any,
        **kwargs: Any,
    ) -> None:

        # See `contribute_to_class` for true prefix setup.
        self.init_prefix = prefix

        # We override `default` by, err.., default so that we can get
        # sensible usage out of the field without having to supply a
        # default always. If you explicitly do not want a default then
        # pass `default=None` or `default=""` depending on your case.
        kwargs["default"] = generate_cuid if default is NOT_PROVIDED else default

        # Ensure a unique index is set up by default unless the caller
        # explicitly disables it; this seems like the sane thing to do.
        kwargs.setdefault("unique", True)

        # NB: 25-chars is the minimum length for a full-length cuid
        # alone; but a) we support arbitary-length prefixes and b) the
        # spec allows for future implementations to increase the length
        # of the cuid. Due to this, and the fact Django requires a
        # max_length for CharFields we set a lenient default but we
        # recommend passing your own one in if you wish. If you're on
        # Postgres there is no real need as there is no perf diff.
        # between char(n), varchar(n) and text.
        kwargs.setdefault("max_length", 40)

        super().__init__(*args, **kwargs)

    def get_internal_type(self) -> str:
        return "CharField"

    def deconstruct(
        self,
    ) -> tuple[str, str, list, dict]:
        """Provide init values to serialize as part of migration freezing."""
        name, path, args, kwargs = super().deconstruct()

        # Store the generated prefix so that changes to
        # the prefix over time result in migration.
        kwargs["prefix"] = self.prefix

        return name, path, args, kwargs

    def check(self, **kwargs: Any) -> list[checks.CheckMessage]:
        errors = super().check(**kwargs)
        errors.extend(self._check_prefix())
        return errors

    def _check_prefix(self) -> list[checks.Error]:
        # Types have to be ignored here because these are runtime type checks
        # that will run against 3rd-party codebases we can't possibly predict.
        if not isinstance(self.init_prefix, str) and not callable(self.init_prefix):  # type: ignore[unreachable]
            return [  # type: ignore [unreachable]
                checks.Error(
                    "'prefix' keyword argument must be a string, or a callable",
                    hint=(
                        "Pass a string or a callable function (see docs for spec); "
                        "alternatively remove the argument to disable prefixing."
                    ),
                    obj=self,
                    id="CuidField.E001",
                )
            ]
        return []

    def to_python(self, value: object) -> Cuid | None:
        """Convert values to the 'Python object': the Cuid."""
        if isinstance(value, Cuid):
            return value

        if value is None:
            return value

        try:
            cuid = Cuid(value, prefix=self.prefix)
        except (CuidTypeMismatch, CuidInvalid) as exc:
            raise exceptions.ValidationError(
                self.error_messages[exc.error_message_type],
                code=exc.error_message_type,
                params={"value": value},
            )
        except CuidPrefixMismatch as exc:
            raise exceptions.ValidationError(
                self.error_messages[exc.error_message_type],
                code=exc.error_message_type,
                params={"value": value, "prefix": self.prefix},
            )
        return cuid

    # def from_db_value(self, value, expression, connection) -> Cuid | None:
    #     """Convert a value as returned by the database to a Python object."""
    #     if value is None:
    #         return value
    #     return Cuid(value, prefix=self.prefix)

    def get_prep_value(self, value: object) -> str | None:
        """Return the value prepared for use as a parameter in a query."""
        if value is None or value == "":
            return None

        if isinstance(value, Cuid):
            return str(value)

        try:
            cuid = Cuid(value, prefix=self.prefix)
        except ValueError as exc:
            msg = self.error_messages[exc.error_message_type]  # type: ignore[attr-defined]
            raise ValueError(msg % {"value": value})

        return str(cuid)

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
        model attributes/meta.
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
