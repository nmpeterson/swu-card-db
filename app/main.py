from typing import Annotated, Union

from fastapi import FastAPI, Request, Depends, Header
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import get_db, SWUSet, SWUCard


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
            .all()
        )
        return templates.TemplateResponse(
            request=request, name="card.html", context={"card": card, "variants": variants}
        )
    except Exception:
        # TODO: Implement 404 page
        return JSONResponse(content={"error": "Card not found"}, status_code=404)


@app.get("/set_list", response_class=HTMLResponse)
async def set_list(
    request: Request, db: Session = Depends(get_db), hx_request: Annotated[Union[str, None], Header()] = None
):
    sets = db.query(SWUSet).order_by(SWUSet.number).all()
    if hx_request:
        return templates.TemplateResponse(request=request, name="set_list.html", context={"sets": sets})
    return JSONResponse(content=jsonable_encoder(sets))


@app.get("/card_list/{set_id}", response_class=HTMLResponse)
async def card_list(
    request: Request,
    set_id: str,
    db: Session = Depends(get_db),
    hx_request: Annotated[Union[str, None], Header()] = None,
):
    cards = (
        db.query(SWUCard)
        .filter(SWUCard.set_id == set_id, SWUCard.variant_type == "Normal")
        .order_by(SWUCard.number)
        .all()
    )
    if hx_request:
        return templates.TemplateResponse(request=request, name="card_list.html", context={"cards": cards})
    return JSONResponse(content=jsonable_encoder(cards))
