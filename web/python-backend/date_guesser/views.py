from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from .models import Item

def items(request):
    """
    Show all available items.
    """
    
    context = {"item_list": Item.objects.all()}
    return render(request, "date_guesser/items.html", context)

def show(request, item_id: str):
    """
    Show an image and let the user guess the appropriate date.
    """
    context = {"item": Item.objects.get(pk=item_id)}
    return render(request, "date_guesser/show.html", context)

def tell(request):
    """
    Tell the user the answer.
    """
    pass