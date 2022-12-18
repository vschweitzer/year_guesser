import hashlib
import datetime
import json
import typing
import os

from django.core.exceptions import ObjectDoesNotExist
from date_guesser.models import Item, Citation

def skip_dracula():
    try:
        citations = Citation.objects.all().filter(citation__icontains="dracula")
    except ObjectDoesNotExist as ex:
        print("Could not find any item: {ex}")
        exit(0)

    print(f"Found {len(citations)} items.")

    for c in citations:
        print(c.item.id)
        c.item.skip = True
        c.item.save()

def run():
    skip_dracula()