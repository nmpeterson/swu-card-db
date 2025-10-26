import re
from urllib.parse import quote_plus

from sqlalchemy import ForeignKey, create_engine, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship, sessionmaker

DATABASE = "data/db.sqlite3"

engine = create_engine(f"sqlite:///{DATABASE}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SWUSet(Base):
    __tablename__ = "sets"
    id: Mapped[str] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column()
    rotation: Mapped[str | None] = mapped_column()
    name: Mapped[str] = mapped_column()
    cards: Mapped[list["SWUCard"]] = relationship(back_populates="card_set", order_by="SWUCard.id")


class SWUCard(Base):
    __tablename__ = "cards"
    id: Mapped[str] = mapped_column(primary_key=True)
    set_id: Mapped[str] = mapped_column(ForeignKey("sets.id"))
    number: Mapped[int] = mapped_column()
    name: Mapped[str] = mapped_column()
    subtitle: Mapped[str | None] = mapped_column()
    unique: Mapped[bool] = mapped_column()
    rarity: Mapped[str] = mapped_column()
    variant_type: Mapped[str] = mapped_column()
    card_type: Mapped[str] = mapped_column()
    cost: Mapped[str | None] = mapped_column()
    power: Mapped[str | None] = mapped_column()
    hp: Mapped[str | None] = mapped_column()
    front_text: Mapped[str | None] = mapped_column()
    double_sided: Mapped[bool] = mapped_column()
    epic_action: Mapped[str | None] = mapped_column()
    back_text: Mapped[str | None] = mapped_column()
    artist: Mapped[str] = mapped_column()
    artist_search: Mapped[str] = mapped_column()
    arenas: Mapped[list["SWUCardArena"]] = relationship()
    aspects: Mapped[list["SWUCardAspect"]] = relationship(order_by="SWUCardAspect.sort_order")
    traits: Mapped[list["SWUCardTrait"]] = relationship()
    keywords: Mapped[list["SWUCardKeyword"]] = relationship()
    card_set: Mapped["SWUSet"] = relationship(back_populates="cards")

    @property
    def _all_traits(self) -> list[str]:
        session = get_db()
        db = session.__next__()
        all_traits = [
            t.trait for t in db.query(SWUCardTrait.trait).distinct().order_by(SWUCardTrait.trait).all() if t.trait
        ]
        del db
        session.close()
        return all_traits

    @hybrid_property
    def name_and_subtitle(self) -> str:  # type: ignore
        return self.name + " " + (self.subtitle or "")

    @name_and_subtitle.expression
    def name_and_subtitle(cls):
        return cls.name + func.coalesce(cls.subtitle, "")

    @hybrid_property
    def card_text(self) -> str:  # type: ignore
        return (self.front_text or "") + " " + (self.epic_action or "") + " " + (self.back_text or "")

    @card_text.expression
    def card_text(cls):
        return func.coalesce(cls.front_text, "") + func.coalesce(cls.epic_action, "") + func.coalesce(cls.back_text, "")

    @hybrid_property
    def front_text_html(self) -> str:
        is_pilot = any(t.trait == "PILOT" for t in self.traits)
        return self._htmlify_card_text(self.front_text or "", is_pilot=is_pilot)

    @hybrid_property
    def back_text_html(self) -> str:
        is_pilot = any(t.trait == "PILOT" for t in self.traits)
        return self._htmlify_card_text(self.back_text or "", is_pilot=is_pilot)

    @hybrid_property
    def epic_action_html(self) -> str:
        return self._htmlify_card_text(self.epic_action or "")

    @staticmethod
    def _bold(text: str) -> str:
        return f"<b>{text}</b>"

    @staticmethod
    def _italic(text: str) -> str:
        return f"<i>{text}</i>"

    @staticmethod
    def _span(text: str, classes: str, aria_desc: str | None = None) -> str:
        return f'<span class="{classes}" {f'aria-description="{aria_desc}"' if aria_desc else ""}>{text}</span>'

    @staticmethod
    def _image(src: str, alt: str, classes: str | None = None) -> str:
        return f'<img src="{src}" alt="{alt}" {f'class="{classes}"' if classes else ""}>'

    @staticmethod
    def _link(text: str, href: str, classes: str | None = None) -> str:
        return f'<a href="{href}" {f'class="{classes}"' if classes else ""}>{text}</a>'

    def _htmlify_card_text(self, text: str, is_pilot: bool = False) -> str:
        # Initalize multi-line flags
        pilot_text_start_line = None

        lines = text.strip().split("\n")
        for i, line in enumerate(lines):
            # Initialize flags
            full_sentinel = False
            conditional_sentinel = False

            # Punctuation cleanup
            line = re.sub(r'"(.+)"', lambda x: f"“{x.group(1)}”", line)
            line = re.sub(r" - ", " — ", line)
            line = re.sub(r"'", "’", line)

            # Bold action/trigger text
            line = re.sub(r"Epic Action:", lambda x: self._bold(x.group(0)), line)
            line = re.sub(r"Action(?: \[.+\])?:", lambda x: self._bold(x.group(0)), line)
            line = re.sub(r"When [^.:]+:", lambda x: self._bold(x.group(0)), line)
            line = re.sub(r"On [^.:]+:", lambda x: self._bold(x.group(0)), line)

            # Replace text with appropriate symbols/images
            line = re.sub(
                r"(\[.*)Exhaust(.*\])",
                lambda x: f"{x.group(1)}{self._image('/images/icons/exhaust.svg', 'Exhaust', classes='exhaust')}{x.group(2)}",
                line,
                flags=re.IGNORECASE,
            )
            line = re.sub(
                r"(Aggression|Command|Cunning|Heroism|Vigilance|Villainy)",
                lambda x: self._link(
                    self._image(f"/images/aspects/{x.group(1)}-small.png", alt=x.group(1), classes="aspect-img"),
                    f"/search?aspect={x.group(1)}&variant_type=Normal",
                ),
                line,
                flags=re.IGNORECASE,
            )
            line = re.sub(
                r"(non-)?(unique)( \((?:non-)?unique\))",
                lambda x: f"{x.group(1) if x.group(1) else ''}{self._span('✧', classes='unique', aria_desc='Unique')}{x.group(3)}",
                line,
                flags=re.IGNORECASE,
            )

            # Italicize reminder text on Normal variants, hide it on others
            line = re.sub(
                r"( ?\(.+?\))",
                lambda x: self._span(x.group(1), classes="reminder") if self.variant_type == "Normal" else "",
                line,
            )

            # Bold and uppercase "keyword"/"keywords" in text
            line = re.sub(
                r"keywords?", lambda x: self._span(x.group(0).upper(), classes="keyword"), line, flags=re.IGNORECASE
            )

            # Add keyword links, flag SENTINEL/PILOTING lines
            if None not in (keywords := [k.keyword for k in self.keywords]):
                for keyword in keywords:
                    if keyword == "SENTINEL":
                        if line.startswith(keyword) or line.startswith(f"Attached unit gains {keyword}"):
                            full_sentinel = True
                        elif re.search(rf"(?:this|attached) unit [^.]*gains [^.]*{keyword}", line, flags=re.IGNORECASE):
                            conditional_sentinel = True
                    elif keyword == "PILOTING":
                        if line.startswith(keyword):
                            pilot_text_start_line = i
                    line = re.sub(
                        rf"({keyword})( \d+)?( \[.+\])?",
                        lambda x: self._span(
                            f"{self._link(x.group(1) + (x.group(2) or ''), f'/search?keyword={x.group(1)}&variant_type=Normal')}{x.group(3) or ''}",
                            classes="keyword",
                        ),
                        line,
                    )
                    line = re.sub(
                        r"BOUNTIES",
                        self._link("BOUNTIES", "/search?keyword=BOUNTY&variant_type=Normal", classes="keyword"),
                        line,
                    )

            # Check for pilot upgrade text
            if (
                is_pilot
                and pilot_text_start_line is None
                and re.search(r"(attached unit|this upgrade)", line, flags=re.IGNORECASE)
            ):
                pilot_text_start_line = i

            # Add trait links
            TRAIT_GRP = "|".join(self._all_traits)
            line = re.sub(
                rf"({TRAIT_GRP})?(?:, )?({TRAIT_GRP})(,? and |,? or | non-)({TRAIT_GRP})",
                lambda x: (
                    self._link(
                        x.group(1).upper(),
                        f"/search?trait={quote_plus(x.group(1).upper())}&variant_type=Normal",
                        classes="trait",
                    )
                    + ", "
                    if x.group(1)
                    else ""
                )
                + self._link(
                    x.group(2).upper(),
                    f"/search?trait={quote_plus(x.group(2).upper())}&variant_type=Normal",
                    classes="trait",
                )
                + x.group(3)
                + self._link(
                    x.group(4).upper(),
                    f"/search?trait={quote_plus(x.group(4).upper())}&variant_type=Normal",
                    classes="trait",
                ),
                line,
                flags=re.IGNORECASE,
            )
            line = re.sub(
                rf"({TRAIT_GRP})((?: ground| space| leader)? (?:unit|card|event))",
                lambda x: f"{self._link(x.group(1).upper(), f'/search?trait={quote_plus(x.group(1).upper())}&variant_type=Normal', classes='trait')}{x.group(2)}",
                line,
                flags=re.IGNORECASE,
            )
            line = re.sub(
                rf"(attached unit is (?:a |an )?)({TRAIT_GRP})",
                lambda x: f"{x.group(1)}{self._link(x.group(2).upper(), f'/search?trait={quote_plus(x.group(2).upper())}&variant_type=Normal', classes='trait')}",
                line,
                flags=re.IGNORECASE,
            )
            line = re.sub(
                rf"(if it’s (?:a |an )?)({TRAIT_GRP})",
                lambda x: f"{x.group(1)}{self._link(x.group(2).upper(), f'/search?trait={quote_plus(x.group(2).upper())}&variant_type=Normal', classes='trait')}",
                line,
                flags=re.IGNORECASE,
            )
            line = re.sub(
                rf"(search [^.]+ deck for [^.]+ )({TRAIT_GRP})",
                lambda x: f"{x.group(1)}{self._link(x.group(2).upper(), f'/search?trait={quote_plus(x.group(2).upper())}&variant_type=Normal', classes='trait')}",
                line,
                flags=re.IGNORECASE,
            )
            line = re.sub(
                rf"gains the ({TRAIT_GRP}) trait",
                lambda x: f"gains the {self._link(x.group(1).upper(), f'/search?trait={quote_plus(x.group(1).upper())}&variant_type=Normal', classes='trait')} trait",
                line,
                flags=re.IGNORECASE,
            )
            line = re.sub(
                r"(unit without a )(pilot)( on it)",
                lambda x: f"{x.group(1)}{self._link(x.group(2).upper(), f'/search?trait={quote_plus(x.group(2).upper())}&variant_type=Normal', classes='trait')}{x.group(3)}",
                line,
                flags=re.IGNORECASE,
            )

            # Add badges for cost and buffs/debuffs
            line = re.sub(r"C=(\d+)", lambda x: self._span(x.group(1), classes="badge cost"), line, flags=re.IGNORECASE)
            line = re.sub(
                r"Action \[(\d+)",
                lambda x: f"Action [{self._span(x.group(1), classes='badge cost')}",
                line,
                flags=re.IGNORECASE,
            )
            line = re.sub(
                r"(costs?|pays?) (\d+)",
                lambda x: f"{x.group(1)} {self._span(x.group(2), classes='badge cost')}",
                line,
            )
            line = re.sub(
                r"([+-]?\d+)/([+-]?\d+)",
                lambda x: f"{self._span(x.group(1), classes='badge power')}/{self._span(x.group(2), classes='badge hp')}",
                line,
            )
            line = re.sub(
                r"(\d+)( or (:?less|more)(?: remaining)? HP)",
                lambda x: f"{self._span(x.group(1), classes='badge hp')}{x.group(2)}",
                line,
            )
            line = re.sub(
                r"(\d+)( or (:?less|more) power)",
                lambda x: f"{self._span(x.group(1), classes='badge power')}{x.group(2)}",
                line,
            )

            # Wrap each line in a <p> tag
            line = f'<p class="card-text">{line}</p>'

            # Add sentinel decoration
            if full_sentinel:
                line = f'<div class="alert alert-danger p-2 mb-1">{line}</div>'
            elif conditional_sentinel:
                line = f'<div class="alert alert-danger p-2 mb-1 text-body" style="background: none;">{line}</div>'

            # Add PILOTING decoration
            if i == pilot_text_start_line:
                line = f'<div class="alert alert-light p-2 mb-1">{line}'

            lines[i] = line

        formatted_text = "\n".join(line for line in lines if line)
        if pilot_text_start_line is not None:
            formatted_text += "</div>"
        return formatted_text


class SWUCardArena(Base):
    __tablename__ = "card_arenas"
    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[str] = mapped_column(ForeignKey("cards.id"))
    arena: Mapped[str | None] = mapped_column()


class SWUCardAspect(Base):
    __tablename__ = "card_aspects"
    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[str] = mapped_column(ForeignKey("cards.id"))
    aspect: Mapped[str | None] = mapped_column()
    color: Mapped[str | None] = mapped_column()
    sort_order: Mapped[int] = mapped_column()
    double: Mapped[bool] = mapped_column()


class SWUCardTrait(Base):
    __tablename__ = "card_traits"
    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[str] = mapped_column(ForeignKey("cards.id"))
    trait: Mapped[str | None] = mapped_column()


class SWUCardKeyword(Base):
    __tablename__ = "card_keywords"
    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[str] = mapped_column(ForeignKey("cards.id"))
    keyword: Mapped[str | None] = mapped_column()
