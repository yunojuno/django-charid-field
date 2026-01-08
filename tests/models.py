from functools import partial

from django.db import models

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
    null_id_with_no_default = TestUIDField(null=True, default=None, blank=True)

    # Showcase a blankable but not null field; while also showcasing
    # a field where a default is not provided at all (not just None).
    not_null_id_but_blank = CharIDField(max_length=30, blank=True, unique=False)

    # Showcase the default field but without an index.
    no_index_id = TestUIDField(unique=False)

    # Showcase setting unique explicitly.
    unique_id = TestUIDField(unique=True)

    # Showcase with a static default + a prefix. This is very much an edge
    # case as I can't think of a good reason to ever want a static default
    # for an ID field, but given you can call it like this: we should test it.
    prefixed_and_non_callable_default_id = TestUIDField(
        prefix="test_", default="abcde", unique=False
    )

    def __str__(self):
        return f"[{self.id}] {self.name}"


class RelatedIDModel(models.Model):
    """Test related model to link to TestUIDField acting as primary key."""

    id = TestUIDField(primary_key=True)
    parent = models.ForeignKey(IDModel, on_delete=models.CASCADE)

    name = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.id} => {self.parent_id}"
