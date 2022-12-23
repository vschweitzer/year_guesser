import hashlib
import datetime
import json
import typing
import os

from django.core.exceptions import ObjectDoesNotExist
from date_guesser.models import Item, Stats, Image, Collection, Citation

def load_from_json(path: str):
    input_dict: dict
    
    with open(path, "r") as json_file:
        input_dict = json.load(json_file)
    
    for collection_index in input_dict:
        collection: str = collection_index.strip("/")
        add_collection_if_not_exists(collection)

        for item_index in input_dict[collection_index]:
            item: str = item_index.strip("/")
            skip = item.endswith("sheet") or item.endswith("sheets")
            for page_index in input_dict[collection_index][item_index]:
                page = int(page_index)
                
                add_item_and_related(item, page, input_dict[collection_index][item_index][page_index], [collection], skip=skip)

def add_item_and_related(
    item: str, page: int, item_dict: dict, collections: list = [], provider: str = "smithsonian", skip: bool = False
):
    to_save: list = []
    hasher = hashlib.sha256
    
    item_id = hasher((item + "/" + str(page)).encode("utf-8")).hexdigest()
    #print(item_id)
    to_save.append(add_item_if_not_exists(item_id, item, page, item_dict, provider=provider, skip=skip))
    for collection in collections:
        add_item_to_collection(collection, item_id)

    to_save.append(add_image_if_not_exists(item_id, item_id))
    to_save.append(add_stats_if_not_exist(item_id))

    for style in item_dict["cite_this"]:
        to_save.append(add_citation_if_not_exists(item_id, style, item_dict["cite_this"][style]))

    for saveable in to_save:
        if saveable is not None:
            print(f"Saving {saveable.item}")
            saveable.save()

def pk_exists(object, pk) -> bool:
    try:
        object.objects.get(pk=pk)
        return True
    except ObjectDoesNotExist:
        return False

def add_item_if_not_exists(item_id: str, item: str, page: int, item_dict: dict, provider: str = "smithsonian", skip: bool = False):
    item = item.strip("/")
    page = int(page)
    date: datetime.datetime = datetime.datetime.fromisoformat(item_dict["date"])
    date_raw: str = item_dict["date_raw"]

    item_exists: bool = pk_exists(Item, item_id)
    
    if not item_exists:
        i = Item.objects.create(
            id = item_id,
            item = item_id, 
            page = page,
            provider = provider,
            date = date,
            date_raw = date_raw,
            skip = skip,
        )
        return i
    else:
        return None

def add_collection_if_not_exists(collection_id: str):
    collection_exists: bool = pk_exists(Collection, collection_id)
    if not collection_exists:
        c = Collection.objects.create(
            collection = collection_id
        )
        return c
    else:
        return None

def add_image_if_not_exists(image_id: str, item_key: str, base_dir: str = "./images", ending: str = ".jpeg", license: str = "CC0"):
    image_exists: bool = pk_exists(Image, image_id)
    image_path: str = os.path.join(base_dir, image_id + ending)

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file at \"{image_path}\" does not exist")

    if not image_exists:
        item = Item.objects.get(pk=item_key)

        i = Image(
            item = item,
            image_id = image_id,
            license = license
        )
        i.set_image(path=image_path, name=image_id + ending)
        return i
    else:
        return None

def add_item_to_collection(collection_id: str, item_id: str):
    c = Collection.objects.get(pk=collection_id)
    i = Item.objects.get(pk=item_id)
    c.items.add(i)
    return None

def add_stats_if_not_exist(item_id: str):
    stats_exist = pk_exists(Stats, item_id)
    if not stats_exist:
        i = Item.objects.get(pk = item_id)
        s = Stats(
            item = i
        )
        return s
    else:
        return None

def add_citation_if_not_exists(item_id: str, style: str, citation: str):
    i = Item.objects.get(pk=item_id)
    citation_exists: bool = False
    try:
        result = i.citation_set.filter(style=style)
        citation_exists = bool(result)
    except ObjectDoesNotExist as ex:
        print(ex)
        print("Dunno")
    
    if not citation_exists:
        c = Citation(
            item = i,
            style = style,
            citation = citation
        )
        #print(c.item)
        c.save()
        return None
    else:
        print(f"Not adding {item_id} - {style}")
        print(result)
        print(bool(result))
        return None

def run():
    input_path: str = "./images.json"
    load_from_json(input_path)

