import json
import os
from typing import Any
import requests

DATA_DIR = os.path.dirname(__file__)
SWU_API_URL = "https://api.swu-db.com"
FULL_SETS = [
    "SOR",
    "SHD",
    "TWI",
    "LOF",
]
PARTIAL_SETS = {
    "JTL": [*range(1, 525), *range(997, 1051)],  # Ignore foils and prestige serialized
}
DROP_PROPERTIES = [
    "FrontArt",
    "BackArt",
    "MarketPrice",
    "LowPrice",
    "FoilPrice",
    "LowFoilPrice",
]


def main():
    """Collect card data for each set, and write combined array to all_cards.json"""
    all_cards = []
    for set_id in FULL_SETS:
        print(f"Fetching {set_id} card data...")
        try:
            response = requests.get(f"{SWU_API_URL}/cards/{set_id}")
            response.raise_for_status()
            resp_json = response.json()
            for card in sorted(resp_json["data"], key=lambda x: x["Number"]):
                # print(f"{card['Set']}-{card['Number']}: {card['Name']}")
                all_cards.append(clean_card(card))
        except requests.exceptions.HTTPError as e:
            raise ValueError(f"Full set data not found for {set_id}") from e
    for set_id, card_numbers in PARTIAL_SETS.items():
        print(f"Fetching *partial* {set_id} card data...")
        need_cards = set(card_numbers)
        try:
            response = requests.get(f"{SWU_API_URL}/cards/{set_id}")
            response.raise_for_status()
            resp_json = response.json()
            for card in sorted(resp_json["data"], key=lambda x: int(x["Number"])):
                # print(f"{card['Set']}-{card['Number']}: {card['Name']}")
                if (card_number := int(card["Number"])) in need_cards:
                    all_cards.append(clean_card(card))
                    need_cards.remove(card_number)
        except requests.exceptions.HTTPError as e:
            print(f"Full set data not found for {set_id}: {e}")
        if need_cards:
            print(f"Fetching {len(need_cards)} remaining {set_id} cards one by one...")
        for card_number in sorted(need_cards):
            try:
                response = requests.get(f"{SWU_API_URL}/cards/{set_id}/{card_number}")
                response.raise_for_status()
                card = response.json()
                # print(f"{card['Set']}-{card['Number']}: {card['Name']}")
                all_cards.append(clean_card(card))
            except requests.exceptions.HTTPError as e:
                print(f"Error fetching data for {set_id}-{card_number}: {e}")
    with open(os.path.join(DATA_DIR, "all_cards.json"), "wb") as f:
        print("Writing data to all_cards.json...")
        f.write(json.dumps(all_cards, indent=2).encode("utf-8"))


def clean_card(card: dict[str, Any]) -> dict[str, Any]:
    """Drop unwanted properties from card object"""
    return {k: v for k, v in card.items() if k not in DROP_PROPERTIES}


if __name__ == "__main__":
    main()
