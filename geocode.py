import json
import os
import sys
import time
import requests
import pandas as pd
from google import genai
from google.genai import types

# Assure la compatibilité des encodages sous Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def obtenir_coordonnees(venue, city):
    """Tente de géocoder l'adresse via data.gouv.fr, puis OpenStreetMap, et enfin Gemini en fallback."""
    adresse_complete = f"{venue}, {city}".strip(", ")
    
    # 1. Tentative data.gouv.fr (France)
    url_gouv = "https://api-adresse.data.gouv.fr/search/"
    try:
        res = requests.get(url_gouv, params={"q": adresse_complete, "limit": 1}, timeout=5)
        if res.status_code == 200:
            features = res.json().get("features", [])
            if features:
                coords = features[0]["geometry"]["coordinates"]
                return coords[0], coords[1], "data.gouv.fr"
    except Exception:
        pass

    # 2. Fallback OpenStreetMap (Nominatim)
    url_osm = "https://nominatim.openstreetmap.org/search"
    headers_osm = {"User-Agent": "BandsintownScraperApp/1.0"}
    try:
        res = requests.get(url_osm, params={"q": adresse_complete, "format": "json", "limit": 1}, headers=headers_osm, timeout=5)
        if res.status_code == 200:
            resultats = res.json()
            if resultats:
                return float(resultats[0]["lon"]), float(resultats[0]["lat"]), "OpenStreetMap"
    except Exception:
        pass

    return None, None, None


