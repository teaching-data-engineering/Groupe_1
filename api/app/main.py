import datetime
import json
from functools import lru_cache
from typing import Literal, Union
from urllib.parse import quote
import joblib
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from google.cloud import bigquery
from pydantic import BaseModel
from api.app.data_base import TABLE, find_artists, paginate_events, rsvp_stats_by, run_query
from api.app.security import verify_token
from bandsintown_scraper.config import MODELS_DIR
from bandsintown_scraper.model import build_features

TOP_ARTISTS_LIMIT = 5
PREDICTION_THRESHOLD = 0.5
TOP_FEATURES_LIMIT = 4

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

#-------------------------------- Page d'accueil ----------------------------------------
@app.get("/")
def read_root():
    return {"Hello": "World"}

#------------------------------- Tous les événement ---------------------------------------------
# version de sécurité :
#S'il n'y a pas d'autre paramètre, utilise ?token=12345.
#S'il y a déjà un paramètre, ajoute &token=12345 à la fin.

@app.get("/events")
def read_events(page: int = Query(1, ge=1)):
    return paginate_events("/events", page)

#---------------------------tous les événements associés à un artiste particulier----------------------------------


@app.get("/events/artist/{artistName}")
def read_events_by_artist(artistName: str, page: int = Query(1, ge=1)):
    artists = find_artists(artistName)
    if not artists:
        raise HTTPException(404, f"Aucun artiste ne correspond à « {artistName} »")
    params = [bigquery.ArrayQueryParameter("artistes", "STRING", artists)]
    result = paginate_events(f"/events/artist/{quote(artistName)}", page, "artiste IN UNNEST(@artistes)", params=params)
    return {"artistes_trouves": artists, **result}


#-------------------------------- Statistiques RSVPs par venue ----------------------------------------

@app.get("/events/by-venue")
def read_rsvp_stats_by_venue():
    return rsvp_stats_by("lieu")

#-------------------------------- Événements en fonction de la popularité ----------------------------------------


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


@lru_cache(maxsize=1)
def load_top_features():
    """Variables les plus importantes, lues dans le rapport qui porte le même nom que le dernier modèle."""
    report_path = sorted(MODELS_DIR.glob("popularite_*.joblib"))[-1].with_suffix(".json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    return list(report["importance_variables"])[:TOP_FEATURES_LIMIT]


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
    top_features = load_top_features()
    predictions[top_features] = X.loc[selected, top_features].round(3)
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
@app.get("/events/streaming-vs-in-person")
def read_streaming_vs_in_person():
    rows = run_query(f"SELECT COALESCE(streaming, FALSE) AS en_ligne, COUNT(*) AS total FROM `{TABLE}` GROUP BY en_ligne")
    totals = {row["en_ligne"]: row["total"] for row in rows}
    return {"en_ligne": totals.get(True, 0), "en_presentiel": totals.get(False, 0)}


#-------------------------------- Liste des événements en fin de semaine ----------------------------------------
@app.get("/events/weekend")
def read_weekend_events(page: int = Query(1, ge=1)):
    return paginate_events("/events/weekend", page, "est_weekend")


#-------------------------------- Statistiques RSVPs par type d'événement ----------------------------------------
@app.get("/events/average-rsvp-by-type")
def read_rsvp_stats_by_type():
    return rsvp_stats_by("type_evenement")


#-------------------------------- Événements en approche (dans les 7 jours) ----------------------------------------
@app.get("/events/upcoming")
def read_upcoming_events(page: int = Query(1, ge=1)):
    """Calculé depuis la date du jour : jours_avant_evenement est figé à la date de collecte."""
    today = "CURRENT_DATE('Europe/Paris')"
    where = f"DATE(debut) >= {today} AND DATE_DIFF(DATE(debut), {today}, DAY) < 7"
    return paginate_events("/events/upcoming", page, where)


#-------------------------------- Évolution du RSVP au fil du temps (Rolling Window) ----------------------------------------
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


# À garder après les routes fixes : sinon /events/{event_id} capte /events/weekend, /events/by-venue...
#-------------------------------- Un événement précis ----------------------------------------
@app.get("/events/{event_id}", response_model=Event)
def read_event(event_id: int):
    params = [bigquery.ScalarQueryParameter("event_id", "INT64", event_id)]
    rows = run_query(f"SELECT * FROM `{TABLE}` WHERE id = @event_id", params)
    if not rows:
        raise HTTPException(404, "Événement introuvable")
    return rows[0]


@app.put("/events/{event_id}")
def update_event(event_id: int, event: Event):
    """Valide l'événement reçu et le renvoie : rien n'est écrit dans BigQuery."""
    return {"event_id": event_id, "artiste": event.artiste}
