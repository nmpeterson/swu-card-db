from collections import Counter
import json
import os
import re
import sqlite3
from unidecode import unidecode

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

ASPECT_COLORS = {
    "Vigilance": "blue",
    "Command": "green",
    "Aggression": "red",
    "Cunning": "yellow",
    "Villainy": "black",
    "Heroism": "white",
}

KEYWORDS = {
    "AMBUSH",
    "GRIT",
    "OVERWHELM",
    "RAID",
    "RESTORE",
    "SABOTEUR",
    "SENTINEL",
    "SHIELDED",
    "BOUNTY",
    "SMUGGLE",
    "COORDINATE",
    "EXPLOIT",
    "PILOTING",
    "HIDDEN",
}

ARTIST_SEARCH_REMAP = {
    # Remap artist name typos or alternate spellings (other than diacritics)
    "Aitor Prieto Reyes": "Aitor Prieto",
    "Amélie Hutt": "Axel Hutt",
    "Anny Maulina": "Ann Maulina",
    "Christian Papzoglakis": "Christian Papazoglakis",
    "Frank Cannels": "Francois Cannels",
    "Gretel Nancy Lusky": "Gretel Lusky",
    "Liana Anatolievich": "Liana Anatolevich",
    "Roxana Karpatvogyi": "Roxana Karpatvolgyi",
    "Sandra Chewlińska": "Sandra Chlewińska",
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
    keyword_rows = []
    for card in all_cards:
        card_id = f"{card['Set']}-{card['Number']}"
        if card_id in corrections:
            card.update(corrections[card_id])
        front_text, front_keywords = clean_card_text(card.get("FrontText"))
        back_text, back_keywords = clean_card_text(card.get("BackText"))
        card_rows.append(
            (
                card_id,
                card["Set"],
                int(card["Number"]),
                card["Name"],
                card.get("Subtitle"),
                card.get("Unique", False),
                card["Rarity"],
                card["VariantType"],
                card["Type"],
                card.get("Cost"),
                card.get("Power"),
                card.get("HP"),
                front_text,
                card.get("DoubleSided", False),
                card.get("EpicAction"),
                back_text,
                card["Artist"],
                unidecode(ARTIST_SEARCH_REMAP.get(card["Artist"], card["Artist"])),
            )
        )
        if card.get("Aspects") == []:
            del card["Aspects"]
        for aspect, n in Counter(card.get("Aspects", [None])).items():
            aspect = None if aspect == "" else aspect
            aspect_rows.append((card_id, aspect, ASPECT_COLORS.get(aspect), ASPECT_SORT_ORDER[aspect], int(n > 1)))
        for trait in card.get("Traits", [None]):
            trait_rows.append((card_id, trait))
        for arena in card.get("Arenas", [None]):
            arena_rows.append((card_id, arena))
        keywords = front_keywords | back_keywords
        if not keywords:
            keywords.add(None)
        for keyword in keywords:
            keyword_rows.append((card_id, keyword))
        if not keyword_rows:
            keyword_rows.append(None)
    print("Parsed card data into rows for insertion into database")

    # Load set data
    sets = json.load(open(os.path.join(DATA_DIR, "sets.json"), "rb"))
    print(f"Loaded {len(sets):,} sets' data into memory")
    set_rows = [(s["id"], s["number"], s["rotation"], s["name"]) for s in sets]
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
                "rotation" TEXT,
                "name" TEXT NOT NULL
            )
            """
        )
        cur.executemany("""INSERT INTO sets VALUES(?,?,?,?)""", set_rows)
        con.commit()

        print(f"Creating cards table ({len(card_rows):,} rows)")
        cur.execute(
            """
            CREATE TABLE cards (
                "id" TEXT PRIMARY KEY,
                "set_id" TEXT NOT NULL,
                "number" INTEGER NOT NULL,
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
                "artist_search" TEXT NOT NULL,
                FOREIGN KEY ("set_id") REFERENCES sets("id")
            )
            """
        )
        cur.executemany(f"""INSERT INTO cards VALUES({",".join("?" * len(card_rows[0]))})""", card_rows)
        con.commit()

        print(f"Creating card_aspects table ({len(aspect_rows):,} rows)")
        cur.execute(
            """
            CREATE TABLE card_aspects (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "card_id" TEXT NOT NULL,
                "aspect" TEXT,
                "color" TEXT,
                "sort_order" INTEGER NOT NULL,
                "double" INTEGER NOT NULL,
                FOREIGN KEY ("card_id") REFERENCES cards("id")
            )
            """
        )
        cur.executemany(
            """INSERT INTO card_aspects ("card_id", "aspect", "color", "sort_order", "double") VALUES(?,?,?,?,?)""",
            aspect_rows,
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

        print(f"Creating card_keywords table ({len(keyword_rows):,} rows)")
        cur.execute(
            """
            CREATE TABLE card_keywords (
                "id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "card_id" TEXT NOT NULL,
                "keyword" TEXT,
                FOREIGN KEY ("card_id") REFERENCES cards("id")
            )
            """
        )
        cur.executemany("""INSERT INTO card_keywords ("card_id", "keyword") VALUES(?,?)""", keyword_rows)
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
        cur.execute("""CREATE INDEX keyword_card_id_index ON card_keywords (card_id)""")
        cur.execute("""CREATE INDEX keyword_search_index ON card_keywords (keyword)""")
        con.commit()


def clean_card_text(text: str | None) -> tuple[str | None, set[str]]:
    keywords = set()
    if not text:
        return text, keywords
    text = text.replace("{", "").replace("}", "")
    lines = [line.strip() for line in text.split("\n")]
    KW_GRP = "|".join(KEYWORDS)  # Group of all possible keywords
    NOT_UNLESS = "(?<!unless he)(?<!unless she)(?<!unless it)"  # Negative lookbehind for "unless he/she/it"

    for i in range(len(lines)):
        # Find lines starting with a keyword (and an optional 2nd)
        if match := re.match(pattern := rf"({KW_GRP})( \d+)?(, ({KW_GRP}))?", lines[i], re.IGNORECASE):
            keywords.add(match.group(1).upper())
            if match.group(4):
                keywords.add(match.group(4).upper())
            lines[i] = re.sub(
                pattern,
                lambda x: f"{x.group(1).upper()}{x.group(2) or ''}{f', {x.group(4).upper()}' if x.group(3) else ''}",
                lines[i],
                flags=re.IGNORECASE,
            )

        # Find lines with "gain(s) {keyword}" (but not "unless he/she/it gains {keyword}")
        if match := re.search(
            pattern := rf"({NOT_UNLESS} gains?:?,? \"?)({KW_GRP})( \d+)?( and ({KW_GRP}))?",
            lines[i],
            re.IGNORECASE,
        ):
            keywords.add(match.group(2).upper())
            if match.group(5):
                keywords.add(match.group(5).upper())
            lines[i] = re.sub(
                pattern,
                lambda x: f"{x.group(1)}{x.group(2).upper()}{x.group(3) or ''}{f' and {x.group(5).upper()}' if x.group(4) else ''}",
                lines[i],
                flags=re.IGNORECASE,
            )

        # Find lines with common 2-part keyword patterns
        for pattern in [
            rf"(COORDINATE - )({KW_GRP})",  # "COORDINATE - {keyword}"
            rf"(give it )({KW_GRP})",  # "give it {keyword}"
            rf"(give (?:each|a|an) (?:[^.]+ )?unit )({KW_GRP})",  # "give each/a(n) {qualifier?} unit {keyword}"
            rf"(using )({KW_GRP})",  # "using {keyword}"
            rf"({NOT_UNLESS} has )({KW_GRP})",  # "has {keyword}" (but not "unless he/she/it has {keyword}")
            rf"(units? with )({KW_GRP})",  # "unit(s) with {keyword}"
            r"((?:has|with) a )(bounty)",  # "has/with a {bounty}"
        ]:
            if match := re.search(pattern, lines[i], re.IGNORECASE):
                keywords.add(match.group(2).upper())
                lines[i] = re.sub(pattern, lambda x: f"{x.group(1)}{x.group(2).upper()}", lines[i], flags=re.IGNORECASE)

        # Find lines with "collect ... bounties"
        if match := re.search(pattern := r"(collect [^.]+ )(bounties)", lines[i], re.IGNORECASE):
            keywords.add("BOUNTY")
            lines[i] = re.sub(pattern, lambda x: f"{x.group(1)}{x.group(2).upper()}", lines[i], flags=re.IGNORECASE)

    text = "\n".join(lines)
    return text, keywords


if __name__ == "__main__":
    main()
