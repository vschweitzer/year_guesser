import requests
import urllib.parse
import copy
import typing
import datetime
import re


class LOCResource:
    json: dict
    id: str

    def __init__(self, json: dict, id: str) -> None:
        self.json = copy.deepcopy(json)
        self.id = id

    def __str__(self) -> str:
        return self.json.__str__

    def __repr__(self) -> str:
        return self.json.__repr__

    def get_page_entries(self):
        return self.json["page"]

    def current_page(self):
        return self.json["pagination"]["current"]

    def pages(self):
        return self.json["pagination"]["total"]

    def largest_image(self, mimetype: typing.Optional[str] = "image/jpeg"):
        page_entries = self.get_page_entries()
        if not page_entries:
            raise ValueError("No valid entries found.")
        filter_func = lambda x: (mimetype is None) or (
            "mimetype" in x and x["mimetype"] == mimetype
        )
        valid_entries = list(filter(filter_func, page_entries))
        if not valid_entries:
            raise ValueError("No valid entries found for mimetype.")
        return max(
            valid_entries,
            key=lambda x: x["size"] if "size" in x else x["width"] * x["height"],
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
            possible_date_formats: list = ["%Y-%m-%d", "%Y-%m", "%Y", "c%Y."]

            for date_string in [
                date_entry,
                re.sub(r"^\D*(.*?)\D*$", r"\1", date_entry),
            ]:
                for date_format in possible_date_formats:
                    try:
                        date = datetime.datetime.strptime(str(date_string), date_format)
                        break
                    except ValueError:
                        pass
                if date is not None:
                    break

            if date is None:
                raise ValueError(f"Could not parse {date_entry} as a datetime")
            return date
        else:
            return date_entry


class LOCCrawler:
    base_url: str = "https://www.loc.gov/"
    default_params: dict
    default_headers: dict

    def __init__(self) -> None:
        self.default_headers = {}
        self.default_params = {}

    def make_request(self, rel, params: dict = {}, headers: dict = {}):
        # Currently only supports GET
        url: str = urllib.parse.urljoin(self.base_url, rel)
        req = requests.get(
            url,
            params={**self.default_params, **params},
            headers={**self.default_headers, **headers},
        )
        return req

    def json_request(self, rel, params: dict = {}, headers: dict = {}):
        json_params: dict = {"fo": "json"}
        return self.make_request(
            rel=rel,
            params={**self.default_params, **params, **json_params},
            headers={**self.default_headers, **headers},
        ).json()

    def get_resource(self, id: str):
        rel = urllib.parse.urljoin("resource/", id)
        return LOCResource(self.json_request(rel=rel), id)


if __name__ == "__main__":
    import pprint

    crawler = LOCCrawler()
    res = crawler.get_resource("highsm.44338")
    print(res.pages())
    print(res.other_pages())
    print(res.largest_image())
    print(res.date())
    print(str(res.date(parse=False)))
