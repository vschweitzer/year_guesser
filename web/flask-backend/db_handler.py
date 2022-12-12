import mariadb
import typing
import json
import datetime


class DBHandler:
    def __init__(self, config_path: str) -> None:
        with open(config_path, "r") as config_file:
            self.config: dict = json.load(config_file)

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
                    #exit(0)

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

    def add_full_item(self, item_id: str, page: int, item: dict):
        date: datetime.datetime = datetime.datetime.fromisoformat(item["date"])
        date_raw: str = item["date_raw"]
        if not self.item_exists(item_id, page):
            try:
                self.add_item(id=item_id, page=page, date=date, date_raw=date_raw)
            except Exception as ex:
                print(ex)

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

    def delete_all_items(self):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM items")


if __name__ == "__main__":
    db_config_path: str = "./db_access.json"
    handler = DBHandler(db_config_path)
    for id, page in handler.get_ids():
        print(f"{id} - {page}")

    
    handler.load_from_json("./images.json")
