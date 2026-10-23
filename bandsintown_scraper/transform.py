import json
import re
import time
from datetime import date

import pandas as pd
from curl_cffi import requests

from bandsintown_scraper.config import (
    CACHE_DIR,
    EXTERNAL_API_DELAY_SECONDS,
    EXTERNAL_API_MAX_RETRIES,
    EXTERNAL_API_USER_AGENT,
    GEOCODING_VIEWBOX,
    LOCAL_COUNTRY_CODE,
    MUSICBRAINZ_MIN_SCORE,
    MUSICBRAINZ_URL,
    NOMINATIM_URL,
    RAW_DATA_DIR,
)

FIELDS = {
    "id": "id",
    "artistName": "artiste",
    "title": "titre",
    "venueName": "lieu",
    "locationText": "localisation",
    "startsAt": "debut",
    "endsAt": "fin",
    "rsvpCountInt": "nb_rsvp",
    "eventUrl": "url_evenement",
    "streamingEvent": "streaming",
    "watchLiveText": "watch_live_text",
}

EVENT_TYPE_PATTERNS = {
    "festival": r"\bfest",
    "soirée": r"\b(party|soir[ée]e|club|dj)\b",
}
DEFAULT_EVENT_TYPE = "concert"

# Seuils choisis d'après la distribution observée : médiane à 0 RSVP, 90 % des événements à 10 ou moins
POPULARITY_BINS = [-1, 0, 9, 99, float("inf")]
POPULARITY_LABELS = ["aucune", "faible", "moyenne", "forte"]

ARTISTS_CACHE_PATH = CACHE_DIR / "artistes.json"
VENUES_CACHE_PATH = CACHE_DIR / "lieux.json"


def read_raw_events(raw_dir):
    """Lit tous les JSON bruts. La date de collecte est la date d'écriture du fichier."""
    events = []
    for json_path in sorted(raw_dir.glob("*/page_*.json")):
        collection_date = date.fromtimestamp(json_path.stat().st_mtime)
        with open(json_path, encoding="utf-8") as file:
            for event in json.load(file):
                events.append({**event, "date_collecte": collection_date})
    return events


def add_location_columns(df):
    location_parts = df["localisation"].str.rsplit(",", n=1, expand=True)
    df["ville"] = location_parts[0].str.strip()
    df["pays"] = location_parts[1].str.strip()
    # "PARIS", "Paris 19 Buttes-Chaumont"... désignent tous Paris
    df.loc[df["ville"].str.lower().str.startswith("paris", na=False), "ville"] = "Paris"
    return df


def add_date_columns(df):
    df["jour_semaine"] = df["debut"].dt.day_name()
    df["est_weekend"] = df["debut"].dt.dayofweek >= 5
    df["numero_semaine"] = df["debut"].dt.isocalendar().week.astype(int)
    df["mois"] = df["debut"].dt.month
    df["heure"] = df["debut"].dt.hour
    df["jours_avant_evenement"] = (df["debut"].dt.normalize() - df["date_collecte"]).dt.days
    df["duree_heures"] = (df["fin"] - df["debut"]).dt.total_seconds() / 3600
    return df


def classify_event_type(title):
    if pd.isna(title):
        return DEFAULT_EVENT_TYPE
    for event_type, pattern in EVENT_TYPE_PATTERNS.items():
        if re.search(pattern, title, flags=re.IGNORECASE):
            return event_type
    return DEFAULT_EVENT_TYPE


def load_cache(cache_path):
    if not cache_path.exists():
        return {}
    with open(cache_path, encoding="utf-8") as file:
        return json.load(file)


def save_cache(cache, cache_path):
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as file:
        json.dump(cache, file, ensure_ascii=False, indent=2)


def fetch_external_json(url, params):
    """Renvoie la réponse JSON, ou None en cas d'échec (le résultat ne doit alors pas être mis en cache)."""
    for attempt in range(1, EXTERNAL_API_MAX_RETRIES + 1):
        response = requests.get(url, params=params, headers={"User-Agent": EXTERNAL_API_USER_AGENT})
        time.sleep(EXTERNAL_API_DELAY_SECONDS * attempt)
        if response.status_code == 200:
            return response.json()
        if response.status_code not in (429, 503):
            break
    print(f"{url} : échec ({response.status_code})")
    return None


def obtenir_nationalite(artiste):
    """Code pays ISO de l'artiste selon MusicBrainz ("" si inconnu), ou None si la requête échoue."""
    data = fetch_external_json(
        MUSICBRAINZ_URL,
        {"query": f'artist:"{artiste.replace(chr(34), "")}"', "fmt": "json", "limit": 1},
    )
    if data is None:
        return None
    artists = data.get("artists", [])
    # Sans ce score minimum, MusicBrainz renvoie souvent un homonyme
    if not artists or int(artists[0].get("score", 0)) < MUSICBRAINZ_MIN_SCORE:
        return ""
    return artists[0].get("country", "")


def obtenir_coordonnees(lieu, ville, pays):
    """Coordonnées de la salle selon Nominatim, à défaut celles de la ville. None si la requête échoue."""
    for query, source in [(f"{lieu}, {ville}, {pays}", "salle"), (f"{ville}, {pays}", "ville")]:
        data = fetch_external_json(
            NOMINATIM_URL,
            {"q": query, "format": "json", "limit": 1, "viewbox": GEOCODING_VIEWBOX, "bounded": 1},
        )
        if data is None:
            return None
        if data:
            return {"longitude": float(data[0]["lon"]), "latitude": float(data[0]["lat"]), "source": source}
    return {"longitude": None, "latitude": None, "source": ""}


def fill_cache(cache, cache_path, keys, fetch):
    """Interroge l'API pour les clés absentes du cache. Le cache est sauvegardé même en cas d'interruption."""
    missing_keys = [key for key in keys if key not in cache]
    if not missing_keys:
        return
    print(f"{cache_path.name} : {len(missing_keys)} recherches (environ {len(missing_keys) * 2} s)...")
    try:
        for done, key in enumerate(missing_keys, start=1):
            result = fetch(key)
            if result is not None:
                cache[key] = result
            if done % 50 == 0:
                print(f"  {done}/{len(missing_keys)}")
                save_cache(cache, cache_path)
    finally:
        save_cache(cache, cache_path)


def add_external_columns(df, enrich_online):
    """Nationalité de l'artiste et coordonnées GPS de la salle, lues depuis le cache.

    Avec enrich_online=True, les valeurs absentes du cache sont d'abord demandées aux API.
    """
    artists_cache = load_cache(ARTISTS_CACHE_PATH)
    venues_cache = load_cache(VENUES_CACHE_PATH)

    venue_keys = df["lieu"] + "|" + df["ville"].fillna("") + "|" + df["pays"].fillna("")

    if enrich_online:
        fill_cache(artists_cache, ARTISTS_CACHE_PATH, df["artiste"].dropna().unique(), obtenir_nationalite)
        fill_cache(
            venues_cache,
            VENUES_CACHE_PATH,
            venue_keys.dropna().unique(),
            lambda key: obtenir_coordonnees(*key.split("|")),
        )

    df["pays_artiste"] = df["artiste"].map(artists_cache).replace("", None)
    df["artiste_local"] = df["pays_artiste"].map(
        lambda country: None if pd.isna(country) else country == LOCAL_COUNTRY_CODE
    )

    venues = venue_keys.map(venues_cache)
    df["longitude"] = venues.map(lambda venue: venue["longitude"] if isinstance(venue, dict) else None)
    df["latitude"] = venues.map(lambda venue: venue["latitude"] if isinstance(venue, dict) else None)
    df["source_geocodage"] = venues.map(lambda venue: venue["source"] if isinstance(venue, dict) else None)
    return df


def load_events_dataframe(raw_dir=RAW_DATA_DIR, enrich_online=False):
    """Agrège tous les JSON bruts en un DataFrame enrichi, une ligne par événement."""
    events = read_raw_events(raw_dir)

    df = pd.DataFrame(events, columns=[*FIELDS, "date_collecte"]).rename(columns=FIELDS)
    df = df.drop_duplicates(subset="id")
    df["debut"] = pd.to_datetime(df["debut"])
    df["fin"] = pd.to_datetime(df["fin"])
    df["date_collecte"] = pd.to_datetime(df["date_collecte"])

    df = add_location_columns(df)
    df = add_date_columns(df)
    df["type_evenement"] = df["titre"].map(classify_event_type)
    df["popularite"] = pd.cut(df["nb_rsvp"], bins=POPULARITY_BINS, labels=POPULARITY_LABELS)
    df = add_external_columns(df, enrich_online)

    # Le pays de la salle ne sert qu'au géocodage : c'est presque toujours la France
    df = df.drop(columns="pays")
    return df.sort_values("debut").reset_index(drop=True)


if __name__ == "__main__":
    events_df = load_events_dataframe()
    print(events_df.head(10))
    print(f"{len(events_df)} événements")
