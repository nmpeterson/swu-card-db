import json
import os
from io import BytesIO

import requests
from PIL import Image


OVERWRITE = False  # Set to True to overwrite existing images
UPDATE_SET_IDS = {
    "SOR",
    "SHD",
    "TWI",
    "JTL",
    "LOF",
    "SEC",
}

DATA_DIR = os.path.dirname(__file__)
IMG_DIR = os.path.abspath(os.path.join(DATA_DIR, "../app/static/images"))
CARD_IMG_URL = "https://swudb.com/images/cards/{set_id}/{number}.png"
CARD_BACK_IMG_URL = "https://swudb.com/images/cards/{set_id}/{number}-portrait.png"


def main():
    try:
        all_cards = json.load(open(os.path.join(DATA_DIR, "all_cards.json"), "rb"))
    except FileNotFoundError as e:
        raise RuntimeError("Could not find all_cards.json. Please run fetch_card_data.py to create it.") from e
    print(f"Loaded {len(all_cards):,} cards' data into memory")

    print("Fetching card images...")
    for card in all_cards:
        set_id = card["Set"]
        if UPDATE_SET_IDS and set_id not in UPDATE_SET_IDS:
            continue
        number = card["Number"]
        double_sided = card.get("DoubleSided", False)
        url = CARD_IMG_URL.format(set_id=set_id, number=number)
        fetch_images = {url: f"{IMG_DIR}/cards/{set_id}/{number}.webp"}
        if double_sided:
            url_back = CARD_BACK_IMG_URL.format(set_id=set_id, number=number)
            fetch_images[url_back] = f"{IMG_DIR}/cards/{set_id}/{number}-back.webp"
        for url, path in fetch_images.items():
            if OVERWRITE or not os.path.exists(path):
                if not os.path.exists(os.path.dirname(path)):
                    os.makedirs(os.path.dirname(path))
                try:
                    print(f"Fetching {url} -> {path}")
                    response = requests.get(url)
                    if response.status_code == 404 and url.endswith("-portrait.png"):
                        url = url.replace("-portrait.png", "-back.png")
                        print(f"Fetching {url} -> {path}")
                        response = requests.get(url)
                    response.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    print(f"Failed to fetch {url}: {e}")
                else:
                    im = Image.open(BytesIO(response.content))
                    im.save(path, "webp")


if __name__ == "__main__":
    main()
