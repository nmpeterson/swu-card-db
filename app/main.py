import logging
from typing import Annotated

from fastapi import FastAPI, Request, Depends, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import get_db, SWUSet, SWUCard, SWUCardArena, SWUCardAspect, SWUCardTrait
from .models import SetModel, CardModel

logging.basicConfig(level=logging.DEBUG)

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/sets/{set_id}", response_class=HTMLResponse)
async def get_set(request: Request, set_id: str, db: Session = Depends(get_db)):
    swu_set = db.query(SWUSet).filter(SWUSet.id == set_id).first()
    return templates.TemplateResponse(request=request, name="set.html", context={"set": swu_set})


@app.get("/cards/{card_id}", response_class=HTMLResponse)
async def get_card(request: Request, card_id: str, db: Session = Depends(get_db)):
    try:
        card = db.query(SWUCard).filter(SWUCard.id == card_id).first()
        variants = (
            db.query(SWUCard)
            .filter(
                SWUCard.id != card.id,
                SWUCard.name == card.name,
                SWUCard.card_type == card.card_type,
                SWUCard.subtitle == card.subtitle,
            )
            .join(SWUCard.card_set)
            .order_by(SWUSet.number, SWUCard.id)
            .all()
        )
        return templates.TemplateResponse(
            request=request, name="card.html", context={"card": card, "variants": variants}
        )
    except Exception:
        # TODO: Implement 404 page
        return JSONResponse(content={"error": "Card not found"}, status_code=404)


@app.get("/set_list", response_model=list[SetModel])
async def get_sets(
    request: Request,
    db: Session = Depends(get_db),
    hx_request: Annotated[str | None, Header()] = None,
):
    sets = db.query(SWUSet).order_by(SWUSet.number).all()
    if hx_request:
        return templates.TemplateResponse(request=request, name="set_list.html", context={"sets": sets})
    return sets


@app.get("/card_list", response_model=list[CardModel])
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
