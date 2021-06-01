import pytest

from cuidfield import Cuid

from .forms import PrefixedCuidForm, NullableCuidForm
from .models import CuidModel


@pytest.mark.django_db
class TestPrefixedCuidForm:
    def test_initial(self):
        instance_a = CuidModel.objects.create(
            name="Instance A",
            literal_prefixed_cuid="dev_ckp6tebm500001k685ppzonod",
        )
        form = PrefixedCuidForm(instance=instance_a)
        assert form.initial["literal_prefixed_cuid"] == Cuid(
            "dev_ckp6tebm500001k685ppzonod", prefix="dev_"
        )

    def test_create_success(self):
        assert CuidModel.objects.exists() is False
        form = PrefixedCuidForm(
            {
                "name": "Instance A",
                "literal_prefixed_cuid": "dev_ckp6tebm500001k685ppzonod",
            },
        )
        assert form.is_valid()
        instance = form.save()
        assert instance.literal_prefixed_cuid.prefix == "dev_"
        assert instance.literal_prefixed_cuid.cuid == "ckp6tebm500001k685ppzonod"
        assert instance.name == "Instance A - Edit"
        assert isinstance(instance.id, Cuid)
        assert CuidModel.objects.count() == 1

    def test_edit_success(self):
        instance_a = CuidModel.objects.create(
            name="Instance A",
            literal_prefixed_cuid="dev_ckpd1rrim000001jm8iijh07p",
        )
        form = PrefixedCuidForm(
            {
                "name": "Instance A - Edit",
                "literal_prefixed_cuid": "dev_ckp6tebm500001k685ppzonod",
            },
            instance=instance_a,
        )
        assert form.is_valid()
        instance = form.save()
        instance.refresh_from_db()
        assert instance.id == instance_a.id
        assert instance.literal_prefixed_cuid.prefix == "dev_"
        assert instance.literal_prefixed_cuid.cuid == "ckp6tebm500001k685ppzonod"
        assert instance.name == "Instance A - Edit"

    def test_invalid_prefix(self):
        form = PrefixedCuidForm(
            {
                "name": "Instance A",
                "literal_prefixed_cuid": "cus_ckp6tebm500001k685ppzonod",
            },
        )
        assert form.is_valid() is False
        assert "literal_prefixed_cuid" in form.errors

    def test_missing_field(self):
        form = PrefixedCuidForm(
            {
                "name": "Instance A",
                "literal_prefixed_cuid": "cus_ckp6tebm500001k685ppzonod",
            },
        )
        assert form.is_valid() is False
        assert "literal_prefixed_cuid" in form.errors

    def test_required_field(self):
        form = PrefixedCuidForm(
            {"name": "Instance A", "literal_prefixed_cuid": None},
        )
        assert form.is_valid() is False
        assert "literal_prefixed_cuid" in form.errors


@pytest.mark.django_db
class TestNullableCuidForm:
    def test_blank_allowed_on_creation(self):
        form = NullableCuidForm({"name": "Instance A"})
        assert form.is_valid()
        instance = form.save()
        instance.refresh_from_db()
        assert instance.nullable_cuid_with_no_default is None
