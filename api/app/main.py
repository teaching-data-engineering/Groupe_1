import datetime
import json
import math
import re
import secrets
import unicodedata
from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Union
from urllib.parse import quote

import joblib
import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from google.cloud import bigquery

from bandsintown_scraper.config import MODELS_DIR
from bandsintown_scraper.model import build_features
from pydantic import BaseModel
from api.app.data_base import run_query , TABLE




PAGE_SIZE = 36
# Ressemblance minimale (de 0 à 1) pour accepter un nom d'artiste mal orthographié
ARTIST_MATCH_CUTOFF = 0.8
TOP_ARTISTS_LIMIT = 5
PREDICTION_THRESHOLD = 0.5

#-------------------------------- Sécurité : vérification du token ----------------------------------------
# Le token reste dans credentials/, ignoré par git : il ne doit jamais être écrit dans le code
API_TOKEN = json.loads(Path("credentials/api_token.json").read_text(encoding="utf-8"))["token"]
if not API_TOKEN:
    raise ValueError("Le token de credentials/api_token.json est vide : l'API ne démarre pas sans token.")


def verify_token(x_token: Annotated[str | None, Header()] = None, token: str | None = None):
    """Refuse la requête (403) si le token, dans l'en-tête X-Token ou dans l'URL, est absent ou incorrect."""
    received_token = x_token or token
    if received_token is None or not secrets.compare_digest(received_token.encode(), API_TOKEN.encode()):
        raise HTTPException(status_code=403, detail="Token absent ou invalide")


# Le token est vérifié sur toutes les routes de l'application
app = FastAPI(title="API Bandsintown", dependencies=[Depends(verify_token)])

#-------------------------------- Format d'un événement ----------------------------------------
class Event(BaseModel):
    id: int
    artiste: Union[str, None] = None
    titre: Union[str, None] = None
    lieu: Union[str, None] = None
    ville: Union[str, None] = None
    debut: Union[datetime.datetime, None] = None
    nb_rsvp: Union[int, None] = None
    type_evenement: Union[str, None] = None
    popularite: Union[str, None] = None

#-------------------------------- Fonctions communes aux routes ----------------------------------------
def paginate_events(path, page, where="TRUE", order_by="debut, id", params=None, url_filters=""):
    """Renvoie une page d'événements et ses métadonnées. where et order_by ne viennent jamais de l'utilisateur."""
    offset = (page - 1) * PAGE_SIZE
    sql = f"""
        SELECT *
        FROM `{TABLE}`
        WHERE {where}
        ORDER BY {order_by}
        LIMIT {PAGE_SIZE} OFFSET {offset}
    """
    evenements = run_query(sql, params)
    total_resultats = run_query(f"SELECT COUNT(*) AS total FROM `{TABLE}` WHERE {where}", params)[0]["total"]
    total_pages = math.ceil(total_resultats / PAGE_SIZE)
    next_page_url = f"{path}?page={page + 1}{url_filters}" if page < total_pages else None

    return {
        "evenements": evenements,
        "meta_data": {
            "page": page,
            "total_pages": total_pages,
            "total_results": total_resultats,
            "results_per_page": PAGE_SIZE,
            "next_page_url": next_page_url,
        },
    }


def rsvp_stats_by(column):
    """Moyenne, médiane, min, max et nombre d'événements par valeur d'une colonne."""
    return run_query(f"""
        SELECT
            {column},
            COUNT(*) AS nb_evenements,
            ROUND(AVG(nb_rsvp), 2) AS moyenne,
            ANY_VALUE(mediane) AS mediane,
            MIN(nb_rsvp) AS min,
            MAX(nb_rsvp) AS max
        FROM (
            SELECT {column}, nb_rsvp, PERCENTILE_CONT(nb_rsvp, 0.5) OVER (PARTITION BY {column}) AS mediane
            FROM `{TABLE}`
        )
        GROUP BY {column}
        ORDER BY nb_evenements DESC
    """)


#-------------------------------- Page d'accueil ----------------------------------------
#http://127.0.0.1:8000/
@app.get("/")
def read_root():
    return {"Hello": "World"}

#------------------------------- Tous les événement ---------------------------------------------
#http://127.0.0.1:8000/events
#http://127.0.0.1:8000/events?page=2
#version de sécurité :
#S'il n'y a pas d'autre paramètre, utilise ?token=12345.
#S'il y a déjà un paramètre, ajoute &token=12345 à la fin.

@app.get("/events")
def read_events(page: int = Query(1, ge=1)):
    return paginate_events("/events", page)

#-------------------------------- Un événement précis ----------------------------------------
#http://127.0.0.1:8000/events/108878584
@app.get("/events/{event_id}", response_model=Event)
def read_event(event_id: int):
    params = [bigquery.ScalarQueryParameter("event_id", "INT64", event_id)]
    rows = run_query(f"SELECT * FROM `{TABLE}` WHERE id = @event_id", params)
    if not rows:
        raise HTTPException(404, "Événement introuvable")
    return rows[0]

#---------------------------tous les événements associés à un artiste particulier----------------------------------
def normalize_name(name):
    """Enlève majuscules, accents et caractères spéciaux : « Beyoncé ! » et « beyonce » deviennent identiques."""
    without_accents = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", without_accents.lower())


def find_artists(search):
    """Noms exacts des artistes correspondant à la recherche : identique, puis contenu, puis proche."""
    rows = run_query(f"SELECT DISTINCT artiste FROM `{TABLE}` WHERE artiste IS NOT NULL")
    artists_by_name = {}
    for row in rows:
        artists_by_name.setdefault(normalize_name(row["artiste"]), []).append(row["artiste"])
    artists_by_name.pop("", None)

    target = normalize_name(search)
    if not target:
        return []
    if target in artists_by_name:
        return artists_by_name[target]
    names = [name for name in artists_by_name if len(target) >= 4 and target in name]
    names = names or get_close_matches(target, artists_by_name, n=5, cutoff=ARTIST_MATCH_CUTOFF)
    return [artist for name in names for artist in artists_by_name[name]]


#http://127.0.0.1:8000/events/artist/muse
#http://127.0.0.1:8000/events/artist/muse?page=2
@app.get("/events/artist/{artistName}")
def read_events_by_artist(artistName: str, page: int = Query(1, ge=1)):
    artists = find_artists(artistName)
    if not artists:
        raise HTTPException(404, f"Aucun artiste ne correspond à « {artistName} »")
    params = [bigquery.ArrayQueryParameter("artistes", "STRING", artists)]
    result = paginate_events(f"/events/artist/{quote(artistName)}", page, "artiste IN UNNEST(@artistes)", params=params)
    return {"artistes_trouves": artists, **result}


#-------------------------------- Statistiques RSVPs par venue ----------------------------------------
#http://127.0.0.1:8000/events/by-venue
@app.get("/events/by-venue")
def read_rsvp_stats_by_venue():
    return rsvp_stats_by("lieu")

#-------------------------------- Événements en fonction de la popularité ----------------------------------------
#http://127.0.0.1:8000/events/popularity?popularite=aucune
#http://127.0.0.1:8000/events/popularity?page=2
#http://127.0.0.1:8000  /events/popularity  ?popularite=forte  &page=2
#                       └─── la route ───┘  └─ 1er paramètre ┘ └ 2e ┘

@app.get("/events/popularity")
def read_events_by_popularity(
    popularite: Literal["forte", "moyenne", "faible", "aucune"] | None = None,
    page: int = Query(1, ge=1),
):
    """Événements classés du plus au moins populaire, éventuellement filtrés sur un niveau."""
    order_by = """
        CASE popularite WHEN 'forte' THEN 1 WHEN 'moyenne' THEN 2 WHEN 'faible' THEN 3 WHEN 'aucune' THEN 4 ELSE 5 END,
        nb_rsvp DESC, id
    """
    if popularite is None:
        return paginate_events("/events/popularity", page, order_by=order_by)
    params = [bigquery.ScalarQueryParameter("popularite", "STRING", popularite)]
    return paginate_events(
        "/events/popularity", page, "popularite = @popularite", order_by, params, f"&popularite={popularite}"
    )

#-------------------------------- Prévision d'affluence sur une période----------------------------------------

@lru_cache(maxsize=1)
def load_latest_model():
    """Dernier modèle sauvegardé, lu une seule fois : redémarrer le serveur après un nouvel entraînement."""
    model_paths = sorted(MODELS_DIR.glob("popularite_*.joblib"))
    return joblib.load(model_paths[-1]) if model_paths else None

#http://127.0.0.1:8000/events/predicted-attendance?date=2026-11-14
@app.get("/events/predicted-attendance")
def read_predicted_attendance(date: datetime.date):
    """Événements d'une date avec leur score de popularité (au moins 10 RSVP) calculé par le modèle.

    Le modèle classe les événements : il ne prédit pas un nombre de spectateurs. Le score sert à les comparer,
    ce n'est pas une vraie probabilité, car les classes sont rééquilibrées à l'entraînement (class_weight).
    """
    model = load_latest_model()
    if model is None:
        raise HTTPException(503, "Aucun modèle : lancez python main.py --skip-scraping --train")
    # Toute la table : build_features compte les événements par salle et par artiste
    events = pd.DataFrame(run_query(f"SELECT * FROM `{TABLE}`"))
    X, _ = build_features(events)
    selected = pd.to_datetime(events["debut"]).dt.date == date
    if not selected.any():
        raise HTTPException(404, f"Aucun événement collecté le {date}")

    predictions = events.loc[selected, ["id", "artiste", "lieu", "debut"]].copy()
    predictions["score_popularite"] = model.predict_proba(X[selected])[:, 1].round(3)
    predictions = predictions.sort_values("score_popularite", ascending=False)
    return {
        "date": date,
        "nb_evenements": len(predictions),
        "nb_evenements_populaires_prevus": int((predictions["score_popularite"] >= PREDICTION_THRESHOLD).sum()),
        "score_moyen": round(float(predictions["score_popularite"].mean()), 3),
        "evenements": json.loads(predictions.to_json(orient="records", date_format="iso")),
    }


#-------------------------------- Événements en ligne vs. événements en présentiel ----------------------------------------
#http://127.0.0.1:8000/events/streaming-vs-in-person
@app.get("/events/streaming-vs-in-person")
def read_streaming_vs_in_person():
    rows = run_query(f"SELECT COALESCE(streaming, FALSE) AS en_ligne, COUNT(*) AS total FROM `{TABLE}` GROUP BY en_ligne")
    totals = {row["en_ligne"]: row["total"] for row in rows}
    return {"en_ligne": totals.get(True, 0), "en_presentiel": totals.get(False, 0)}


#-------------------------------- Liste des événements en fin de semaine ----------------------------------------
#http://127.0.0.1:8000/events/weekend
#http://127.0.0.1:8000/events/weekend?page=2
@app.get("/events/weekend")
def read_weekend_events(page: int = Query(1, ge=1)):
    return paginate_events("/events/weekend", page, "est_weekend")


#-------------------------------- Statistiques RSVPs par type d'événement ----------------------------------------
#http://127.0.0.1:8000/events/average-rsvp-by-type
@app.get("/events/average-rsvp-by-type")
def read_rsvp_stats_by_type():
    return rsvp_stats_by("type_evenement")


#-------------------------------- Événements en approche (dans les 7 jours) ----------------------------------------
#http://127.0.0.1:8000/events/upcoming
#http://127.0.0.1:8000/events/upcoming?page=2
@app.get("/events/upcoming")
def read_upcoming_events(page: int = Query(1, ge=1)):
    """Calculé depuis la date du jour : jours_avant_evenement est figé à la date de collecte."""
    today = "CURRENT_DATE('Europe/Paris')"
    where = f"DATE(debut) >= {today} AND DATE_DIFF(DATE(debut), {today}, DAY) < 7"
    return paginate_events("/events/upcoming", page, where)


#-------------------------------- Évolution du RSVP au fil du temps (Rolling Window) ----------------------------------------
#http://127.0.0.1:8000/events/rsvp-trend
@app.get("/events/rsvp-trend")
def read_rsvp_trend():
    """Total des RSVP par jour et sa moyenne glissante sur les 7 derniers jours calendaires."""
    return run_query(f"""
        SELECT
            jour,
            total_rsvp,
            ROUND(AVG(total_rsvp) OVER (ORDER BY UNIX_DATE(jour) RANGE BETWEEN 6 PRECEDING AND CURRENT ROW), 2)
                AS moyenne_glissante_7j
        FROM (SELECT DATE(debut) AS jour, SUM(nb_rsvp) AS total_rsvp FROM `{TABLE}` GROUP BY jour)
        ORDER BY jour
    """)


#-------------------------------- Top 5 des artistes les plus populaires ----------------------------------------
#http://127.0.0.1:8000/events/top-artists
#http://127.0.0.1:8000/events/top-artists?critere=rsvp
@app.get("/events/top-artists")
def read_top_artists(critere: Literal["evenements", "rsvp"] = "evenements"):
    order_by = "nb_evenements" if critere == "evenements" else "total_rsvp"
    return run_query(f"""
        SELECT artiste, COUNT(*) AS nb_evenements, SUM(nb_rsvp) AS total_rsvp
        FROM `{TABLE}`
        WHERE artiste IS NOT NULL
        GROUP BY artiste
        ORDER BY {order_by} DESC, artiste
        LIMIT {TOP_ARTISTS_LIMIT}
    """)





@app.put("/events/{event_id}")
def update_event(event_id: int, event: Event):
    """Valide l'événement reçu et le renvoie : rien n'est écrit dans BigQuery."""
    return {"event_id": event_id, "artiste": event.artiste}


