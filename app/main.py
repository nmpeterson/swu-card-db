import logging
from datetime import date
from typing import Annotated, Literal
from urllib.parse import quote_plus

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.sql.expression import func
from sqlalchemy.orm import Session

from .database import get_db, SWUSet, SWUCard, SWUCardArena, SWUCardAspect, SWUCardTrait, SWUCardKeyword
from .models import SetModel, CardModel

logging.basicConfig(level=logging.DEBUG)

app = FastAPI(
    title="SWUcards.info APIs",
    version="preview",
    contact={
        "name": "Noel Peterson",
        "url": "https://www.swucards.info",
        "email": "noel@swucards.info",
    },
    redoc_url=None,
)
app.mount("/images", StaticFiles(directory="app/static/images"), name="images")
app.mount("/css", StaticFiles(directory="app/static/css"), name="css")
templates = Jinja2Templates(directory="app/templates", trim_blocks=True, lstrip_blocks=True)

# Add quote_plus filter to Jinja2 templates
templates.env.filters["quote_plus"] = quote_plus

# Get current year for footer
current_year = date.today().year
templates.env.globals["current_year"] = current_year


# Get common database query results ONCE for template context
session = get_db()
db = session.__next__()

all_sets = db.query(SWUSet).order_by(SWUSet.number).all()

advanced_search_options = {
    "set_options": [{"id": s.id, "name": s.name} for s in all_sets],
    "arena_options": [
        a.arena for a in db.query(SWUCardArena.arena).distinct().order_by(SWUCardArena.arena).all() if a.arena
    ],
    "aspect_options": [
        {"aspect": a.aspect, "color": a.color}
        for a in db.query(SWUCardAspect.aspect, SWUCardAspect.color, SWUCardAspect.sort_order)
        .distinct()
        .order_by(SWUCardAspect.sort_order)
        .all()
        if a.aspect
    ],
    "trait_options": [
        t.trait for t in db.query(SWUCardTrait.trait).distinct().order_by(SWUCardTrait.trait).all() if t.trait
    ],
    "keyword_options": [
        k.keyword
        for k in db.query(SWUCardKeyword.keyword).distinct().order_by(SWUCardKeyword.keyword).all()
        if k.keyword
    ],
    "card_type_options": [
        c.card_type for c in db.query(SWUCard.card_type).distinct().order_by(SWUCard.card_type).all()
    ],
    "rarity_options": [c.rarity for c in db.query(SWUCard.rarity).distinct().order_by(SWUCard.rarity).all()],
    "artist_options": [
        c.artist_search for c in db.query(SWUCard.artist_search).distinct().order_by(SWUCard.artist_search).all()
    ],
    "variant_type_options": [
        c.variant_type for c in db.query(SWUCard.variant_type).distinct().order_by(SWUCard.variant_type).all()
    ],
    "rotation_options": [
        s.rotation for s in db.query(SWUSet.rotation).distinct().order_by(SWUSet.rotation).all() if s.rotation
    ],
}

del db
session.close()

templates.env.globals["all_sets"] = all_sets


# Define routes
@app.get("/", include_in_schema=False)
async def root(request: Request):
    """Return the home page at /"""
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/search", include_in_schema=False)
async def search(request: Request, db: Session = Depends(get_db)):
    """Return the search page (form and results) at /search"""
    search_context = {"has_query_params": len(request.query_params) > 0, **advanced_search_options}
    return templates.TemplateResponse(request=request, name="search.html", context=search_context)


@app.get("/sets/{set_id}", include_in_schema=False)
async def get_set_page(request: Request, set_id: str, db: Session = Depends(get_db)):
    """Return the set page for the given set_id at /sets/{set_id}"""
    swu_set = db.query(SWUSet).filter(SWUSet.id == set_id).first()
    if not swu_set:
        raise HTTPException(status_code=404, detail=f"Set '{set_id}' not found")
    return templates.TemplateResponse(request=request, name="set.html", context={"set": swu_set})


@app.get("/cards/{card_id}", include_in_schema=False)
async def get_card_page(request: Request, card_id: str, db: Session = Depends(get_db)):
    """Return the card page for the given card_id at /cards/{card_id} or a random card at /cards/random"""
    if card_id.lower() == "random":
        card = db.query(SWUCard).order_by(func.random()).first()
        return RedirectResponse(f"/cards/{card.id}", status_code=303)
    else:
        card = db.query(SWUCard).filter(SWUCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail=f"Card '{card_id}' not found")
    variants = (
        db.query(SWUCard)
        .filter(
            SWUCard.name == card.name,
            SWUCard.card_type == card.card_type,
            SWUCard.subtitle == card.subtitle,
        )
        .join(SWUCard.card_set)
        .order_by(SWUSet.number, SWUCard.number)
        .all()
    )
    return templates.TemplateResponse(request=request, name="card.html", context={"card": card, "variants": variants})


@app.get("/set_list", response_model=list[SetModel])
async def get_sets(
    request: Request,
    db: Session = Depends(get_db),
    hx_request: Annotated[str | None, Header(include_in_schema=False)] = None,
):
    """Return an array of all SWU sets in the database at /set_list.
    If hx-request header is present, return the set_list.html template.
    """
    if hx_request:
        return templates.TemplateResponse(request=request, name="set_list.html")
    return all_sets


@app.get("/card_list", response_model=list[CardModel])
async def get_cards(
    request: Request,
    db: Session = Depends(get_db),
    hx_request: Annotated[str | None, Header(include_in_schema=False)] = None,
    name: str | None = None,
    text: str | None = None,
    aspect: Literal["", *(a["aspect"] for a in advanced_search_options["aspect_options"])] | None = None,
    card_type: Literal["", *advanced_search_options["card_type_options"]] | None = None,
    trait: Literal["", *advanced_search_options["trait_options"]] | None = None,
    keyword: Literal["", *advanced_search_options["keyword_options"]] | None = None,
    arena: Literal["", *advanced_search_options["arena_options"]] | None = None,
    set_id: Literal["", *(s["id"] for s in advanced_search_options["set_options"])] | None = None,
    rarity: Literal["", *advanced_search_options["rarity_options"]] | None = None,
    artist: Literal["", *advanced_search_options["artist_options"]] | None = None,
    variant_type: Literal["", *advanced_search_options["variant_type_options"]] | None = None,
    rotation: Literal["", *advanced_search_options["rotation_options"]] | None = None,
):
    """Return an array of all SWU cards matching the query parameters at /card_list.
    If hx-request header is present, return the card_list.html template.
    """
    cards = db.query(SWUCard)
    if set_id:
        cards = cards.filter(SWUCard.set_id == set_id)
    if rotation:
        cards = cards.filter(SWUSet.rotation == rotation)
    if variant_type:
        cards = cards.filter(SWUCard.variant_type == variant_type)
    if card_type:
        cards = cards.filter(SWUCard.card_type == card_type)
    if rarity:
        cards = cards.filter(SWUCard.rarity == rarity)
    if artist:
        cards = cards.filter(SWUCard.artist_search.icontains(artist))
    if name:
        name_like = "%".join(name.strip().split())
        cards = cards.filter(SWUCard.name_and_subtitle.icontains(name_like))
    if text:
        text_like = "%".join(text.strip().split())
        cards = cards.filter(SWUCard.card_text.icontains(text_like))
    if arena:
        cards = cards.join(SWUCardArena).filter(SWUCard.arenas.any(SWUCardArena.arena == arena))
    if aspect:
        cards = cards.join(SWUCardAspect).filter(SWUCard.aspects.any(SWUCardAspect.aspect == aspect))
    if trait:
        cards = cards.join(SWUCardTrait).filter(SWUCard.traits.any(SWUCardTrait.trait == trait))
    if keyword:
        cards = cards.join(SWUCardKeyword).filter(SWUCard.keywords.any(SWUCardKeyword.keyword == keyword))
    cards = cards.join(SWUCard.card_set).order_by(SWUSet.number, SWUCard.number).all()
    if hx_request:
        return templates.TemplateResponse(request=request, name="card_list.html", context={"cards": cards})
    return cards


@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    """Return the favicon.ico file at /favicon.ico"""
    return FileResponse("app/static/images/swucards/favicon.ico")


@app.get("/robots.txt", include_in_schema=False)
async def get_robots():
    """Return the robots.txt file at /robots.txt"""
    return FileResponse("app/static/robots.txt")


# Exception handlers
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    """Return the 404 template for missing pages"""
    return templates.TemplateResponse(request=request, name="404.html", context={})
