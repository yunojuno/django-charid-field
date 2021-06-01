from django import forms

from tests.models import CuidModel


class PrefixedCuidForm(forms.ModelForm):
    class Meta:
        model = CuidModel
        fields = ("name", "literal_prefixed_cuid")


class NullableCuidForm(forms.ModelForm):
    class Meta:
        model = CuidModel
        fields = ("name", "nullable_cuid_with_no_default")
