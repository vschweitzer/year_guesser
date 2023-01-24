import requests
import urllib.parse
import copy
import typing
import datetime
import re
import logging
import time
import json
import os

import logger

logging.getLogger(__name__).setLevel(logging.DEBUG)


class LOCBase:
    json: dict
    id: str
    logger: logging.Logger = logging.getLogger(__name__)

    def __init__(self, json: dict, id: str) -> None:
        self.json = copy.deepcopy(json)
        self.id = id

    def __str__(self) -> str:
        return self.json.__str__


class LOCResource(LOCBase):
    logger: logging.Logger = logging.getLogger(__name__)

    def __init__(self, json: dict, id: str) -> None:
        super().__init__(json, id)
        if "access_restricted" in self.json:
            if self.json["item"]["access_restricted"]:
                raise ValueError(f'Access restricted for "{self.id}"')

    def has_image(self) -> bool:
        try:
            online_format = self.json["item"]["online_format"]
        except KeyError:
            raise ValueError("Could not determine content type")
        if type(online_format) == str:
            return online_format == "image"
        else:
            return "image" in online_format

    def get_image_options(self):
        image_options: list = []
        try:
            image_options = self.json["page"]
        except KeyError:
            pass
        if image_options:
            return image_options

        try:
            for resource in self.json["resources"]:
                if "files" not in resource:
                    continue
                for file_list in resource["files"]:
                    image_options += file_list
        except KeyError as ex:
            self.logger.warning(f"Exception occurred while assembling file list: {ex}")
            return []

        return image_options

    def current_page(self):
        try:
            return self.json["pagination"]["current"]
        except KeyError:
            return 1

    def pages(self):
        try:
            return self.json["pagination"]["total"]
        except KeyError:
            return 1

    def largest_image(self, mimetype: typing.Optional[str] = "image/jpeg"):
        image_options = self.get_image_options()
        if not image_options:
            raise ValueError("No valid entries found.")
        filter_func = lambda x: (mimetype is None) or (
            "mimetype" in x and x["mimetype"] == mimetype
        )
        valid_entries = list(filter(filter_func, image_options))
        if not valid_entries:
            raise ValueError("No valid entries found for mimetype.")
        return max(
            valid_entries,
            key=lambda x: x["size"]
            if "size" in x
            else x["width"] * x["height"]
            if ("width" in x and "height" in x)
            else 0,
        )

    def other_pages(self):
        pages: list = list(range(1, self.pages() + 1))
        pages.remove(self.current_page())
        return pages

    def date(self, parse=True):
        date_entry = self.json["item"]["date"]

        if parse:
            date_entry = str(date_entry)
            date = None
            possible_date_formats: list = [
                "%Y-%m-%d",
                "%d. %m. %Y",
                "%d-%m-%Y",
                "%d %B %Y",
                "%d. %B %Y",
                "%d. %b. %Y",
                "%d %b %Y",
                "%Y %B %d",
                "%Y %B %d.",
                "%Y %b. %d.",
                "%Y %b %d",
                "%m %Y",
                "%m. %Y",
                "%B %Y",
                "%B. %Y",
                "%B-%Y",
                "%b %Y",
                "%b. %Y",
                "%b-%Y",
                "%Y-%m",
                "%Y %m",
                "%Y-%B",
                "%Y %B",
                "%Y %B.",
                "%Y-%b",
                "%Y %b",
                "%Y %b.",
                "%Y",
                "c%Y.",
            ]

            possible_date_strings: list = [date_entry]
            # if "item" in self.json and "sort_date" in self.json["item"]:
            #    possible_date_strings.append(str(self.json["item"]["sort_date"]))
            possible_date_strings.append(re.sub(r"^\D*(.*?)\D*$", r"\1", date_entry))

            for date_string in possible_date_strings:
                for date_format in possible_date_formats:
                    try:
                        date = datetime.datetime.strptime(str(date_string), date_format)
                        break
                    except ValueError:
                        pass
                if date is not None:
                    break
                self.logger.warning(f'Processing date string "{date_entry}"')

            if date is None:
                raise ValueError(f'Could not parse "{date_entry}" as a datetime')
            return date
        else:
            return date_entry

    def minimized_dict(self):
        d: dict = {}
        d["date"] = str(self.date())
        d["date_raw"] = self.date(parse=False)
        d["jpeg"] = self.largest_image()
        d["cite_this"] = self.json["cite_this"]
        d["access_restricted"] = self.json["item"]["access_restricted"]
        return d


class LOCCollection(LOCBase):
    def items(self):
        return self.json["content"]["set"]["items"]

    def item_ids(self):
        return [
            urllib.parse.urlparse(item["link"]).path.strip("/") for item in self.items()
        ]

    def next_url(self):
        if self.json["next"] is None:
            raise KeyError("No next page")
        return self.json["next"]["url"]


class LOCCrawler:
    base_url: str = "https://www.loc.gov/"
    default_params: dict
    default_headers: dict
    logger: logging.Logger = logging.getLogger(__name__)

    def __init__(self) -> None:
        self.default_headers = {}
        self.default_params = {}

    def make_request(
        self,
        rel,
        params: dict = {},
        headers: dict = {},
        append_url: bool = True,
        retry_on_timeout: int = 2,
        timeout: int = 15,
    ):
        # Currently only supports GET
        if append_url:
            url: str = urllib.parse.urljoin(self.base_url, rel)
        self.logger.debug(f"Raw URL {url}")

        for retry in range(retry_on_timeout + 1):
            req = requests.get(
                url,
                params={**self.default_params, **params},
                headers={**self.default_headers, **headers},
            )
            if not req.ok:
                if (req.status_code in [429, 503]) and retry != retry_on_timeout:
                    self.logger.warning(
                        f"Received status {req.status_code} on retry {retry}. Retrying in {timeout} seconds"
                    )
                    time.sleep(timeout)
                    continue
                else:
                    raise ValueError(f"Request failed: {req.status_code}")

        self.logger.debug(f"Requested URL {req.url}")
        return req

    def json_request(
        self, rel, params: dict = {}, headers: dict = {}, append_url: bool = True
    ):
        json_params: dict = {"fo": "json"}
        return self.make_request(
            rel=rel,
            params={**self.default_params, **params, **json_params},
            headers={**self.default_headers, **headers},
            append_url=append_url,
        ).json()

    def get_resource(
        self,
        id: str,
        page: typing.Optional[int] = None,
        append_prefix: bool = False,
        append_url: bool = True,
    ) -> LOCResource:
        if append_prefix:
            rel = urllib.parse.urljoin("resource/", id)
        else:
            rel = id
        params: dict = {}
        if page is not None:
            params["sp"] = page
        return LOCResource(
            self.json_request(rel=rel, params=params, append_url=append_url), id
        )

    def get_collection(self, rel: str, append_url: bool = True) -> LOCCollection:
        return LOCCollection(self.json_request(rel, append_url=append_url), id=rel)

    def remove_base_url(self, url: str):
        if url.startswith(self.base_url):
            return url[len(self.base_url) :]
        else:
            raise ValueError("URL has to start with base URL")

    def get_collections(self, start_id: str, append_url: bool = True) -> list:
        cols: list = []
        current_col = self.get_collection(start_id, append_url=append_url)

        while True:
            self.logger.debug(f'Got collection ID "{current_col.id}"')
            cols.append(current_col.id)
            try:
                new_id: str = self.remove_base_url(current_col.next_url())
            except KeyError:
                break
            current_col = self.get_collection(new_id)
        return cols


if __name__ == "__main__":
    import pprint

    crawler = LOCCrawler()
    collection_path: str = "./images.json"
    if os.path.exists(collection_path):
        with open(collection_path, "r") as collection_file:
            collections: dict = json.load(collection_file)
    else:
        collections: dict = {}
    c_ids: typing.List[str] = [
        "free-to-use/main-streets",
        "free-to-use/teachers-and-students/",
        "free-to-use/kitchens-and-baths/",
        #'free-to-use/books-maps-more/',
        "free-to-use/natural-disasters/",
        #'free-to-use/fish-and-fishing/',
        #'free-to-use/skyscrapers/',
        "free-to-use/older-people/",
        "free-to-use/farm-life/",
        "free-to-use/diners-drive-ins-restaurants/",
        #'free-to-use/athletes/',
        "free-to-use/aircraft/",
        "free-to-use/families/",
        "free-to-use/lighthouses/",
        "free-to-use/disability-awareness/",
        #'free-to-use/advertising-food/',
        #'free-to-use/birds/',
        #'free-to-use/american-revolution/',
        "free-to-use/historic-sites/",
        #'free-to-use/hats/',
        "free-to-use/libraries/",
        #'free-to-use/presidential-papers/',
        #'free-to-use/art-of-the-book/',
        "free-to-use/shoes/",
        "free-to-use/games-for-fun-and-relaxation/",
        "free-to-use/autumn-and-halloween/",
        "free-to-use/work-in-america/",
        #'free-to-use/tennis/',
        #'free-to-use/independence-day/',
        "free-to-use/weddings/",
        #'free-to-use/horses/',
        #'free-to-use/maps-of-cities/',
        #'free-to-use/cherry-blossoms/',
        "free-to-use/motion-picture-theaters/",
        "free-to-use/discovery-and-exploration/",
        #'free-to-use/veterans/',
        #'free-to-use/genealogy/',
        "free-to-use/cars/",
        "free-to-use/hotels-motels-inns/",
        #'free-to-use/ice-cream/',
        "free-to-use/swimming-beaches/",
        "free-to-use/cats/",
        "free-to-use/historical-travel-pictures/",
        #'free-to-use/african-american-women-changemakers/',
        #'free-to-use/wwi-posters/',
        #'free-to-use/poster-parade/',
        #'free-to-use/bridges/',
        #'free-to-use/not-an-ostrich/',
        #'free-to-use/baseball-cards/',
        #'free-to-use/japanese-prints/',
        #'free-to-use/bicycles/',
        #'free-to-use/irish-americans/',
        "free-to-use/dogs/",
        #'free-to-use/flickrcommons/',
        #'free-to-use/public-domain-films-from-the-national-film-registry/',
        #'free-to-use/abraham-lincoln/',
        #'free-to-use/civil-war-drawings/',
        #'free-to-use/classic-childrens-books/',
        #'free-to-use/john-margolies-roadside-america-photograph-archive/',
        #'free-to-use/c-m-bell-studio-collection/',
        "free-to-use/architecture-and-design/",
        #'free-to-use/travel-posters/',
        #'free-to-use/womens-history-month/',
        #'free-to-use/gottlieb-jazz-photos/',
        #'free-to-use/us-presidential-inaugurations/',
        #'free-to-use/football/',
        "free-to-use/holidays/",
        #'free-to-use/wpa-posters/',
        #'free-to-use/thanksgiving/',
        #'free-to-use/presidential-portraits/'
    ]

    for c_id in c_ids:
        if c_id not in collections:
            items: dict = {}
        else:
            items: dict = collections[c_id]

        collection = crawler.get_collection(rel=c_id)

        for item_id in collection.item_ids():
            if item_id in items and items[item_id]:
                print("Skipped existing item")
                continue
            try:
                # time.sleep(1)
                item = crawler.get_resource(item_id)
                if item_id not in items:
                    items[item_id] = {}
                if (
                    item.current_page() not in items[item_id]
                    or not items[item_id][item.current_page()]
                ):
                    items[item_id][item.current_page()] = item.minimized_dict()
                other_pages = item.other_pages()
            except Exception as ex:
                print(f"Exception occured: {ex}")
                continue
            for page in other_pages:
                if page not in items[item_id] or not items[item_id][page]:
                    try:
                        item = crawler.get_resource(item_id, page=page)
                        items[item_id][item.current_page()] = item.minimized_dict()
                    except Exception as ex:
                        print(f"Exception occured: {ex}")
                        continue
                else:
                    print("Skipping existing page")

        collections[c_id] = items

    with open(collection_path, "w") as collection_file:
        json.dump(collections, collection_file)
    # pprint.pprint(collections)
