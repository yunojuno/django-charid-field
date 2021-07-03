from django import forms

from tests.models import IDModel


class PrefixedIDForm(forms.ModelForm):
    class Meta:
        model = IDModel
        fields = ("name", "prefixed_id")


class NullableIDForm(forms.ModelForm):
    class Meta:
        model = IDModel
        fields = ("name", "null_id_with_no_default")
