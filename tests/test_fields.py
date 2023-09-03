import json
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.serializers.base import DeserializationError
from django.http import Http404
from django.shortcuts import get_object_or_404

from .models import IDModel, RelatedIDModel
from .helpers import TEST_UID_REGEX, generate_test_uid


@pytest.mark.django_db
class TestIDModel:
    def setup_method(self):
        # The main entity tests will be carried out against.
        self.instance_a = IDModel.objects.create(name="Instance A")
        # Extra entities to ensure lookup/ordering tests are safe.
        self.instance_b = IDModel.objects.create(name="Instance B")

    def test_creation_types_and_basic_values(self):
        assert isinstance(self.instance_a, IDModel)

        assert isinstance(self.instance_a.id, str)
        assert isinstance(self.instance_a.default_id, str)
        assert isinstance(self.instance_a.prefixed_id, str)
        assert self.instance_a.null_id_with_no_default is None
        assert self.instance_a.not_null_id_but_blank == ""
        assert isinstance(self.instance_a.no_index_id, str)
        assert isinstance(self.instance_a.prefixed_and_non_callable_default_id, str)

        assert TEST_UID_REGEX.match(self.instance_a.id)
        assert TEST_UID_REGEX.match(self.instance_a.default_id)
        assert TEST_UID_REGEX.match(self.instance_a.prefixed_id)
        assert TEST_UID_REGEX.match(self.instance_a.no_index_id)

        assert self.instance_a.prefixed_id.startswith("dev_")
        assert self.instance_a.prefixed_and_non_callable_default_id == "test_abcde"

    def test_ordering_by_id(self):
        asc_queryset = IDModel.objects.all().order_by("id")
        assert list(asc_queryset) == [self.instance_a, self.instance_b]
        desc_queryset = IDModel.objects.all().order_by("-id")
        assert list(desc_queryset) == [self.instance_b, self.instance_a]

    def test_no_collision_amongst_same_model_fields(self):
        # This is obviously not a collision-resistance test; but rather
        # one to ensure that defining two IDfields on the same model
        # never results in weird cross-contamination of defaults.
        assert (
            len(
                set(
                    [
                        self.instance_a.id,
                        self.instance_a.default_id,
                        self.instance_a.prefixed_id,
                        self.instance_a.null_id_with_no_default,
                        self.instance_a.no_index_id,
                        self.instance_a.prefixed_and_non_callable_default_id,
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
            ("default_id", "default_id"),
            ("prefixed_id", "prefixed_id"),
            ("no_index_id", "no_index_id"),
        ),
    )
    def test_get_lookup(self, model_field_name, lookup_field_name):
        lookup_value = getattr(self.instance_a, model_field_name)

        # Test QuerySet.get
        lookup_filter = {lookup_field_name: lookup_value}
        instance = IDModel.objects.get(**lookup_filter)
        assert instance == self.instance_a

        # Test QuerySet.filter exact (implicit)
        lookup_filter = {lookup_field_name: lookup_value}
        queryset = IDModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

        # Test QuerySet.filter exact (explicit)
        lookup_filter = {f"{lookup_field_name}__exact": lookup_value}
        queryset = IDModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

        # Test QuerySet.filter iexact
        lookup_filter = {f"{lookup_field_name}__iexact": lookup_value}
        queryset = IDModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

        # Test QuerySet.filter contains
        lookup_filter = {f"{lookup_field_name}__contains": lookup_value}
        queryset = IDModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

        # Test QuerySet.filter icontains
        lookup_filter = {f"{lookup_field_name}__icontains": lookup_value}
        queryset = IDModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

        # Test Queryset.filter __in
        lookup_filter = {f"{lookup_field_name}__in": [lookup_value]}
        queryset = IDModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

    def test_lookups__with_empty_string(self):
        qs = IDModel.objects.filter(not_null_id_but_blank="")
        assert list(qs) == [self.instance_a, self.instance_b]

    def test_lookups__with_none(self):
        qs = IDModel.objects.filter(null_id_with_no_default=None)
        assert list(qs) == [self.instance_a, self.instance_b]

    def test_lookups__subqueries(self):
        a = IDModel.objects.create(name="Record A")
        b = IDModel.objects.create(name="Record B")
        IDModel.objects.create(name="Record C")
        queryset = IDModel.objects.filter(name__icontains="Record").order_by("name")[:2]
        assert len(queryset) == 2
        assert list(queryset) == [a, b]

        subquery_lookup = IDModel.objects.filter(id__in=queryset.values("id"))
        assert len(subquery_lookup) == 2
        assert list(subquery_lookup) == [a, b]

    def test_lookups__values(self):
        values_qs = IDModel.objects.values("id")
        assert list(values_qs) == [
            {"id": self.instance_a.id},
            {"id": self.instance_b.id},
        ]

    def test_lookups__values_list(self):
        values_list_qs = IDModel.objects.values_list("id", flat=True)
        assert list(values_list_qs) == [
            self.instance_a.id,
            self.instance_b.id,
        ]

    def test_lookups__isnull(self):
        assert IDModel.objects.filter(null_id_with_no_default__isnull=True).count() == 2
        assert IDModel.objects.filter(id__isnull=False).count() == 2

    def test_lookups__gt_lt(self):
        a = IDModel.objects.create(name="Record A")
        b = IDModel.objects.create(name="Record B")
        c = IDModel.objects.create(name="Record C")
        base_queryset = IDModel.objects.filter(name__icontains="Record")

        gt_queryset = base_queryset.filter(id__gt=b.id).order_by("id")
        assert list(gt_queryset) == [c]

        lt_queryset = base_queryset.filter(id__lt=b.id).order_by("id")
        assert list(lt_queryset) == [a]

        gte_queryset = base_queryset.filter(id__gte=b.id).order_by("id")
        assert list(gte_queryset) == [b, c]

        lte_queryset = base_queryset.filter(id__lte=b.id).order_by("id")
        assert list(lte_queryset) == [a, b]

    def test_get_or_create(self):
        instance, created = IDModel.objects.get_or_create(name="Instance A")
        assert isinstance(instance, IDModel)
        assert instance.id == self.instance_a.id
        assert created is False

        instance, created = IDModel.objects.get_or_create(name="Instance D")
        assert isinstance(instance, IDModel)
        # Ensure only one can be returned.
        assert IDModel.objects.get(id=instance.id)
        assert created is True

    def test_get_object_or_404__when_found__no_prefix(self):
        instance_a = get_object_or_404(IDModel, id=self.instance_a.id)
        assert instance_a == self.instance_a

    def test_get_object_or_404__when_not_found__no_prefix(self):
        with pytest.raises(Http404):
            get_object_or_404(IDModel, id="does_not_exist")

    def test_get_object_or_404__when_found__with_prefix(self):
        instance_a = get_object_or_404(IDModel, prefixed_id=self.instance_a.prefixed_id)
        assert instance_a == self.instance_a

    def test_get_object_or_404__when_not_found__with_prefix(self):
        with pytest.raises(Http404):
            get_object_or_404(IDModel, prefixed_id="does_not_exist")

    def test_setting_primary_key(self):
        old_id = self.instance_a.id
        self.instance_a.id = generate_test_uid()
        new_id = self.instance_a.id
        assert isinstance(new_id, str)
        assert new_id != old_id

        # Test persistance & retrieval; because we are changing the primary
        # key and re-saving we should expect a brand new object to be created
        # but the old one should be left alone. Because it is left alone, we
        # must cycle the id fields with a unique index, as otherwise the new
        # object will not persist.
        self.instance_a.default_id = generate_test_uid()
        self.instance_a.prefixed_id = generate_test_uid(prefix="dev_")
        self.instance_a.unique_id = generate_test_uid()
        self.instance_a.save()
        self.instance_a.refresh_from_db()
        assert self.instance_a.id == new_id
        assert IDModel.objects.filter(id=old_id).count() == 1
        assert IDModel.objects.filter(id=new_id).count() == 1

    @pytest.mark.parametrize(
        "model_field_name",
        (
            "default_id",
            "prefixed_id",
            "null_id_with_no_default",
            "no_index_id",
        ),
    )
    def test_setting_non_primary_key(self, model_field_name):
        old_id = getattr(self.instance_a, model_field_name)
        field = self.instance_a._meta.get_field(model_field_name)
        new_id_string = f"{field.prefix}{generate_test_uid()}"
        setattr(self.instance_a, model_field_name, new_id_string)
        new_id = getattr(self.instance_a, model_field_name)
        assert isinstance(new_id, str)
        assert new_id != old_id
        assert new_id.startswith(field.prefix) is True

        # Test persistance & retrieval; because we are settings non-primary key
        # values we would expect the mutation to occur on the existing entity.
        self.instance_a.save()
        self.instance_a.refresh_from_db()
        assert getattr(self.instance_a, model_field_name) == new_id
        assert IDModel.objects.filter(**{model_field_name: new_id}).count() == 1
        if old_id:
            assert IDModel.objects.filter(**{model_field_name: old_id}).count() == 0

    @pytest.mark.parametrize(
        "model_field_name, expected",
        (
            ("id", True),
            ("unique_id", True),
            ("default_id", False),
            ("prefixed_id", False),
            ("null_id_with_no_default", False),
            ("not_null_id_but_blank", False),
            ("no_index_id", False),
            ("prefixed_and_non_callable_default_id", False),
        ),
    )
    def test_unique_set_default(self, model_field_name, expected):
        field = self.instance_a._meta.get_field(model_field_name)
        assert field.unique is expected

    def test_foreign_key__with_parent_model__instance(self):
        related_instance = RelatedIDModel.objects.create(
            name="Blue Album", parent=self.instance_a
        )
        assert isinstance(related_instance, RelatedIDModel)
        assert related_instance.parent == self.instance_a
        assert RelatedIDModel.objects.get(parent=self.instance_a) == related_instance

    def test_foreign_key__with_parent_model__string(self):
        related_instance = RelatedIDModel.objects.create(
            name="Blue Album", parent_id=self.instance_a.id
        )
        assert isinstance(related_instance, RelatedIDModel)
        assert related_instance.parent == self.instance_a
        assert RelatedIDModel.objects.get(parent=self.instance_a.id) == related_instance

    def test_dumpdata(self):
        out = StringIO()
        call_command("dumpdata", "tests.IDModel", stdout=out)
        output_json = out.getvalue()
        output = json.loads(output_json)

        assert output == [
            {
                "model": "tests.idmodel",
                "pk": self.instance_a.id,
                "fields": {
                    "name": "Instance A",
                    "default_id": self.instance_a.default_id,
                    "prefixed_id": self.instance_a.prefixed_id,
                    "null_id_with_no_default": None,
                    "not_null_id_but_blank": "",
                    "no_index_id": self.instance_a.no_index_id,
                    "unique_id": self.instance_a.unique_id,
                    "prefixed_and_non_callable_default_id": "test_abcde",
                },
            },
            {
                "model": "tests.idmodel",
                "pk": self.instance_b.id,
                "fields": {
                    "name": "Instance B",
                    "default_id": self.instance_b.default_id,
                    "prefixed_id": self.instance_b.prefixed_id,
                    "null_id_with_no_default": None,
                    "not_null_id_but_blank": "",
                    "no_index_id": self.instance_b.no_index_id,
                    "unique_id": self.instance_b.unique_id,
                    "prefixed_and_non_callable_default_id": "test_abcde",
                },
            },
        ]

    def test_loaddata(self):
        out = StringIO()
        call_command("loaddata", "idmodels", stdout=out)
        assert out.getvalue().strip() == "Installed 2 object(s) from 1 fixture(s)"
        instance_a = IDModel.objects.get(pk="ckp6tebm500001k685ppzonod")
        instance_b = IDModel.objects.get(pk="ckp6tebm600061k68mrl86aei")
        assert instance_a.name == "Instance A"
        assert instance_b.name == "Instance B"
