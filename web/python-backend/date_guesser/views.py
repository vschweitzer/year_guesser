import random

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader
from .models import Item
from .forms import YearForm

def items(request):
    """
    Show all available items.
    """
    
    items = Item.objects.all().filter(skip=False)
    context = {"item_list": items}
    return render(request, "date_guesser/items.html", context)

def show(request, item_id: str):
    """
    Show an image and let the user guess the appropriate date or show their guess result.
    """

    if request.method == "POST":
        is_result = True
        year_form = YearForm(request.POST)
    else:
        is_result = False
        year_form = YearForm()

    item = Item.objects.get(pk=item_id)
    context = {
        "item": item,
        "citation": item.citation_set.filter(style="apa").first().citation,
        "min_year": Item.min_year(),
        "max_year": Item.max_year(),
        "year_form": year_form,
        "is_result": is_result,
    }
    if is_result:
        context["is_valid"] = year_form.is_valid(),
        context["actual_year"] = item.date.year
        context["guessed_year"] = request.POST["year_guess"]
        if context["is_valid"]:
            context["off_by"] = abs(int(context["guessed_year"]) - int(context["actual_year"]))
            context["year_form"] = year_form.cleaned_data

    return render(request, "date_guesser/show.html", context)

def show_form(request):
    if request.method == "POST":
        data = request.POST
    elif request.method == "GET":
        data = request.GET
    else:
        raise ValueError("Invalid method")

    context = {
        "form_data": data
    }
    return render(request, "date_guesser/form_shower.html", context)

def random_image(request):
    random_item = random.choice(Item.objects.all().filter(skip=False).exclude(date_raw__startswith="Documentation compiled after"))
    return redirect(random_item)