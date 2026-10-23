import json

import pandas as pd

from bandsintown_scraper.config import RAW_DATA_DIR
from geocode import obtenir_coordonnees 

FIELDS = {
    "id": "id",
    "artistName": "artiste",
    "venueName": "lieu",
    "locationText": "ville",   
    "startsAt": "debut",
    "endsAt": "fin",
    "eventUrl": "url_evenement",
    "streamingEvent": "streaming",
    "watchLiveText": "watch_live_text",
}


def load_events_dataframe(raw_dir=RAW_DATA_DIR, with_gps=True):  # <-- AJOUT : option with_gps
    """Agrège tous les JSON bruts en un DataFrame, une ligne par événement."""
    events = []
    for json_path in sorted(raw_dir.glob("*/page_*.json")):
        with open(json_path, encoding="utf-8") as file:
            events.extend(json.load(file))
    df = pd.DataFrame(events, columns=list(FIELDS)).rename(columns=FIELDS)
    df = df.drop_duplicates(subset="id")
    df["debut"] = pd.to_datetime(df["debut"])
    df["fin"] = pd.to_datetime(df["fin"])
    df = df.sort_values("debut").reset_index(drop=True)
    # ------------------ BLOC GÉOCODAGE (AJOUT) ------------------
    if with_gps:
        # 1. On liste uniquement les couples (lieu, ville) uniques pour aller vite
        lieux_uniques = df[["lieu", "ville"]].drop_duplicates().dropna()
        print(f"Géocodage de {len(lieux_uniques)} salles uniques...")
        coords = []
        for _, row in lieux_uniques.iterrows():
            lon, lat, src = obtenir_coordonnees(row["lieu"], row["ville"])
            coords.append({
                "lieu": row["lieu"],
                "ville": row["ville"],
                "longitude": lon,
                "latitude": lat,
                "sourceGeocodage": src
            })
        # 2. On fusionne les coordonnées avec l'ensemble des concerts
        df = df.merge(pd.DataFrame(coords), on=["lieu", "ville"], how="left")
    return df.sort_values("debut").reset_index(drop=True)
