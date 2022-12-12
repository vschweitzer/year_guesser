import requests
import hashlib
import json
import os
import time

class SequentialDownloadHandler:
    save_path: str
    dataset: dict

    def __init__(self, dataset_path: str, save_path: str = "./images") -> None:
        self.save_path = save_path
        self.hasher = hashlib.sha256

        with open(dataset_path, "r") as dataset_file:
            self.dataset = json.load(dataset_file)

        for collection in self.dataset:
            for item_index in self.dataset[collection]:
                item = item_index.strip("/")
                for page_index in self.dataset[collection][item_index]:
                    page = int(page_index)
                    url: str = self.dataset[collection][item_index][page_index]["jpeg"]["url"]
                    self.download(item, page, url)
                    time.sleep(0.01)

    def download(self, id: str, page: int, url: str):
        output_path: str = os.path.join(self.save_path, self.get_id(id, page) + ".jpeg")
        if os.path.exists(output_path):
            print(f"Skipping {output_path}")
            return
        req = requests.get(url)
        with open(output_path, "wb") as output_file:
            output_file.write(req.content)
        print(output_path)

    def get_id(self, id: str, page: int):
        unhashed: str = id.strip("/") + "/" + str(page)
        return self.hasher(unhashed.encode("utf-8")).hexdigest()
    
if __name__ == "__main__":
    sdh = SequentialDownloadHandler("./images.json")