import json
from typing import Union
import joblib
from fastapi import FastAPI, HTTPException, Query

from bandsintown_scraper.config import MODELS_DIR
from bandsintown_scraper.model import build_features
from bandsintown_scraper.transform import load_events_dataframe
from pydantic import BaseModel
from api.app.data_base import run_query , TABLE




PAGE_SIZE = 36

# Chargés une seule fois au démarrage : redémarrer le serveur après une nouvelle collecte
events = load_events_dataframe()
X, _ = build_features(events)
model_paths = sorted(MODELS_DIR.glob("popularite_*.joblib"))
model = joblib.load(model_paths[-1]) if model_paths else None

app = FastAPI(title="API Bandsintown")

class Objet(BaseModel):
    name: str
    price: float
    is_offer: Union[bool, None] = None

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/events/{objet_id}")
async def read_objet(objet_id: int, q: Union[str, None] = None):
    return {"objet_id": objet_id, "q": q}

@app.put("/events/{objet_id}")
def update_objet(objet_id: int, objet: Objet):
    return {"objet_name": objet.name, "objet_id": objet_id}

@app.get("/events")
def read_events(page: int = Query(1, ge=1)):
    offset = (page - 1) * PAGE_SIZE
    sql = f"""
        SELECT id, artiste, lieu, debut, nb_rsvp
        FROM `{TABLE}`
        ORDER BY debut, id
        LIMIT {PAGE_SIZE} OFFSET {offset}
    """
    return {"page": page, "taille_page": PAGE_SIZE, "evenements": run_query(sql)}
