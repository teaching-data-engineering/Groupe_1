import math
import re
import unicodedata
from difflib import get_close_matches

from google.cloud import bigquery

from bandsintown_scraper.loader import get_bigquery_client

PAGE_SIZE = 36
# Ressemblance minimale (de 0 à 1) pour accepter un nom d'artiste mal orthographié
ARTIST_MATCH_CUTOFF = 0.8

client = get_bigquery_client()
TABLE = f"{client.project}.dataset_group_1.events_bandsintown"


def run_query(sql, params=None):
    """Exécute une requête SQL sur BigQuery et renvoie les lignes sous forme de dictionnaires."""
    job_config = bigquery.QueryJobConfig(query_parameters=params or [])
    return [dict(row) for row in client.query(sql, job_config=job_config).result()]


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
