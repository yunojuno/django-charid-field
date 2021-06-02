from django import forms

from tests.models import IDModel


class PrefixedIDForm(forms.ModelForm):
    class Meta:
        model = IDModel
        fields = ("name", "literal_prefixed_id")


class NullableIDForm(forms.ModelForm):
    class Meta:
        model = IDModel
        fields = ("name", "nullable_id_with_no_default")
