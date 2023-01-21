import hashlib
import datetime
import json
import typing
import os

from django.core.exceptions import ObjectDoesNotExist
from date_guesser.models import Provider, License


def run():
    providers = [
        {
            "short_name": "wikidata",
            "long_name": "Wikidata",
            "url": "https://www.wikidata.org/",
        },
        {
            "short_name": "loc",
            "long_name": "Library of Congress",
            "url": "https://www.loc.gov/",
        },
    ]

    licenses = [
        {
            "short_name": "cc0",
            "long_name": "Creative Commons Zero",
        }
    ]

    for provider in providers:
        new = Provider(**provider)
        new.save()

    for license in licenses:
        new = License(**license)
        new.save()
