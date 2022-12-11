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
        return cursor

    def load_from_json(self, path: str):
        input_dict: dict
        with open(path, "r") as json_file:
            input_dict = json.load(json_file)
        for collection_index in input_dict:
            collection: str = collection_index.strip("/")
            print(collection)
            try:
                self.add_collection(collection)
            except Exception as ex:
                pass
        
            for item_index in input_dict[collection_index]:
                item = item_index.strip("/")
                for page_index in input_dict[collection_index][item_index]:
                    page = int(page_index)
                    print(f"{collection} - {item} - {page}")

    def add_collection(self, id: str):
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO collections (collection_id) VALUES (?)", (id,))
        return cursor

if __name__ == "__main__":
    db_config_path: str = "./db_access.json"
    handler = DBHandler(db_config_path)
    for id, page in handler.get_ids():
        print(f"{id} - {page}")
    
    handler.load_from_json("./images.json")