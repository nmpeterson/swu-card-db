import json
import os
import requests


OVERWRITE = False  # Set to True to overwrite existing images
DATA_DIR = os.path.dirname(__file__)
IMG_DIR = os.path.abspath(os.path.join(DATA_DIR, "../app/static/images"))
CARD_IMG_URL = "https://swudb.com/cards/{set_id}/{number}.png"
CARD_BACK_IMG_URL = "https://swudb.com/cards/{set_id}/{number}-portrait.png"
ASPECT_IMG_URL = "https://swudb.com/images/{aspect}.png"
ASPECTS = [
    "Aggression",
    "Command",
    "Cunning",
    "Vigilance",
    "Villainy",
    "Heroism",
]


def main():
    try:
        all_cards = json.load(open(os.path.join(DATA_DIR, "all_cards.json"), "rb"))
    except FileNotFoundError as e:
        raise RuntimeError("Could not find all_cards.json. Please run fetch_card_data.py to create it.") from e
    print(f"Loaded {len(all_cards):,} cards' data into memory")

    print("Fetching card images...")
    for card in all_cards:
        set_id = card["Set"]
        number = card["Number"]
        double_sided = card.get("DoubleSided", False)
        url = CARD_IMG_URL.format(set_id=set_id, number=number)
        fetch_images = {url: f"{IMG_DIR}/cards/{set_id}/{number}.png"}
        if double_sided:
            url_back = CARD_BACK_IMG_URL.format(set_id=set_id, number=number)
            fetch_images[url_back] = f"{IMG_DIR}/cards/{set_id}/{number}-back.png"
        for url, path in fetch_images.items():
            if OVERWRITE or not os.path.exists(path):
                if not os.path.exists(os.path.dirname(path)):
                    os.makedirs(os.path.dirname(path))
                print(f"Fetching {url} -> {path}")
                response = requests.get(url)
                with open(path, "wb") as f:
                    f.write(response.content)

    print("Fetching aspect images...")
    for aspect in ASPECTS:
        url = ASPECT_IMG_URL.format(aspect=aspect)
        path = f"{IMG_DIR}/aspects/{aspect}.png"
        if OVERWRITE or not os.path.exists(path):
            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            print(f"Fetching {url} -> {path}")
            response = requests.get(url)
            with open(path, "wb") as f:
                f.write(response.content)


if __name__ == "__main__":
    main()
