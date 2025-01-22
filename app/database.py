from sqlalchemy import ForeignKey, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship, sessionmaker

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
    name: Mapped[str] = mapped_column()
    cards: Mapped[list["SWUCard"]] = relationship(back_populates="card_set", order_by="SWUCard.id")


class SWUCard(Base):
    __tablename__ = "cards"
    id: Mapped[str] = mapped_column(primary_key=True)
    set_id: Mapped[str] = mapped_column(ForeignKey("sets.id"))
    number: Mapped[str] = mapped_column()
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
    arenas: Mapped[list["SWUCardArena"]] = relationship()
    aspects: Mapped[list["SWUCardAspect"]] = relationship(order_by="SWUCardAspect.sort_order")
    traits: Mapped[list["SWUCardTrait"]] = relationship()
    keywords: Mapped[list["SWUCardKeyword"]] = relationship()
    card_set: Mapped["SWUSet"] = relationship(back_populates="cards")

    @hybrid_property
    def name_and_subtitle(self) -> str:
        return self.name + " " + (self.subtitle or "")

    @name_and_subtitle.expression
    @classmethod
    def name_and_subtitle(cls):
        return cls.name + func.coalesce(cls.subtitle, "")

    @hybrid_property
    def card_text(self) -> str:
        return (self.front_text or "") + " " + (self.epic_action or "") + " " + (self.back_text or "")

    @card_text.expression
    @classmethod
    def card_text(cls):
        return func.coalesce(cls.front_text, "") + func.coalesce(cls.epic_action, "") + func.coalesce(cls.back_text, "")


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
