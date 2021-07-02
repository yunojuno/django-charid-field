import pytest

from .forms import PrefixedIDForm, NullableIDForm
from .models import IDModel


@pytest.mark.django_db
class TestPrefixedIDForm:

    def test_initial__without_instance(self):
        form = PrefixedIDForm()
        assert form["prefixed_id"].value().startswith("dev_")

    def test_initial__with_instance(self):
        instance_a = IDModel.objects.create(
            name="Instance A",
            prefixed_id="dev_ckp6tebm500001k685ppzonod",
        )
        form = PrefixedIDForm(instance=instance_a)
        assert form.initial["prefixed_id"] == "dev_ckp6tebm500001k685ppzonod"
        assert form["prefixed_id"].value() == "dev_ckp6tebm500001k685ppzonod"

    def test_create_success(self):
        assert IDModel.objects.exists() is False
        form = PrefixedIDForm(
            {
                "name": "Instance A",
                "prefixed_id": "dev_ckp6tebm500001k685ppzonod",
            },
        )
        assert form.is_valid() is True, form.errors
        instance = form.save()
        assert instance.prefixed_id == "dev_ckp6tebm500001k685ppzonod"
        assert instance.name == "Instance A"
        assert isinstance(instance.id, str)
        assert IDModel.objects.count() == 1

    def test_edit_success(self):
        instance_a = IDModel.objects.create(
            name="Instance A",
            prefixed_id="dev_ckpd1rrim000001jm8iijh07p",
        )
        form = PrefixedIDForm(
            {
                "name": "Instance A - Edit",
                "prefixed_id": "dev_ckp6tebm500001k685ppzonod",
            },
            instance=instance_a,
        )
        assert form.is_valid() is True, form.errors
        instance = form.save()
        instance.refresh_from_db()
        assert instance.id == instance_a.id
        assert instance.prefixed_id == "dev_ckp6tebm500001k685ppzonod"
        assert instance.name == "Instance A - Edit"

    def test_missing_field(self):
        form = PrefixedIDForm(
            {
                "name": "Instance A",
            },
        )
        assert form.is_valid() is False
        assert len(form.errors) == 1
        assert "prefixed_id" in form.errors
        assert len(form.errors["prefixed_id"]) == 1
        assert form.errors["prefixed_id"][0] == "This field is required."

    def test_invalid_prefix(self):
        form = PrefixedIDForm(
            {
                "name": "Instance A",
                "prefixed_id": "cus_ckp6tebm500001k685ppzonod",
            },
        )
        assert form.is_valid() is False
        assert len(form.errors) == 1
        assert "prefixed_id" in form.errors
        assert len(form.errors["prefixed_id"]) == 1
        assert "requires the prefix “dev_”." in form.errors["prefixed_id"][0]

    def test_field_has_no_required_value(self):
        form = PrefixedIDForm(
            {"name": "Instance A", "prefixed_id": None},
        )
        assert form.is_valid() is False
        assert len(form.errors) == 1
        assert "prefixed_id" in form.errors
        assert len(form.errors["prefixed_id"]) == 1
        assert form.errors["prefixed_id"][0] == "This field is required."


@pytest.mark.django_db
class TestNullableIDForm:
    def test_blank_allowed_on_creation(self):
        form = NullableIDForm({"name": "Instance A"})
        assert form.is_valid()
        instance = form.save()
        instance.refresh_from_db()
        assert instance.nullable_id_with_no_default is None
