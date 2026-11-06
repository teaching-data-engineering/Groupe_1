import json

import joblib
from fastapi import FastAPI, HTTPException, Query
from typing import Union
from pydantic import BaseModel

from bandsintown_scraper.config import MODELS_DIR
from bandsintown_scraper.model import build_features
from bandsintown_scraper.transform import load_events_dataframe

class Objet(BaseModel):
    name:str
    price:float
    is_offer:Union[bool,None]=None


# Chargés une seule fois au démarrage : redémarrer le serveur après une nouvelle collecte
events = load_events_dataframe()
X, _ = build_features(events)
model_paths = sorted(MODELS_DIR.glob("popularite_*.joblib"))
model = joblib.load(model_paths[-1]) if model_paths else None

app = FastAPI(title="API Bandsintown")


@app.get("/") 
def read_root():
    return {"Hello": "World"}

@app.get("/mon_endpoint/{objet_id}")
async def read_objet(objet_id:int,q:Union[str,None]=None):
    return {"objet_id":objet_id,"q":q}


