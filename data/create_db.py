from collections import Counter
import json
import os
import sqlite3

DATA_DIR = os.path.dirname(__file__)

ASPECT_SORT_ORDER = {
    "Vigilance": 1,
    "Command": 2,
    "Aggression": 3,
    "Cunning": 4,
    "Villainy": 5,
    "Heroism": 6,
    None: 7,
}


def main():
    # Load card data
    try:
        all_cards = json.load(open(os.path.join(DATA_DIR, "all_cards.json"), "rb"))
    except FileNotFoundError as e:
        raise RuntimeError("Could not find all_cards.json. Please run fetch_card_data.py to create it.") from e
    print(f"Loaded {len(all_cards):,} cards' data into memory")

    # Load manual corrections
    try:
        corrections = json.load(open(os.path.join(DATA_DIR, "corrections.json"), "rb"))
    except FileNotFoundError:
        corrections = {}

    card_rows = []
    aspect_rows = []
    trait_rows = []
    arena_rows = []
    for card in all_cards:
        card_id = f"{card['Set']}-{card['Number']}"
        if card_id in corrections:
            card.update(corrections[card_id])
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
            aspect_rows.append((card_id, aspect, ASPECT_SORT_ORDER[aspect], int(n > 1)))
        for trait in card.get("Traits", [None]):
            trait_rows.append((card_id, trait))
        for arena in card.get("Arenas", [None]):
            arena_rows.append((card_id, arena))
    print("Parsed card data into rows for insertion into database")

    # Load set data
    sets = json.load(open(os.path.join(DATA_DIR, "sets.json"), "rb"))
    print(f"Loaded {len(sets):,} sets' data into memory")
    set_rows = [(s["id"], s["number"], s["name"]) for s in sets]
    print("Parsed set data into rows for insertion into database")

    db = os.path.join(DATA_DIR, "db.sqlite3")
    if os.path.exists(db):
        print(f"Deleting existing database {db}")
        os.remove(db)
    with sqlite3.connect(db) as con:
        print(f"Initialized database {db}")
        cur = con.cursor()

        print(f"Creating sets table ({len(sets):,} rows)")
        cur.execute(
            """
            CREATE TABLE sets (
                "id" TEXT PRIMARY KEY,
                "number" INTEGER NOT NULL,
                "name" TEXT NOT NULL
            )
            """
        )
        cur.executemany("""INSERT INTO sets VALUES(?,?,?)""", set_rows)
        con.commit()

        print(f"Creating cards table ({len(card_rows):,} rows)")
        cur.execute(
            """
            CREATE TABLE cards (
                "id" TEXT PRIMARY KEY,
                "set_id" TEXT NOT NULL,
                "number" TEXT NOT NULL,
                "name" TEXT NOT NULL,
                "subtitle" TEXT,
                "unique" INTEGER NOT NULL,
                "rarity" TEXT NOT NULL,
                "variant_type" TEXT NOT NULL,
                "card_type" TEXT NOT NULL,
                "cost" TEXT,
                "power" TEXT,
                "hp" TEXT,
                "front_text" TEXT,
                "double_sided" INTEGER NOT NULL,
                "epic_action" TEXT,
                "back_text" TEXT,
                "artist" TEXT NOT NULL,
                FOREIGN KEY ("set_id") REFERENCES sets("id")
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
                "sort_order" INTEGER NOT NULL,
                "double" INTEGER NOT NULL,
                FOREIGN KEY ("card_id") REFERENCES cards("id")
            )
            """
        )
        cur.executemany(
            """INSERT INTO card_aspects ("card_id", "aspect", "sort_order", "double") VALUES(?,?,?,?)""", aspect_rows
        )
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

        print("Adding indices")
        cur.execute("""CREATE INDEX set_id_index ON sets (id)""")
        cur.execute("""CREATE INDEX set_search_index ON cards (number, name)""")
        cur.execute("""CREATE INDEX card_id_index ON cards (id)""")
        cur.execute("""CREATE INDEX card_search_index ON cards (set_id, variant_type, card_type, rarity, artist)""")
        cur.execute("""CREATE INDEX aspect_card_id_index ON card_aspects (card_id)""")
        cur.execute("""CREATE INDEX aspect_search_index ON card_aspects (aspect, sort_order)""")
        cur.execute("""CREATE INDEX trait_card_id_index ON card_traits (card_id)""")
        cur.execute("""CREATE INDEX trait_search_index ON card_traits (trait)""")
        cur.execute("""CREATE INDEX arena_card_id_index ON card_arenas (card_id)""")
        cur.execute("""CREATE INDEX arena_search_index ON card_arenas (arena)""")
        con.commit()


if __name__ == "__main__":
    main()
