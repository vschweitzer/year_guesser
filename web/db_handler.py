import mariadb
import typing
import json
import datetime
import hashlib


class DBHandler:
    def __init__(self, config_path: str) -> None:
        with open(config_path, "r") as config_file:
            self.config: dict = json.load(config_file)
        self.hasher = hashlib.sha256
        self.connection: mariadb.Connection = mariadb.connect(**self.config)
        self.connection.autocommit = True
        # self.cursor: mariadb.Cursor = self.connection.cursor()

    def get_ids(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT item_id, page FROM items")
        return cursor.fetchall()

    def load_from_json(self, path: str):
        input_dict: dict
        with open(path, "r") as json_file:
            input_dict = json.load(json_file)
        for collection_index in input_dict:
            collection: str = collection_index.strip("/")
            print(collection)
            if not self.collection_exists(collection):
                try:
                    self.add_collection(collection)
                except Exception as ex:
                    pass

            for item_index in input_dict[collection_index]:
                item = item_index.strip("/")
                for page_index in input_dict[collection_index][item_index]:
                    page = int(page_index)
                    print(f"{collection} - {item} - {page}")
                    self.add_full_item(
                        item, page, input_dict[collection_index][item_index][page_index]
                    )
                    # exit(0)

    def add_collection(self, id: str):
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO collections (collection_id) VALUES (?)", (id,))
        return cursor

    def boolean_selection(self, query: str, items: tuple):
        cursor = self.connection.cursor()
        cursor.execute(query, items)
        return bool(cursor.fetchall())

    def collection_exists(self, id: str):
        return self.boolean_selection(
            "SELECT collection_id FROM collections c WHERE(c.collection_id = ?)", (id,)
        )

    def add_full_item(
        self, item_id: str, page: int, item: dict, collections: list = []
    ):
        date: datetime.datetime = datetime.datetime.fromisoformat(item["date"])
        date_raw: str = item["date_raw"]
        image_id: str = self.get_image_id(item_id, page)
        if not self.item_exists(item_id, page):
            self.add_item(id=item_id, page=page, date=date, date_raw=date_raw)
        else:
            print("Skip item insertion")

        if not self.image_exists(item_id, page, image_id):
            self.add_image(item_id=item_id, page=page, image_id=image_id)
        else:
            print("Skip image insertion")

        for collection_id in collections:
            if not self.collection_item_exists(item_id, page, collection_id):
                self.add_item_to_collection(item_id, page, collection_id)
            else:
                print(f"Skip inserting {item_id}/{page} into {collection_id}")

        for style in item["cite_this"]:
            if not self.item_citation_exists(item_id, page, style):
                self.add_item_citation(item_id, page, style, item["cite_this"][style])

    def item_citation_exists(self, item_id: str, page: int, style: str):
        return self.boolean_selection(
            "SELECT item_id, page, style FROM cite_as WHERE (item_id = ? AND page = ? AND style = ?)",
            (item_id, page, style),
        )

    def add_item_citation(self, item_id: str, page: int, style: str, citation: str):
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO cite_as (item_id, page, style, citation) VALUES (?, ?, ?, ?)",
            (item_id, page, style, citation),
        )

    def collection_item_exists(self, item_id: str, page: int, collection_id: str):
        return self.boolean_selection(
            "SELECT item_id, page, collection_id FROM collection_items c WHERE (c.item_id = ? AND c.page = ? AND c.collection_id = ?)",
            (item_id, page, collection_id),
        )

    def add_item_to_collection(self, item_id: str, page: int, collection_id: str):
        if not self.item_exists(item_id, page):
            raise KeyError(f"Item {item_id}/{page} does not exist")

        if not self.collection_exists(collection_id):
            raise KeyError(f"Collection {collection_id} does not exist")

        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO collection_items (item_id, page, collection_id) VALUES (?, ?, ?)",
            (item_id, page, collection_id),
        )

    def add_item(self, id: str, page: int, date: datetime.datetime, date_raw: str):
        cursor = self.connection.cursor()
        date_string: str = date.strftime("%Y-%m-%d")
        cursor.execute(
            "INSERT INTO items (item_id, page, date, date_raw) VALUES (?, ?, ?, ?)",
            (id, page, date_string, date_raw),
        )

    def item_exists(self, id: str, page: int):
        return self.boolean_selection(
            "SELECT item_id, page FROM items i WHERE(i.item_id = ? AND i.page = ?)",
            (
                id,
                page,
            ),
        )

    def add_image(self, item_id: str, page: int, image_id: str, ending: str = "jpeg"):
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO images (item_id, page, image_id, ending) VALUES (?, ?, ?, ?)",
            (item_id, page, image_id, ending),
        )

    def image_exists(
        self, item_id: str, page: int, image_id: str, ending: str = "jpeg"
    ):
        return self.boolean_selection(
            "SELECT item_id, page, image_id, ending FROM images i WHERE (i.item_id = ? AND i.page = ? AND i.image_id = ? AND i.ending = ?)",
            (item_id, page, image_id, ending),
        )

    def delete_all_items(self):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM items")

    def get_image_id(self, id: str, page: int):
        unhashed: str = id.strip("/") + "/" + str(page)
        return self.hasher(unhashed.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    db_config_path: str = "./db_access.json"
    handler = DBHandler(db_config_path)
    handler.delete_all_items()
    for id, page in handler.get_ids():
        print(f"{id} - {page}")

    handler.load_from_json("./images.json")
