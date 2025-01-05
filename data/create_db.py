from collections import Counter
import json
import os
import sqlite3

DATA_DIR = os.path.dirname(__file__)


def main():
    try:
        all_cards = json.load(open(os.path.join(DATA_DIR, "all_cards.json"), "rb"))
    except FileNotFoundError as e:
        raise RuntimeError("Could not find all_cards.json. Please run fetch_card_data.py to create it.") from e
    print(f"Loaded {len(all_cards):,} cards' data into memory")
    card_rows = []
    aspect_rows = []
    trait_rows = []
    arena_rows = []
    for card in all_cards:
        card_id = f"{card['Set']}-{card['Number']}"
        card_rows.append(
            (
                card_id,
                card["Set"],
                card["Number"],
                card["Name"],
                card.get("Subtitle"),
                card.get("Unique", False),
                card["Rarity"],
                card["VariantType"],
                card["Type"],
                card.get("Cost"),
                card.get("Power"),
                card.get("HP"),
                card.get("FrontText"),
                card.get("DoubleSided", False),
                card.get("EpicAction"),
                card.get("BackText"),
                card["Artist"],
            )
        )
        for aspect, n in Counter(card.get("Aspects", [None])).items():
            aspect_rows.append((card_id, aspect, int(n > 1)))
        for trait in card.get("Traits", [None]):
            trait_rows.append((card_id, trait))
        for arena in card.get("Arenas", [None]):
            arena_rows.append((card_id, arena))
    print("Parsed card data into rows for insertion into database")

    db = os.path.join(DATA_DIR, "db.sqlite3")
    if os.path.exists(db):
        print(f"Deleting existing database {db}")
        os.remove(db)
    with sqlite3.connect(db) as con:
        print(f"Initialized database {db}")
        cur = con.cursor()
        print(f"Creating cards table ({len(card_rows):,} rows)")
        cur.execute(
            """
            CREATE TABLE cards (
                "id" TEXT PRIMARY KEY,
                "set" TEXT NOT NULL,
                "number" TEXT NOT NULL,
                "name" TEXT NOT NULL,
                "subtitle" TEXT,
                "unique" INTEGER NOT NULL,
                "rarity" TEXT NOT NULL,
                "variant_type" TEXT NOT NULL,
                "type" TEXT NOT NULL,
                "cost" TEXT,
                "power" TEXT,
                "hp" TEXT,
                "front_text" TEXT,
                "double_sided" INTEGER NOT NULL,
                "epic_action" TEXT,
                "back_text" TEXT,
                "artist" TEXT NOT NULL
            )
            """
        )
        cur.executemany(f"""INSERT INTO cards VALUES({','.join('?' * 17)})""", card_rows)
        con.commit()

        print(f"Creating card_aspects table ({len(aspect_rows):,} rows)")
        cur.execute(
            """
            CREATE TABLE card_aspects (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "card_id" TEXT NOT NULL,
                "aspect" TEXT,
                "double" INTEGER NOT NULL,
                FOREIGN KEY ("card_id") REFERENCES cards("id")
            )
            """
        )
        cur.executemany("""INSERT INTO card_aspects ("card_id", "aspect", "double") VALUES(?,?,?)""", aspect_rows)
        con.commit()

        print(f"Creating card_traits table ({len(trait_rows):,} rows)")
        cur.execute(
            """
            CREATE TABLE card_traits (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "card_id" TEXT NOT NULL,
                "trait" TEXT,
                FOREIGN KEY ("card_id") REFERENCES cards("id")
            )
            """
        )
        cur.executemany("""INSERT INTO card_traits ("card_id", "trait") VALUES(?,?)""", trait_rows)
        con.commit()

        print(f"Creating card_arenas table ({len(arena_rows):,} rows)")
        cur.execute(
            """
            CREATE TABLE card_arenas (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "card_id" TEXT NOT NULL,
                "arena" TEXT,
                FOREIGN KEY ("card_id") REFERENCES cards("id")
            )
            """
        )
        cur.executemany("""INSERT INTO card_arenas ("card_id", "arena") VALUES(?,?)""", arena_rows)
        con.commit()


if __name__ == "__main__":
    main()
