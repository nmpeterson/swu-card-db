import json
import os
import requests

DATA_DIR = os.path.dirname(__file__)
SWU_API_URL = "https://api.swu-db.com"
SETS = [
    "SOR",
    "SHD",
    "TWI",
]
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
    for set_id in SETS:
        print(f"Fetching {set_id} card data...")
        response = requests.get(f"{SWU_API_URL}/cards/{set_id}")
        resp_json = response.json()
        for card in sorted(resp_json["data"], key=lambda x: x["Number"]):
            # print(f"{card['Set']}-{card['Number']}: {card['Name']}")
            all_cards.append(clean_card(card))
    with open(os.path.join(DATA_DIR, "all_cards.json"), "wb") as f:
        print("Writing data to all_cards.json...")
        f.write(json.dumps(all_cards, indent=2).encode("utf-8"))


def clean_card(card: dict[str, any]) -> dict[str, any]:
    """Drop unwanted properties from card object"""
    return {k: v for k, v in card.items() if k not in DROP_PROPERTIES}


if __name__ == "__main__":
    main()
