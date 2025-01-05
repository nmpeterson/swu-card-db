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
async def get_set(request: Request, set_id: str):
    return templates.TemplateResponse(request=request, name="set.html", context={"set_id": set_id})


@app.get("/cards/{card_id}", response_class=HTMLResponse)
async def get_card(request: Request, card_id: str, db: Session = Depends(get_db)):
    try:
        card = db.query(SWUCard).filter(SWUCard.id == card_id).first()
        variants = (
            db.query(SWUCard)
            .filter(
                SWUCard.id != card.id,
                SWUCard.name == card.name,
                SWUCard.type == card.type,
                SWUCard.subtitle == card.subtitle,
            )
            .all()
        )
        return templates.TemplateResponse(
            request=request, name="card.html", context={"card": card, "variants": variants}
        )
    except IndexError:
        return JSONResponse(content={"error": "Card not found"}, status_code=404)


@app.get("/set_list", response_class=HTMLResponse)
async def set_list(
    request: Request, db: Session = Depends(get_db), hx_request: Annotated[Union[str, None], Header()] = None
):
    SETS = [
        SWUSet(id="SOR", name="Spark of Rebellion"),
        SWUSet(id="SHD", name="Shadows of the Galaxy"),
        SWUSet(id="TWI", name="Twilight of the Republic"),
        # SWUSet(id="JTL", name="Jump to Lightspeed"),
    ]
    if hx_request:
        return templates.TemplateResponse(request=request, name="set_list.html", context={"sets": SETS})
    return JSONResponse(content=jsonable_encoder(SETS))


@app.get("/card_list/{set_id}", response_class=HTMLResponse)
async def card_list(
    request: Request,
    set_id: str,
    db: Session = Depends(get_db),
    hx_request: Annotated[Union[str, None], Header()] = None,
):
    cards = (
        db.query(SWUCard).filter(SWUCard.set == set_id, SWUCard.variant_type == "Normal").order_by(SWUCard.number).all()
    )
    if hx_request:
        return templates.TemplateResponse(request=request, name="card_list.html", context={"cards": cards})
    return JSONResponse(content=jsonable_encoder(cards))
