"""Enrichissement des évènements Bandsintown (Paris).

Entrée  : events_bandsintown_v2.csv (colonnes : id, artiste, lieu, debut, fin, url_evenement, ...)
Sortie  : data/events_enrichis.csv

Le script est idempotent : il peut être relancé tous les jours (pipeline ETL).
Les coordonnées sont mises en cache pour ne géocoder chaque lieu qu'une fois.
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

ENTREE = Path("events_bandsintown_v2.csv")
SORTIE = Path("data/events_enrichis.csv")
CACHE_GEO = Path("data/cache_geocodage.json")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Nominatim exige un User-Agent identifiable et max 1 requête par seconde.
USER_AGENT = "TD-Scraping-M2/1.0 (usage pédagogique)"
VILLE = "Paris, France"


def enrichir_dates(df: pd.DataFrame) -> pd.DataFrame:
    df["debut"] = pd.to_datetime(df["debut"], errors="coerce")
    df["fin"] = pd.to_datetime(df["fin"], errors="coerce")

    df["annee"] = df["debut"].dt.year
    df["mois"] = df["debut"].dt.month
    df["numero_semaine"] = df["debut"].dt.isocalendar().week.astype("Int64")
    df["jour_semaine"] = df["debut"].dt.dayofweek          # 0 = lundi
    df["est_weekend"] = df["jour_semaine"] >= 5
    df["heure_debut"] = df["debut"].dt.hour
    df["moment_journee"] = pd.cut(
        df["heure_debut"],
        bins=[-1, 11, 17, 21, 24],
        labels=["matin", "après-midi", "soirée", "nuit"],
    )
    # La fin n'est souvent pas renseignée : la durée reste alors vide.
    df["duree_heures"] = (df["fin"] - df["debut"]).dt.total_seconds() / 3600

    # Calculé à chaque exécution : change donc tous les jours.
    aujourdhui = pd.Timestamp.now().normalize()
    df["jours_avant_evenement"] = (df["debut"].dt.normalize() - aujourdhui).dt.days
    return df


def charger_cache() -> dict:
    if CACHE_GEO.exists():
        return json.loads(CACHE_GEO.read_text(encoding="utf-8"))
    return {}


def geocoder(lieu: str):
    params = {"q": f"{lieu}, {VILLE}", "format": "json", "limit": 1}
    r = requests.get(NOMINATIM_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=15)
    r.raise_for_status()
    resultats = r.json()
    if not resultats:
        return None
    return {"latitude": float(resultats[0]["lat"]), "longitude": float(resultats[0]["lon"])}


def enrichir_lieux(df: pd.DataFrame) -> pd.DataFrame:
    cache = charger_cache()
    for lieu in df["lieu"].dropna().unique():
        if lieu in cache:
            continue
        try:
            cache[lieu] = geocoder(lieu)
        except requests.exceptions.RequestException as e:
            print(f"Géocodage impossible pour {lieu} : {e}")
            continue
        time.sleep(1.1)  # respect de la limite de 1 requête par seconde

    CACHE_GEO.parent.mkdir(parents=True, exist_ok=True)
    CACHE_GEO.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    df["latitude"] = df["lieu"].map(lambda l: (cache.get(l) or {}).get("latitude"))
    df["longitude"] = df["lieu"].map(lambda l: (cache.get(l) or {}).get("longitude"))
    return df


def main():
    df = pd.read_csv(ENTREE)
    df = df.drop_duplicates(subset="id")
    df = enrichir_dates(df)
    df = enrichir_lieux(df)

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SORTIE, index=False, encoding="utf-8")
    print(f"{len(df)} évènements enrichis enregistrés dans {SORTIE}")


if __name__ == "__main__":
    main()
