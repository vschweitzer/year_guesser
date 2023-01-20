import hashlib
import typing
import os

from django.core.exceptions import ObjectDoesNotExist
from date_guesser.models import (
    Item,
    Stats,
    Image,
    Collection,
    Citation,
    Provider,
    License,
)
from django.db import models


def get_item_pk(
    item_id: str,
    page: typing.Optional[int] = None,
    image_url: typing.Optional[str] = None,
    hasher=hashlib.sha256,
):
    item_id = str(item_id)

    if not item_id:
        raise ValueError("Item id cannot be empty")

    if page is not None and image_url is not None:
        raise ValueError("Ambiguous identifiers")

    if page is not None:
        page = int(page)
        return hasher((item_id + "/" + str(page)).encode("utf-8")).hexdigest()
    elif image_url is not None:
        image_url = str(image_url)
        return hasher((item_id + "/" + image_url).encode("utf-8")).hexdigest()
    else:
        raise ValueError("Insufficient identifiers")


def add_item_and_related(
    item_id: str,
    item_dict: dict,
    provider_pk: str,
    citations: typing.Dict[str, str],  # style: citation
    collections: typing.List[str] = [],
    image_url: typing.Optional[str] = None,
    page: typing.Optional[int] = None,
    skip: bool = False,
    image_base_dir: str = "./images",
    image_file_ending: str = ".jpeg",
    license_pk: str = "cc0",
):
    to_save: list = []
    item_pk: str = get_item_pk(item_id=item_id, page=page, image_url=image_url)
    provider = Provider.objects.get(pk=provider_pk)
    if page is not None:
        page = int(page)

    i = add_item_if_not_exists(
        pk=item_pk,
        item_id=item_id,
        item_dict=item_dict,
        provider=provider,
        image_url=image_url,
        page=page,
        skip=skip,
    )

    if i is not None:
        i.save()

    for collection in collections:
        add_item_to_collection(collection, item_id)

    to_save.append(
        add_image_if_not_exists(
            item_pk,
            item_pk,
            base_dir=image_base_dir,
            ending=image_file_ending,
            license_pk=license_pk,
        )
    )
    to_save.append(add_stats_if_not_exist(item_pk))

    for style in citations:
        to_save.append(add_citation_if_not_exists(item_pk, style, citations[style]))

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


def add_item_if_not_exists(
    pk: str,
    item_id: str,
    item_dict: dict,
    provider: Provider,
    image_url: typing.Optional[str] = None,
    page: typing.Optional[int] = None,
    skip: bool = False,
):
    item_exists: bool = pk_exists(Item, pk)

    if not item_exists:
        i = Item.objects.create(
            id=pk,
            item=item_id,
            page=page,
            image_url=image_url,
            provider=provider,
            skip=skip,
            **item_dict,
        )
        return i
    else:
        return None


def add_collection_if_not_exists(collection_id: str):
    collection_exists: bool = pk_exists(Collection, collection_id)
    if not collection_exists:
        c = Collection.objects.create(collection=collection_id)
        return c
    else:
        return None


def add_image_if_not_exists(
    pk: str,
    item_key: str,
    base_dir: str = "./images",
    ending: str = ".jpeg",
    license_pk: str = "cc0",
):
    image_exists: bool = pk_exists(Image, pk)
    image_path: str = os.path.join(base_dir, pk + ending)
    license: License = License.objects.get(pk=license_pk)

    if not os.path.exists(image_path):
        raise FileNotFoundError(f'Image file at "{image_path}" does not exist')

    if not image_exists:
        item = Item.objects.get(pk=item_key)

        i = Image(item=item, image_id=pk, license=license)
        i.set_image(path=image_path, name=pk + ending)
        return i
    else:
        return None


def add_item_to_collection(collection_pk: str, item_pk: str):
    c = Collection.objects.get(pk=collection_pk)
    i = Item.objects.get(pk=item_pk)
    c.items.add(i)
    return None


def add_stats_if_not_exist(item_pk: str):
    stats_exist = pk_exists(Stats, item_pk)
    if not stats_exist:
        i = Item.objects.get(pk=item_pk)
        s = Stats(item=i)
        return s
    else:
        return None


def add_citation_if_not_exists(item_pk: str, style: str, citation: str):
    i = Item.objects.get(pk=item_pk)
    citation_exists: bool
    try:
        Citation.objects.get(item=item_pk, style=style)
        citation_exists = True
    except ObjectDoesNotExist as ex:
        citation_exists = False

    try:
        result = i.citation_set.filter(style=style)
        citation_exists = bool(result)
    except ObjectDoesNotExist as ex:
        print(ex)
        print("Dunno")

    if not citation_exists:
        c = Citation(item=i, style=style, citation=citation)
        return c
    else:
        print(f"Not adding {item_pk} - {style}")
        print(result)
        print(bool(result))
        return None
