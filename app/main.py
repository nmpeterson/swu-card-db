import logging
import urllib.parse
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import get_db, SWUSet, SWUCard, SWUCardArena, SWUCardAspect, SWUCardTrait
from .models import SetModel, CardListModel

logging.basicConfig(level=logging.DEBUG)

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates", trim_blocks=True, lstrip_blocks=True)


def https_url_for(request: Request, name: str, **path_params: Any) -> str:
    http_url = request.url_for(name, **path_params)
    return str(http_url).replace("http://", "https://", 1)


templates.env.globals["https_url_for"] = https_url_for


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
    "card_type_options": [
        c.card_type for c in db.query(SWUCard.card_type).distinct().order_by(SWUCard.card_type).all()
    ],
    "rarity_options": [c.rarity for c in db.query(SWUCard.rarity).distinct().order_by(SWUCard.rarity).all()],
    "artist_options": [c.artist for c in db.query(SWUCard.artist).distinct().order_by(SWUCard.artist).all()],
    "variant_type_options": [
        c.variant_type for c in db.query(SWUCard.variant_type).distinct().order_by(SWUCard.variant_type).all()
    ],
}

del db
session.close()

templates.env.globals["all_sets"] = all_sets


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/search", response_class=HTMLResponse)
async def search(request: Request, db: Session = Depends(get_db)):
    search_context = {"query_string": urllib.parse.urlencode(request.query_params), **advanced_search_options}
    return templates.TemplateResponse(request=request, name="search.html", context=search_context)


@app.get("/sets/{set_id}", response_class=HTMLResponse)
async def get_set_page(request: Request, set_id: str, db: Session = Depends(get_db)):
    swu_set = db.query(SWUSet).filter(SWUSet.id == set_id).first()
    if not swu_set:
        raise HTTPException(status_code=404, detail=f"Set '{set_id}' not found")
    return templates.TemplateResponse(request=request, name="set.html", context={"set": swu_set})


@app.get("/cards/{card_id}", response_class=HTMLResponse)
async def get_card_page(request: Request, card_id: str, db: Session = Depends(get_db)):
    card = db.query(SWUCard).filter(SWUCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail=f"Card '{card_id}' not found")
    variants = (
        db.query(SWUCard)
        .filter(
            # SWUCard.id != card.id,
            SWUCard.name == card.name,
            SWUCard.card_type == card.card_type,
            SWUCard.subtitle == card.subtitle,
        )
        .join(SWUCard.card_set)
        .order_by(SWUSet.number, SWUCard.id)
        .all()
    )
    return templates.TemplateResponse(request=request, name="card.html", context={"card": card, "variants": variants})


@app.get("/set_list", response_model=list[SetModel])
async def get_sets(
    request: Request,
    db: Session = Depends(get_db),
    hx_request: Annotated[str | None, Header()] = None,
):
    if hx_request:
        return templates.TemplateResponse(request=request, name="set_list.html")
    return all_sets


@app.get("/card_list", response_model=list[CardListModel])
async def get_cards(
    request: Request,
    db: Session = Depends(get_db),
    hx_request: Annotated[str | None, Header()] = None,
):
    cards = db.query(SWUCard)
    if set_id := request.query_params.get("set_id"):
        cards = cards.filter(SWUCard.set_id == set_id)
    if name := request.query_params.get("name"):
        cards = cards.filter(SWUCard.name.icontains(name))
    if variant_type := request.query_params.get("variant_type"):
        cards = cards.filter(SWUCard.variant_type == variant_type)
    if card_type := request.query_params.get("card_type"):
        cards = cards.filter(SWUCard.card_type == card_type)
    if rarity := request.query_params.get("rarity"):
        cards = cards.filter(SWUCard.rarity == rarity)
    if artist := request.query_params.get("artist"):
        cards = cards.filter(SWUCard.artist == artist)
    if arena := request.query_params.get("arena"):
        cards = cards.join(SWUCardArena).filter(SWUCard.arenas.any(SWUCardArena.arena == arena))
    if aspect := request.query_params.get("aspect"):
        cards = cards.join(SWUCardAspect).filter(SWUCard.aspects.any(SWUCardAspect.aspect == aspect))
    if trait := request.query_params.get("trait"):
        cards = cards.join(SWUCardTrait).filter(SWUCard.traits.any(SWUCardTrait.trait == trait))
    cards = cards.join(SWUCard.card_set).order_by(SWUSet.number, SWUCard.id).all()
    if hx_request:
        return templates.TemplateResponse(request=request, name="card_list.html", context={"cards": cards})
    return cards


@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(request=request, name="404.html", context={})
