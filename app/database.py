from dataclasses import dataclass
from sqlalchemy import Boolean, ForeignKey, Integer, create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship


DATABASE = "data/db.sqlite3"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@dataclass(frozen=True, kw_only=True)
class SWUSet:
    id: str
    name: str


class SWUCard(Base):
    __tablename__ = "cards"
    id = Column(String, primary_key=True)
    set = Column(String)
    number = Column(String)
    name = Column(String)
    subtitle = Column(String)
    unique = Column(Boolean)
    rarity = Column(String)
    variant_type = Column(String)
    type = Column(String)
    cost = Column(String)
    power = Column(String)
    hp = Column(String)
    front_text = Column(String)
    double_sided = Column(Boolean)
    epic_action = Column(String)
    back_text = Column(String)
    artist = Column(String)
    arenas = relationship("SWUCardArena", back_populates="card")
    aspects = relationship("SWUCardAspect", back_populates="card")
    traits = relationship("SWUCardTrait", back_populates="card")


class SWUCardArena(Base):
    __tablename__ = "card_arenas"
    id = Column(Integer, primary_key=True)
    card_id = Column(String, ForeignKey("cards.id"))
    arena = Column(String)
    card = relationship("SWUCard", back_populates="arenas")


class SWUCardAspect(Base):
    __tablename__ = "card_aspects"
    id = Column(Integer, primary_key=True)
    card_id = Column(String, ForeignKey("cards.id"))
    aspect = Column(String)
    double = Column(Boolean)
    card = relationship("SWUCard", back_populates="aspects")


class SWUCardTrait(Base):
    __tablename__ = "card_traits"
    id = Column(Integer, primary_key=True)
    card_id = Column(String, ForeignKey("cards.id"))
    trait = Column(String)
    card = relationship("SWUCard", back_populates="traits")
