import datetime
import json
from dataclasses import FrozenInstanceError
from io import StringIO

import pytest
from cuid import cuid as generate_cuid
from django.core import exceptions
from django.core.management import call_command
from django.core.serializers.base import DeserializationError
from django.shortcuts import get_object_or_404
from django.test import TestCase, override_settings
from pytest_django.asserts import assertJSONEqual

from cuidfield import Cuid, generate_cuid_string, is_valid_cuid

from .models import CuidModel, RelatedCuidModel


@pytest.mark.django_db
class TestCuidModel:
    def setup_method(self):
        # The main entity tests will be carried out against.
        self.instance_a = CuidModel.objects.create(name="Instance A")
        # Extra entities to ensure lookup/ordering tests are safe.
        self.instance_b = CuidModel.objects.create(name="Instance B")

    def test_creation_types_and_basic_values(self):
        assert isinstance(self.instance_a, CuidModel)

        assert isinstance(self.instance_a.id, Cuid)
        assert isinstance(self.instance_a.default_cuid, Cuid)
        assert isinstance(self.instance_a.literal_prefixed_cuid, Cuid)
        assert isinstance(self.instance_a.callable_prefixed_cuid, Cuid)
        assert isinstance(self.instance_a.no_index_cuid, Cuid)

        assert is_valid_cuid(str(self.instance_a.id)) is True
        assert is_valid_cuid(str(self.instance_a.default_cuid)) is True
        assert is_valid_cuid(str(self.instance_a.literal_prefixed_cuid)) is False
        assert is_valid_cuid(str(self.instance_a.callable_prefixed_cuid)) is True
        assert self.instance_a.nullable_cuid_with_no_default is None
        assert is_valid_cuid(str(self.instance_a.no_index_cuid)) is True

    def test_ordering_by_id(self):
        asc_queryset = CuidModel.objects.all().order_by("id")
        assert list(asc_queryset) == [self.instance_a, self.instance_b]
        desc_queryset = CuidModel.objects.all().order_by("-id")
        assert list(desc_queryset) == [self.instance_b, self.instance_a]

    def test_no_collision_amongst_same_model_fields(self):
        # This is obviously not a collision-resistance test; but rather
        # one to ensure that defining two Cuid fields on the same model
        # never results in weird cross-contamination.
        assert (
            len(
                set(
                    [
                        self.instance_a.id,
                        self.instance_a.default_cuid,
                        self.instance_a.literal_prefixed_cuid,
                        self.instance_a.callable_prefixed_cuid,
                        self.instance_a.nullable_cuid_with_no_default,
                        self.instance_a.no_index_cuid,
                    ]
                )
            )
            == 6
        )

    @pytest.mark.parametrize(
        "model_field_name, lookup_field_name",
        (
            ("id", "id"),
            ("id", "pk"),
            ("default_cuid", "default_cuid"),
            ("literal_prefixed_cuid", "literal_prefixed_cuid"),
            ("callable_prefixed_cuid", "callable_prefixed_cuid"),
            ("no_index_cuid", "no_index_cuid"),
        ),
    )
    def test_lookups__with_cuid_object(self, model_field_name, lookup_field_name):
        lookup_value = getattr(self.instance_a, model_field_name)
        self._assert_lookups(lookup_field_name, lookup_value)

    @pytest.mark.parametrize(
        "model_field_name, lookup_field_name",
        (
            ("id", "id"),
            ("id", "pk"),
            ("default_cuid", "default_cuid"),
            ("literal_prefixed_cuid", "literal_prefixed_cuid"),
            ("callable_prefixed_cuid", "callable_prefixed_cuid"),
            ("no_index_cuid", "no_index_cuid"),
        ),
    )
    def test_get_lookup__with_string(self, model_field_name, lookup_field_name):
        # Apply str() to get the stringified version of the prefixable Cuid object.
        lookup_value = str(getattr(self.instance_a, model_field_name))
        self._assert_lookups(lookup_field_name, lookup_value)

    def _assert_lookups(self, lookup_field_name, lookup_value):
        # Test QuerySet.get
        lookup_filter = {lookup_field_name: lookup_value}
        instance = CuidModel.objects.get(**lookup_filter)
        assert instance == self.instance_a

        # Test QuerySet.filter exact (implicit)
        lookup_filter = {lookup_field_name: lookup_value}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

        # Test QuerySet.filter exact (explicit)
        lookup_filter = {f"{lookup_field_name}__exact": lookup_value}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

        # Test QuerySet.filter iexact
        lookup_filter = {f"{lookup_field_name}__iexact": lookup_value}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

        # Test QuerySet.filter contains
        lookup_filter = {f"{lookup_field_name}__contains": lookup_value}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

        # Test QuerySet.filter icontains
        lookup_filter = {f"{lookup_field_name}__icontains": lookup_value}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

        # Test Queryset.filter __in
        lookup_filter = {f"{lookup_field_name}__in": [lookup_value]}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

    def test_lookups__subqueries(self):
        a = CuidModel.objects.create(name="Record A")
        b = CuidModel.objects.create(name="Record B")
        CuidModel.objects.create(name="Record C")
        queryset = CuidModel.objects.filter(name__icontains="Record").order_by("name")[
            :2
        ]
        assert len(queryset) == 2
        assert list(queryset) == [a, b]

        subquery_lookup = CuidModel.objects.filter(id__in=queryset.values("id"))
        assert len(subquery_lookup) == 2
        assert list(subquery_lookup) == [a, b]

    def test_lookups__values(self):
        values_qs = CuidModel.objects.values("id")
        assert list(values_qs) == [
            {"id": str(self.instance_a.id)},
            {"id": str(self.instance_b.id)},
        ]

    def test_lookups__values_list(self):
        values_list_qs = CuidModel.objects.values_list("id", flat=True)
        assert list(values_list_qs) == [
            str(self.instance_a.id),
            str(self.instance_b.id),
        ]

    def test_lookups__isnull(self):
        assert (
            CuidModel.objects.filter(nullable_cuid_with_no_default__isnull=True).count()
            == 2
        )
        assert CuidModel.objects.filter(id__isnull=False).count() == 2

    def test_lookups__gt_lt(self):
        a = CuidModel.objects.create(name="Record A")
        b = CuidModel.objects.create(name="Record B")
        c = CuidModel.objects.create(name="Record C")
        base_queryset = CuidModel.objects.filter(name__icontains="Record")

        gt_queryset = base_queryset.filter(id__gt=b.id)
        assert list(gt_queryset) == [c]

        lt_queryset = base_queryset.filter(id__lt=b.id)
        assert list(lt_queryset) == [a]

        gte_queryset = base_queryset.filter(id__gte=b.id)
        assert list(gte_queryset) == [b, c]

        lte_queryset = base_queryset.filter(id__lte=b.id)
        assert list(lte_queryset) == [a, b]

    def test_get_or_create(self):
        instance, created = CuidModel.objects.get_or_create(name="Instance A")
        assert isinstance(instance, CuidModel)
        assert instance.id == self.instance_a.id
        assert created is False

        instance, created = CuidModel.objects.get_or_create(name="Instance D")
        assert isinstance(instance, CuidModel)
        assert created is True

    def test_setting_primary_key__as_a_string(self):
        old_cuid = self.instance_a.id
        self.instance_a.id = generate_cuid()
        new_cuid = self.instance_a.id
        assert isinstance(new_cuid, Cuid)
        assert new_cuid != old_cuid

        # Test persistance & retrieval; because we are changing the primary
        # key and re-saving we should expect a brand new object to be created
        # but the old one should be left alone. Because it is left alone, we
        # must cycle the cuid fields with a unique index, as otherwise the new
        # object will not persist.
        self.instance_a.callable_prefixed_cuid.cycle()
        self.instance_a.default_cuid.cycle()
        self.instance_a.literal_prefixed_cuid.cycle()
        self.instance_a.literal_prefixed_cuid_with_custom_default.cycle()
        self.instance_a.save()
        self.instance_a.refresh_from_db()
        assert self.instance_a.id == new_cuid
        assert CuidModel.objects.filter(id=old_cuid).count() == 1
        assert CuidModel.objects.filter(id=new_cuid).count() == 1

    def test_setting_primary_key__as_a_cuid(self):
        old_cuid = self.instance_a.id
        new_cuid_string = generate_cuid_string()
        new_cuid = Cuid(new_cuid_string)
        self.instance_a.id = new_cuid
        set_cuid = self.instance_a.id
        assert isinstance(set_cuid, Cuid)

        # Check retrieved set value against old cuid.
        assert set_cuid != old_cuid
        assert set_cuid.cuid != old_cuid.cuid
        assert set_cuid.prefix == old_cuid.prefix

        # Check retrieved set value against new cuid.
        assert set_cuid == new_cuid
        assert set_cuid.cuid == new_cuid.cuid
        assert set_cuid.prefix == new_cuid.prefix

        # Test persistance & retrieval; because we are changing the primary
        # key and re-saving we should expect a brand new object to be created
        # but the old one should be left alone. Because it is left alone, we
        # must cycle the cuid fields with a unique index, as otherwise the new
        # object will not persist.
        self.instance_a.callable_prefixed_cuid.cycle()
        self.instance_a.default_cuid.cycle()
        self.instance_a.literal_prefixed_cuid.cycle()
        self.instance_a.literal_prefixed_cuid_with_custom_default.cycle()
        self.instance_a.save()
        self.instance_a.refresh_from_db()
        assert self.instance_a.id == new_cuid
        assert CuidModel.objects.filter(id=old_cuid).count() == 1
        assert CuidModel.objects.filter(id=new_cuid).count() == 1

    @pytest.mark.parametrize(
        "model_field_name",
        (
            "default_cuid",
            "literal_prefixed_cuid",
            "callable_prefixed_cuid",
            "nullable_cuid_with_no_default",
            "no_index_cuid",
        ),
    )
    def test_setting_non_primary_key__as_a_string(self, model_field_name):
        old_cuid = getattr(self.instance_a, model_field_name)
        field = self.instance_a._meta.get_field(model_field_name)
        new_cuid_string = f"{field.prefix}{generate_cuid()}"
        setattr(self.instance_a, model_field_name, new_cuid_string)
        new_cuid = getattr(self.instance_a, model_field_name)
        assert isinstance(new_cuid, Cuid)
        assert new_cuid != old_cuid
        assert new_cuid.prefix == field.prefix
        assert is_valid_cuid(new_cuid.cuid)

        # Test persistance & retrieval; because we are settings non-primary key
        # values we would expect the mutation to occur on the existing entity.
        self.instance_a.save()
        self.instance_a.refresh_from_db()
        assert getattr(self.instance_a, model_field_name) == new_cuid
        assert CuidModel.objects.filter(**{model_field_name: new_cuid}).count() == 1
        if old_cuid:
            assert CuidModel.objects.filter(**{model_field_name: old_cuid}).count() == 0

    @pytest.mark.parametrize(
        "model_field_name",
        (
            "default_cuid",
            "literal_prefixed_cuid",
            "callable_prefixed_cuid",
            "nullable_cuid_with_no_default",
            "no_index_cuid",
        ),
    )
    def test_setting_non_primary_key_as_a_cuid(self, model_field_name):
        old_cuid = getattr(self.instance_a, model_field_name)
        field = self.instance_a._meta.get_field(model_field_name)
        new_cuid_string = generate_cuid_string(prefix=field.prefix)
        new_cuid = Cuid(new_cuid_string, prefix=field.prefix)
        setattr(self.instance_a, model_field_name, new_cuid)
        set_cuid = getattr(self.instance_a, model_field_name)
        assert isinstance(set_cuid, Cuid)
        assert is_valid_cuid(set_cuid.cuid)

        # Check retrieved against old cuid.
        assert set_cuid != old_cuid
        if old_cuid:
            assert set_cuid.cuid != old_cuid.cuid
            assert set_cuid.prefix == old_cuid.prefix

        # Check retrieved set value against new cuid.
        assert set_cuid == new_cuid
        assert set_cuid.cuid == new_cuid.cuid
        assert set_cuid.prefix == new_cuid.prefix

        # Test persistance & retrieval; because we are settings non-primary key
        # values we would expect the mutation to occur on the existing entity.
        self.instance_a.save()
        self.instance_a.refresh_from_db()
        assert getattr(self.instance_a, model_field_name) == new_cuid
        assert CuidModel.objects.filter(**{model_field_name: new_cuid}).count() == 1
        if old_cuid:
            assert CuidModel.objects.filter(**{model_field_name: old_cuid}).count() == 0

    def test_setting__inner_cuid_fields_are_immutable(self):
        with pytest.raises(FrozenInstanceError):
            self.instance_a.id.cuid = "fail"

        with pytest.raises(FrozenInstanceError):
            self.instance_a.id.prefix = "fail"

    @pytest.mark.parametrize(
        "value",
        [
            1,
            -1,
            datetime.datetime(2020, 1, 1, 12, 30),
            datetime.date(2020, 1, 1),
        ],
    )
    def test_setting__invalid_values(self, value):
        with pytest.raises(ValueError):
            self.instance_a.id = value

    def test_foreign_key__with_parent_model__instance(self):
        related_instance = RelatedCuidModel.objects.create(
            name="Blue Album", parent=self.instance_a
        )
        assert isinstance(related_instance, RelatedCuidModel)
        assert related_instance.parent == self.instance_a
        assert RelatedCuidModel.objects.get(parent=self.instance_a) == related_instance

    def test_foreign_key__with_parent_model__cuid(self):
        related_instance = RelatedCuidModel.objects.create(
            name="Blue Album", parent_id=self.instance_a.id
        )
        assert isinstance(related_instance, RelatedCuidModel)
        assert related_instance.parent == self.instance_a
        assert (
            RelatedCuidModel.objects.get(parent=self.instance_a.id) == related_instance
        )

    def test_foreign_key__with_parent_model_cuid__string(self):
        related_instance = RelatedCuidModel.objects.create(
            name="Blue Album", parent_id=str(self.instance_a.id)
        )
        assert isinstance(related_instance, RelatedCuidModel)
        assert related_instance.parent == self.instance_a
        assert (
            RelatedCuidModel.objects.get(parent=str(self.instance_a.id))
            == related_instance
        )

    def test_dumpdata(self):
        out = StringIO()
        call_command("dumpdata", "tests.CuidModel", stdout=out)
        output_json = out.getvalue()
        output = json.loads(output_json)

        assert output == [
            {
                "model": "tests.cuidmodel",
                "pk": str(self.instance_a.id),
                "fields": {
                    "name": "Instance A",
                    "default_cuid": str(self.instance_a.default_cuid),
                    "literal_prefixed_cuid": str(self.instance_a.literal_prefixed_cuid),
                    "literal_prefixed_cuid_with_custom_default": str(
                        self.instance_a.literal_prefixed_cuid_with_custom_default
                    ),
                    "callable_prefixed_cuid": str(
                        self.instance_a.callable_prefixed_cuid
                    ),
                    "nullable_cuid_with_no_default": None,
                    "no_index_cuid": str(self.instance_a.no_index_cuid),
                },
            },
            {
                "model": "tests.cuidmodel",
                "pk": str(self.instance_b.id),
                "fields": {
                    "name": "Instance B",
                    "default_cuid": str(self.instance_b.default_cuid),
                    "literal_prefixed_cuid": str(self.instance_b.literal_prefixed_cuid),
                    "literal_prefixed_cuid_with_custom_default": str(
                        self.instance_b.literal_prefixed_cuid_with_custom_default
                    ),
                    "callable_prefixed_cuid": str(
                        self.instance_b.callable_prefixed_cuid
                    ),
                    "nullable_cuid_with_no_default": None,
                    "no_index_cuid": str(self.instance_b.no_index_cuid),
                },
            },
        ]

    def test_loaddata__with_valid_input(self):
        out = StringIO()
        call_command("loaddata", "cuidmodels_valid", stdout=out)
        assert out.getvalue().strip() == "Installed 2 object(s) from 1 fixture(s)"
        instance_a = CuidModel.objects.get(pk="ckp6tebm500001k685ppzonod")
        instance_b = CuidModel.objects.get(pk="ckp6tebm600061k68mrl86aei")
        assert instance_a.name == "Instance A"
        assert instance_b.name == "Instance B"

    def test_loaddata__with_invalid_input(self):
        """
        Ensure that data that doesn't pass field validation fails to import.
        In particular, if a different key prefix is expected, ensure it raises.
        """
        out = StringIO()
        with pytest.raises(DeserializationError):
            call_command("loaddata", "cuidmodels_invalid", stdout=out)

        # Ensure neither entity were inserted, even though only Instance B is invalid.
        instance_a = CuidModel.objects.filter(pk="ckp6tebm500001k685ppzonod").first()
        assert instance_a is None
        instance_b = CuidModel.objects.filter(pk="ckp6tebm600061k68mrl86aei").first()
        assert instance_b is None
