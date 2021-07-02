from django.db import models
from functools import partial

from charidfield import CharIDField

from .helpers import generate_test_uid


# To show off the recommended partial-usage; in production code you would
# likely be wrapping your own chosen ID generation scheme with a field of
# its own, e.g CuidField, KsuidField, UlidField, etc.
TestUIDField = partial(
    CharIDField,
    default=generate_test_uid,
    max_length=30,
    help_text="A char-based UID field for testing.",
)


class IDModel(models.Model):
    """Test model designed to showcase usage as the primary key."""

    name = models.CharField(max_length=20)

    # Showcase default primary key usage.
    id = TestUIDField(primary_key=True)

    # Showcase default non-primary key usage.
    default_id = TestUIDField()

    # Showcase with a literal string prefix, with in-built default.
    prefixed_id = TestUIDField(prefix="dev_")

    # Showcase a nullable field, and overriding to have no default.
    nullable_id_with_no_default = TestUIDField(null=True, default=None, blank=True)

    # Showcase the default field but without an index.
    no_index_id = TestUIDField(unique=False)

    def __str__(self):
        return f"[{self.id}] {self.name}"


class RelatedIDModel(models.Model):
    """Test related model to link to TestUIDField acting as primary key."""

    id = TestUIDField(primary_key=True)
    parent = models.ForeignKey(IDModel, on_delete=models.CASCADE)

    name = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.id} => {self.parent_id}"
