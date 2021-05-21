import re

from cuid import cuid as generate_cuid
from django.db import models
from django.db.models.fields import Field

from cuidfield import CuidField


def get_prefix_from_class_name(
    *,
    model_class: models.Model,
    field_instance: Field,
    field_name: str,
) -> str:
    """Return the Model's name in snake_case for use as a cuid prefix."""
    name = model_class.__name__
    # CamelCase to snake_case
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower() + "_"


def callable_test_default():
    return f"test_{generate_cuid()}"


class CuidModel(models.Model):
    """Test model designed to showcase usage as the primary key."""

    name = models.CharField(max_length=10)

    # Showcase default primary key usage.
    id = CuidField(primary_key=True)

    # Showcase default non-primary key usage.
    default_cuid = CuidField()

    # Showcase with a literal string prefix, with in-built default.
    literal_prefixed_cuid = CuidField(prefix="dev_")

    # Showcase with a literal string prefix, with custom default.
    literal_prefixed_cuid_with_custom_default = CuidField(
        prefix="dev_", default=callable_test_default
    )

    # Showcase with a callable string prefix, with in-built default.
    callable_prefixed_cuid = CuidField(prefix=get_prefix_from_class_name)

    # Showcase with a callable string prefix, with custom default.
    callable_prefixed_cuid = CuidField(
        prefix=get_prefix_from_class_name, default=callable_test_default
    )

    # Showcase a nullable field, and overriding to have no default.
    nullable_cuid_with_no_default = CuidField(null=True, default=None, blank=True)

    # Showcase the default field but without an index.
    no_index_cuid = CuidField(unique=False)

    def __str__(self):
        return f"[{self.id}] {self.name}"


class RelatedCuidModel(models.Model):
    """Test related model to link to CuidField acting as primary key."""

    id = CuidField(primary_key=True)
    parent = models.ForeignKey(CuidModel, on_delete=models.CASCADE)

    name = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.id} => {self.parent_id}"
