import datetime

import pytest
from cuid import cuid as generate_cuid
from django.core import exceptions
from django.core.management import call_command
from django.shortcuts import get_object_or_404
from django.test import TestCase, override_settings
from io import StringIO
from pytest_django.asserts import assertJSONEqual

from cuidfield import is_valid_cuid, Cuid, generate_cuid_string
from .models import (
    CuidModel,
    RelatedCuidModel,
)


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
        assert isinstance(self.instance_a.nullable_cuid_with_no_default, Cuid)
        assert isinstance(self.instance_a.no_index_cuid, Cuid)

        assert is_valid_cuid(str(self.instance_a.id)) is True
        assert is_valid_cuid(str(self.instance_a.default_cuid)) is True
        assert is_valid_cuid(str(self.instance_a.literal_prefixed_cuid)) is False
        assert is_valid_cuid(str(self.instance_a.callable_prefixed_cuid)) is True
        assert self.instance_a.nullable_cuid_with_no_default is None
        assert is_valid_cuid(str(self.instance_a.no_index_cuid)) is True

    def test_ordering_by_id(self):
        asc_queryset = CuidModel.objects.all().order_by('id')
        assert list(asc_queryset) == [self.instance_a, self.instance_b]
        desc_queryset = CuidModel.objects.all().order_by('id')
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

    @pytest.mark.parametrize("field, lookup_field", (
        ("id", "id"),
        ("id", "pk"),
        ("default_cuid", "default_cuid"),
        ("literal_prefixed_cuid", "literal_prefixed_cuid"),
        ("callable_prefixed_cuid", "callable_prefixed_cuid"),
        ("nullable_cuid_with_no_default", "nullable_cuid_with_no_default"),
        ("no_index_cuid", "no_index_cuid"),
    ))
    def test_lookups__with_cuid_object(self, field, lookup_field):
        lookup_value = getattr(self.instance_a, field)
        self._assert_lookups(field, lookup_field, lookup_value)

    @pytest.mark.parametrize("field, lookup_field", (
        ("id", "id"),
        ("id", "pk"),
        ("default_cuid", "default_cuid"),
        ("literal_prefixed_cuid", "literal_prefixed_cuid"),
        ("callable_prefixed_cuid", "callable_prefixed_cuid"),
        ("nullable_cuid_with_no_default", "nullable_cuid_with_no_default"),
        ("no_index_cuid", "no_index_cuid"),
    ))
    def test_get_lookup__with_string(self, field, lookup_field):
        # Apply str() to get the stringified version of the
        # prefixable Cuid object.
        lookup_value = str(getattr(self.instance_a, field))
        self._assert_lookups(field, lookup_field, lookup_value)

    def _assert_lookups(self, field, lookup_field, lookup_value):
        # Test QuerySet.get
        lookup_filter = {lookup_field: lookup_value}
        instance = CuidModel.objects.get(**lookup_filter)
        assert instance == self.instance_a

        # Test QuerySet.filter exact (implicit)
        lookup_filter = {lookup_field: lookup_value}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

        # Test QuerySet.filter exact (explicit)
        lookup_filter = {f"{lookup_field}__exact": lookup_value}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

        # Test QuerySet.filter iexact
        lookup_filter = {f"{lookup_field}__iexact": lookup_value}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

        # Test QuerySet.filter contains
        lookup_filter = {f"{lookup_field}__contains": lookup_value}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

        # Test QuerySet.filter icontains
        lookup_filter = {f"{lookup_field}__icontains": lookup_value}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

        # Test Queryset.filter __in
        lookup_filter = {f"{lookup_field}__in": [lookup_value]}
        queryset = CuidModel.objects.filter(**lookup_filter)
        assert list(queryset) == [self.instance_a]

    def test_lookups__subqueries(self):
        a = CuidModel.objects.create(name="Record A")
        b = CuidModel.objects.create(name="Record B")
        CuidModel.objects.create(name="Record C")
        queryset = CuidModel.objects.filter(name__icontains="Record").order_by("name")[:2]
        assert len(queryset) == 2
        assert list(queryset) == [a, b]

        subquery_lookup = CuidModel.objects.filter(id__in=queryset.values('id'))
        assert len(subquery_lookup) == 2
        assert list(subquery_lookup) == [a, b]

    def test_lookups__isnull(self):
        assert CuidModel.objects.filter(nullable_cuid_with_no_default__isnull=True).count() == 2
        assert CuidModel.objects.filter(id__isnull=False).count() == 2

    def test_lookups__gt_lt(self):
        a = CuidModel.objects.create(name="Record A")
        b = CuidModel.objects.create(name="Record B")
        c = CuidModel.objects.create(name="Record C")
        queryset = CuidModel.objects.filter(name__icontains="Record")

        gt_queryset = queryset.objects.filter(id__gt=b.id)
        assert list(gt_queryset) == [c]

        lt_queryset = queryset.filter(id__lt=b.id)
        assert list(lt_queryset) == [a]

        gte_queryset = queryset.filter(id__gte=b.id)
        assert list(gte_queryset) == [b, c]

        lte_queryset = queryset.filter(id__lte=b.id)
        assert list(lte_queryset) == [a, b]

    def test_get_or_create(self):
        instance, created = CuidModel.objects.get_or_create(name="Instance A")
        assert isinstance(instance, CuidModel)
        assert instance.id == self.instance_a.id
        assert created is False

        instance, created = CuidModel.objects.get_or_create(name="Instance D")
        assert isinstance(instance, CuidModel)
        assert created is True

    @pytest.mark.parametrize("field", (
        "id",
        "default_cuid",
        "literal_prefixed_cuid",
        "callable_prefixed_cuid",
        "nullable_cuid_with_no_default",
        "no_index_cuid",
    ))
    def test_setting__as_a_string(self, field):
        old_cuid = getattr(self.instance_a, field)
        new_cuid_string = f"{old_cuid.prefix}{generate_cuid()}"
        setattr(self.instance_a, field, new_cuid_string)
        new_cuid = getattr(self.instance_a, field)
        assert isinstance(new_cuid, Cuid)
        assert new_cuid != old_cuid
        assert new_cuid.prefix == old_cuid.prefix
        assert is_valid_cuid(new_cuid.cuid)

        # & test persistance & retrieval.
        self.instance_a.save()
        self.instance_a.refresh_from_db()
        assert getattr(self.instance_a, field) == new_cuid
        assert CuidModel.objects.filter({field: old_cuid}).exists() is False
        assert CuidModel.objects.filter({field: new_cuid}).exists() is True

    @pytest.mark.parametrize("field", (
        "id",
        "default_cuid",
        "literal_prefixed_cuid",
        "callable_prefixed_cuid",
        "nullable_cuid_with_no_default",
        "no_index_cuid",
    ))
    def test_setting__as_a_cuid(self, field):
        old_cuid = getattr(self.instance_a, field)
        new_cuid_string = generate_cuid_string(prefix=old_cuid.prefix)
        new_cuid = Cuid(new_cuid_string, prefix=old_cuid.prefix)
        setattr(self.instance_a, field, new_cuid)
        set_cuid = getattr(self.instance_a, field)
        assert isinstance(set_cuid, Cuid)
        assert is_valid_cuid(set_cuid.cuid)

        # Check retrieved against old cuid.
        assert set_cuid != old_cuid
        assert set_cuid.cuid != old_cuid.cuid
        assert set_cuid.prefix == old_cuid.prefix

        # Check retrieved against new cuid.
        assert set_cuid == new_cuid
        assert set_cuid.cuid == new_cuid.cuid
        assert set_cuid.prefix == new_cuid.prefix

        # & test persistance & retrieval.
        self.instance_a.save()
        self.instance_a.refresh_from_db()
        assert getattr(self.instance_a, field) == new_cuid
        assert CuidModel.objects.filter(**{field: old_cuid}).exists() is False
        assert CuidModel.objects.filter(**{field: new_cuid}).exists() is True

    def test_setting__inner_cuid_fields_are_immutable(self):
        with pytest.raises(ValueError):
            self.instance_a.id.cuid = "fail"

        with pytest.raises(ValueError):
            self.instance_a.id.prefix = "fail"

    @pytest.mark.parametrize("value", [
        1,
        -1,
        datetime.datetime(2020, 1, 1, 12, 30),
        datetime.date(2020, 1, 1),
    ])
    def test_setting__invalid_values(self, value):
        with pytest.raises(ValueError):
            self.instance_a.id = value

    def test_foreign_key__with_parent_model_instance(self):
        related_instance = RelatedCuidModel.objects.create(name="Blue Album", parent=self.instance_a)
        assert isinstance(related_instance, RelatedCuidModel)
        assert related_instance.parent == self.instance_a
        assert RelatedCuidModel.objects.get(parent=self.instance_a) == related_instance

    def test_foreign_key__with_parent_model_cuid(self):
        related_instance = RelatedCuidModel.objects.create(name="Blue Album", parent=self.instance_a.id)
        assert isinstance(related_instance, RelatedCuidModel)
        assert related_instance.parent == self.instance_a
        assert RelatedCuidModel.objects.get(parent=self.instance_a.id) == related_instance

    def test_foreign_key__with_parent_model_cuid_string(self):
        related_instance = RelatedCuidModel.objects.create(name="Blue Album", parent=str(self.instance_a.id))
        assert isinstance(related_instance, RelatedCuidModel)
        assert related_instance.parent == self.instance_a
        assert RelatedCuidModel.objects.get(parent=str(self.instance_a.id)) == related_instance

    def test_dumpdata(self):
        out = StringIO()
        call_command("dumpdata", "tests.CuidModel", stdout=out)
        print("dumpdata out", out.getvalue())
        assertJSONEqual(out.getvalue(), """
            [
                {
                    "model": "tests.record",
                    "pk": "Yd3axGx",
                    "fields": {
                        "name": "Test Record",
                        "artist": null,
                        "reference_id": "M3Ka6wW",
                        "prefixed_id": "prefix_2PEK0G5",
                        "string_id": "d3aqj3x",
                        "plain_hashid": "9wXZ03N",
                        "plain_id": "M3K9XwW",
                        "alternate_id": null,
                        "key": "8wx9yyv39o"
                    }
                },
                {
                    "model": "tests.record",
                    "pk": "gVGO031",
                    "fields": {
                        "name": "Blue Album",
                        "artist": "bMrZ5lYd3axGxpW72Vo0",
                        "reference_id": "9wXZ03N",
                        "prefixed_id": null,
                        "string_id": null,
                        "plain_hashid": null,
                        "plain_id": null,
                        "alternate_id": null,
                        "key": null
                    }
                }
            ]
        """)

    def test_loaddata(self):
        out = StringIO()
        call_command("loaddata", "artists", stdout=out)
        self.assertEqual(out.getvalue().strip(), "Installed 2 object(s) from 1 fixture(s)")
        self.assertEqual(Artist.objects.get(pk='bMrZ5lYd3axGxpW72Vo0').name, "John Doe")
        self.assertEqual(Artist.objects.get(pk="Ka0MzjgVGO031r5ybWkJ").name, "Jane Doe")

# TODO(pr) Many more tests needs to come surrounding:
# * lookup filtering
# * persistence
# * nullablity
# * indexing
# * use as a foreignkey (related)

# class HashidsTests(TestCase):
#     def setUp(self):
#         self.record = Record.objects.create(name="Test Record", reference_id=123, prefixed_id=234,
#                                             string_id=345, plain_hashid=456, plain_id=567, key=234)
#         self.record.refresh_from_db()
#         self.ref_hashids = self.record.reference_id._hashids
#
#     @override_settings(HASHID_FIELD_LOOKUP_EXCEPTION=True)
#     def test_exceptions(self):
#         a = Artist.objects.create(name="John Doe")
#         r = Record.objects.create(name="Blue Album", reference_id=123, artist=a, key=456)
#         self.assertTrue(Record.objects.filter(key=str(r.key)).exists())
#         self.assertTrue(Record.objects.filter(key__in=[str(r.key)]).exists())
#         with self.assertRaises(ValueError):
#             self.assertFalse(Record.objects.filter(key=404).exists())
#         with self.assertRaises(ValueError):
#             self.assertFalse(Record.objects.filter(key="invalid").exists())
#         with self.assertRaises(ValueError):
#             self.assertFalse(Record.objects.filter(key__in=[404]).exists())
#         self.assertTrue(Record.objects.filter(artist=a).exists())
#         self.assertTrue(Record.objects.filter(artist_id=a.id).exists())
#         self.assertTrue(Record.objects.filter(artist__in=[a]).exists())
#         self.assertTrue(Record.objects.filter(artist_id__in=[a.id]).exists())
#         self.assertFalse(Record.objects.filter(artist_id=404).exists())
#         with self.assertRaises(ValueError):
#             self.assertFalse(Record.objects.filter(artist_id="invalid").exists())
#         self.assertFalse(Record.objects.filter(artist_id__in=[404]).exists())
#
# class FormTests(TestCase):
#     def setUp(self):
#         self.record = Record.objects.create(name="Test Record", reference_id=123, prefixed_id=234,
#                                             string_id=345, plain_hashid=456, plain_id=567, key=234)
#         self.record.refresh_from_db()
#         self.ref_hashids = self.record.reference_id._hashids
#
#     def test_record_form(self):
#         form = RecordForm(instance=self.record)
#         self.assertEqual(form.initial['reference_id'].hashid, self.ref_hashids.encode(123))
#         form = RecordForm({'name': "A new name", 'reference_id': 987, 'prefixed_id': 987}, instance=self.record)
#         self.assertTrue(form.is_valid())
#         instance = form.save()
#         self.assertEqual(self.record, instance)
#         self.assertEqual(str(self.record.reference_id), self.ref_hashids.encode(987))
#         self.assertEqual(str(self.record.prefixed_id), "prefix_" + self.ref_hashids.encode(987))
#
#     def test_invalid_id_in_form(self):
#         form = RecordForm({'name': "A new name", 'reference_id': "asdfqwer"})
#         self.assertFalse(form.is_valid())
#         self.assertIn('reference_id', form.errors)
#
#     def test_negative_int_in_form(self):
#         form = RecordForm({'name': "A new name", 'reference_id': -5})
#         self.assertFalse(form.is_valid())
#         self.assertIn('reference_id', form.errors)
#
#     def test_int_in_form(self):
#         form = RecordForm({'name': "A new name", 'reference_id': 42})
#         self.assertTrue(form.is_valid())
#