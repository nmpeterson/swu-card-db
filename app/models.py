from pydantic import BaseModel


class SetModel(BaseModel):
    id: str
    name: str
    rotation: str | None
    number: int


class ArenaModel(BaseModel):
    arena: str | None


class AspectModel(BaseModel):
    aspect: str | None
    color: str | None
    double: bool


class TraitModel(BaseModel):
    trait: str | None


class KeywordModel(BaseModel):
    keyword: str | None


class CardModel(BaseModel):
    id: str
    set_id: str
    number: str
    name: str
    subtitle: str | None
    unique: bool
    rarity: str
    variant_type: str
    card_type: str
    cost: str | None
    power: str | None
    hp: str | None
    front_text: str | None
    double_sided: bool
    epic_action: str | None
    back_text: str | None
    artist: str
    aspects: list[AspectModel]
    arenas: list[ArenaModel]
    traits: list[TraitModel]
    keywords: list[KeywordModel]
