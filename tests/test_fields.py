import pytest

from django.core import exceptions
from django.core.management import call_command
from django.shortcuts import get_object_or_404
from django.test import TestCase, override_settings
from io import StringIO

from cuidfield import is_valid_cuid
from .models import (
    CuidModel,
    RelatedCuidModel,
)


@pytest.mark.django_db
class TestCuidModel:
    def setup_method(self):
        self.instance = CuidModel.objects.create(name="Test")
        self.cuid = self.instance.pk
        # Extra entity that should not be returned in lookups,
        # to ensure that lookup filtering actually works.
        CuidModel.objects.create(name="Do not return")

    def test_creation(self):
        assert isinstance(self.instance, CuidModel)
        assert is_valid_cuid(str(self.instance.id)) is True
        assert is_valid_cuid(str(self.instance.default_cuid)) is True
        assert is_valid_cuid(str(self.instance.literal_prefixed_cuid)) is False
        assert is_valid_cuid(str(self.instance.callable_prefixed_cuid)) is True
        assert is_valid_cuid(str(self.instance.nullable_cuid)) is True
        assert is_valid_cuid(str(self.instance.no_index_cuid)) is True
        assert (
            len(
                set(
                    [
                        self.instance.id,
                        self.instance.default_cuid,
                        self.instance.literal_prefixed_cuid,
                        self.instance.callable_prefixed_cuid,
                        self.instance.nullable_cuid,
                        self.instance.no_index_cuid,
                    ]
                )
            )
            == 6
        )

    @pytest.mark.parametrize("lookup_field", ["pk", "id"])
    def test_get_lookup__with_cuid_object(self, lookup_field):
        lookup_filter = {lookup_field: self.cuid}
        instance = CuidModel.objects.get(**lookup_filter)
        assert instance == self.instance

    @pytest.mark.parametrize("lookup_field", ["pk", "id"])
    def test_get_lookup__with_string(self, lookup_field):
        lookup_filter = {lookup_field: str(self.cuid)}
        instance = CuidModel.objects.get(**lookup_filter)
        assert instance == self.instance

    @pytest.mark.parametrize("lookup_field", ["pk", "id"])
    def test_filter_exact_lookup__with_cuid_object(self, lookup_field):
        lookup_filter = {lookup_field: self.cuid}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance]

    @pytest.mark.parametrize("lookup_field", ["pk", "id"])
    def test_filter_exact_lookup__with_string(self, lookup_field):
        lookup_filter = {lookup_field: str(self.cuid)}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance]

    @pytest.mark.parametrize("lookup_field", ["pk", "id"])
    def test_filter_in_lookup__with_cuid_object(self, lookup_field):
        lookup_filter = {f"{lookup_field}__in": [self.cuid]}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance]

    @pytest.mark.parametrize("lookup_field", ["pk", "id"])
    def test_filter_in_lookup__with_string(self, lookup_field):
        lookup_filter = {f"{lookup_field}__in": [str(self.cuid)]}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance]

    def test_get_or_create(self):
        instance, created = CuidModel.objects.get_or_create(name="Test")
        assert isinstance(instance, CuidModel)
        assert instance.id == self.cuid
        assert created is False

        instance, created = CuidModel.objects.get_or_create(name="Create me")
        assert isinstance(instance, CuidModel)
        assert instance.id != self.cuid
        assert created is True


# TODO(pr) Many more tests needs to come surrounding:
# * lookup filtering
# * persistence
# * nullablity
# * indexing
# * use as a foreignkey (related)