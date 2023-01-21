from django import forms
from .models import Item

# from django.db.models import Min, Max


class YearForm(forms.Form):
    # min_year = Item.objects.all().aggregate(Min("date"))["date__min"].year
    # max_year = Item.objects.all().aggregate(Max("date"))["date__max"].year
    year_guess = forms.IntegerField(
        label="Year:",
        min_value=Item.min_year(),
        max_value=Item.max_year(),
    )
