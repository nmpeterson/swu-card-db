import json
import os
import requests

DATA_DIR = os.path.dirname(__file__)
SWU_API_URL = "https://api.swu-db.com"
FULL_SETS = [
    "SOR",
    "SHD",
    "TWI",
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
        response = requests.get(f"{SWU_API_URL}/cards/{set_id}")
        resp_json = response.json()
        for card in sorted(resp_json["data"], key=lambda x: x["Number"]):
            # print(f"{card['Set']}-{card['Number']}: {card['Name']}")
            all_cards.append(clean_card(card))
    for set_id, card_numbers in PARTIAL_SETS.items():
        print(f"Fetching *partial* {set_id} card data...")
        for card_number in card_numbers:
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


def clean_card(card: dict[str, any]) -> dict[str, any]:
    """Drop unwanted properties from card object"""
    return {k: v for k, v in card.items() if k not in DROP_PROPERTIES}


if __name__ == "__main__":
    main()
