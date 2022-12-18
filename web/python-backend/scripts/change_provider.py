from django.core.exceptions import ObjectDoesNotExist
from date_guesser.models import Item

def change_provider(provider, new_provider):
    try:
        items = Item.objects.all().filter(provider=provider)
    except ObjectDoesNotExist as ex:
        print(f"Could not find any item: {ex}")
        exit(0)

    print(f"Found {len(items)} items.")

    for i in items:
        print(i.id)
        i.provider = new_provider
        i.save()

def run():
    change_provider("smithsonian", "loc")