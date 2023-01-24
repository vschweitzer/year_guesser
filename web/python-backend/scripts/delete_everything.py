from django.db import models
import date_guesser.models


def run():
    classes: dict[str, models.Model] = dict(
        [
            (name, cls)
            for name, cls in date_guesser.models.__dict__.items()
            if isinstance(cls, type)
            and str(cls).startswith("<class 'date_guesser.models")
        ]
    )
    for n in classes:
        print(f"Deleting instances of {n}")
        try:
            classes[n].objects.all().delete()
        except Exception as ex:
            print(ex)
