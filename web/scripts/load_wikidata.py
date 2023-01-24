# pip install sparqlwrapper
# https://rdflib.github.io/sparqlwrapper/

import sys
import datetime
import typing
import requests
import os
import urllib.parse
import pathlib

from . import date_guesser_operations

import PIL.Image
from SPARQLWrapper import SPARQLWrapper, JSON
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


def query_wikidata(offset: int = 0, limit: int = 50):
    endpoint_url = "https://query.wikidata.org/sparql"

    query = (
        """
    SELECT DISTINCT ?item ?pic ?itemLabel ?itemDescription ?itemAltLabel (GROUP_CONCAT(?authorLabel; SEPARATOR = ", ") AS ?authors) ?idate ?iprecision ?title WHERE {
      SELECT DISTINCT ?item ?pic ?itemLabel ?itemDescription ?itemAltLabel ?authorLabel ?idate ?iprecision ?title WHERE {
        ?item (wdt:P31/(wdt:P279*)) wd:Q125191;
        wdt:P6216 wd:Q19652;
        wdt:P18 ?pic;
        p:P571 ?inception.
        OPTIONAL { ?item wdt:P170 ?author_entry. }
        OPTIONAL { ?item wdt:P1476 ?title. }
        BIND(COALESCE(?author_entry, "unknown author") AS ?author)
        ?inception psv:P571 ?entry.
        ?entry wikibase:timeValue ?idate;
        wikibase:timePrecision ?iprecision.
        ?item wdt:P6216 wd:Q19652.
        ?inception rdf:type wikibase:BestRank.
        OPTIONAL { ?item wdt:P180 ?depicts. }
        FILTER(?iprecision >= 9 )
        FILTER((!(BOUND(?depicts))) || (NOT EXISTS {
        { ?item wdt:P180 wd:Q40446. }
        UNION
        { ?item (wdt:P180/(wdt:P279*)) wd:Q1931388. }
        UNION
        { ?item (wdt:P180/(wdt:P279*)) wd:Q2937981. }
        }))
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en,[AUTO_LANGUAGE]". }
      }
    }
    GROUP BY ?item ?pic ?itemLabel ?itemDescription ?itemAltLabel ?idate ?iprecision ?title
    ORDER BY (?item)
    OFFSET """
        + str(offset)
        + """
    LIMIT"""
        + str(limit)
        + """
    """
    )
    return get_results(endpoint_url, query)


def get_results(endpoint_url, query):
    user_agent = "WDQS-example Python/%s.%s" % (
        sys.version_info[0],
        sys.version_info[1],
    )
    # TODO adjust user agent; see https://w.wiki/CX6
    sparql = SPARQLWrapper(endpoint_url, agent=user_agent)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()


def parse_date(date: str, strppattern: str = "%Y-%m-%dT%H:%M:%SZ"):
    return datetime.datetime.strptime(date, strppattern)


def apa_date(date: datetime.datetime, precision: int):
    formats: dict = {9: "%Y", 10: "%Y, %B", 11: "%Y, %B %d"}
    return date.strftime(formats[precision])


def get_apa_citation(result: dict):
    author: str = result["authors"]["value"]
    date: str = apa_date(
        parse_date(result["idate"]["value"]), int(result["iprecision"]["value"])
    )
    title: str
    if "title" in result:
        title = result["title"]["value"]
    else:
        title = result["itemLabel"]["value"]
    url: str = result["item"]["value"]
    return f"{author} ({date}): <cite>{title}</cite>. {url}"


def get_filename_from_url(url: str):
    return os.path.basename(urllib.parse.urlparse(url).path)


def file_exists_and_has_size(path: str):
    return os.path.exists(path) and os.stat(path).st_size > 0


def check_and_rescale_image(path: str):
    max_dimension: int = 3000
    changed: bool = False

    image = PIL.Image.open(path)

    output_path = pathlib.Path(path).with_suffix(".jpeg")

    if max(image.size) > max_dimension + 1:  # avoid multiple rescales
        scale_factor: float = max_dimension / max(image.size)
        new_dims: tuple = (
            round(image.width * scale_factor),
            round(image.height * scale_factor),
        )
        image = image.resize(new_dims)
        print(f"Resized {output_path}")
        changed = True

    if image.format != "JPEG":
        print(f"Reformatted {output_path}")
        changed = True

    if changed:
        image.save(output_path, "JPEG", quality=90, optimize=True)
        image.close()
    else:
        image.close()
        if not os.path.exists(output_path):
            os.rename(path, output_path)

    return output_path


def download_image(
    url: str,
    image_path: str,
    contact_info: str,
    session: typing.Optional[requests.Session] = None,
):
    if file_exists_and_has_size(image_path):
        print(f"Got cached version of {url}/{image_path}")
    else:
        user_agent: str = f"HistoricalImageBot/0.0 ({contact_info}) python-requests/{requests.__version__}"
        headers = {"User-Agent": user_agent, "From": contact_info}

        if session is None:
            req = requests.get(url, headers=headers)
        else:
            req = session.get(url, headers=headers)
        try:
            req.raise_for_status()
        except Exception as ex:
            print(f"Could not download {url}: {ex}")
            exit(1)
        if not req.ok:
            raise RuntimeError(f"Could not download {url}:" + str(req.status_code))

        with open(image_path, "wb") as output_file:
            output_file.write(req.content)

    output_path = check_and_rescale_image(image_path)
    return output_path


def run(*args):
    end: bool = False
    offset: int = 0
    offset_step: int = 50
    image_dir: str = "wikidata_images"

    item_count: int = 0

    if not args:
        print(
            "Contact info required. Please provide it as the first argument (--script-args <info>)"
        )
        exit(1)
    contact_info: str = args[0]
    session: requests.Session = requests.Session()

    if not os.path.exists(image_dir):
        os.mkdir(image_dir)

    while not end:
        results = query_wikidata(offset=offset * offset_step)
        offset += 1

        if not results["results"]["bindings"]:
            end = True

        for result in results["results"]["bindings"]:
            item_id: str = result["item"]["value"]
            image_url: str = result["pic"]["value"]
            provider = "wikidata"

            item_dict = {
                "date": parse_date(result["idate"]["value"]),
                "date_precision": int(result["iprecision"]["value"]),
                "label": result["itemLabel"]["value"]
                if "itemLabel" in result
                else None,
                "alt_label": result["itemAltLabel"]["value"]
                if "itemAltLabel" in result
                else None,
                "description": result["itemDescription"]["value"]
                if "itemDescription" in result
                else None,
            }

            citations: typing.Dict[str, str] = {"apa": get_apa_citation(result)}

            image_file_name: str = get_filename_from_url(image_url)
            image_file_ending: str = (
                image_file_name.split(".")[-1] if "." in image_file_name else ""
            )
            image_pk: str = date_guesser_operations.get_item_pk(
                item_id=item_id, image_url=image_url
            )

            print(image_pk)
            try:
                download_image(
                    image_url,
                    os.path.join(image_dir, image_pk + "." + image_file_ending),
                    contact_info=contact_info,
                    session=session,
                )
            except Exception as ex:
                print(ex)
                continue

            date_guesser_operations.add_item_and_related(
                item_id=item_id,
                item_dict=item_dict,
                provider_pk=provider,
                citations=citations,
                image_url=image_url,
                image_base_dir=image_dir,
            )
            item_count += 1
            print(f"Item count: {item_count}")


"""
{'item': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q106618632'}, 'pic': {'type': 'uri', 'value': 'http://commons.wikimedia.org/wiki/Special:FilePath/Das%20Fotoalbum%20f%C3%BCr%20Weierstra%C3%9F%20030%20%28Felix%20Klein%29.jpg'}, 'itemLabel': {'xml:lang': 'en', 'type': 'literal', 'value': 'Felix Klein'}, 'itemDescription': {'xml:lang': 'en', 'type': 'literal', 'value': 'photograph by Georg Brokesch'}, 'author': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q1503813'}, 'authorLabel': {'xml:lang': 'en', 'type': 'literal', 'value': 'Georg Brokesch'}, 'idate': {'datatype': 'http://www.w3.org/2001/XMLSchema#dateTime', 'type': 'literal', 'value': '1885-01-01T00:00:00Z'}, 'iprecision': {'datatype': 'http://www.w3.org/2001/XMLSchema#integer', 'type': 'literal', 'value': '9'}, 'title': {'xml:lang': 'de', 'type': 'literal', 'value': 'Felix Klein'}}
"""
